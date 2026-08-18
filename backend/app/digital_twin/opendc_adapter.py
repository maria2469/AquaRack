"""
OpenDC / CloudSim adapter (SDD Phase 2, Section 13/15).

Digital-twin mode: rack telemetry is now DERIVED from the latest real
laptop reading instead of synthetic WORKLOAD_PROFILES. Rack 1 is an exact
mirror of the laptop; Racks 2..N apply fixed per-rack "hardware profile"
multipliers (cooling efficiency, hardware age, airflow, etc.) plus small
noise on top of the same base signal, and a time-varying workload-drift
curve so utilisation still evolves tick-to-tick. This keeps the adapter's
public contract (SimulationJob rows + Telemetry rows in the shared schema)
unchanged — only `_run_job`'s internals differ.

Jobs run as a background thread (SDD Section 15.3: "asynchronous ...
clients poll GET /api/v1/simulate/opendc/{job_id}"; in AWS this maps to an
AWS Batch job). Progress is checkpointed into SimulationJob.result after
every tick so partial results are visible before completion.
"""
import random
import threading
from datetime import datetime

  # noqa: F401
from app import models
from app.config import settings
from app.database import SessionLocal
from app.digital_twin.laptop_mode import DigitalTwinEngine, RackProfile
from app.water_model.thermo import WaterModel
from app.services.weather_services import get_current_weather

from app.models_ext import Site, SimulationJob


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


class _SyntheticReading:
    """Adapter row: shaped like a Telemetry ORM row so it flows through
    DigitalTwinEngine.simulate() unchanged (Section 15.2)."""

    def __init__(self, cpu_pct: float, ram_pct: float, gpu_pct=None, fan_rpm=None):
        self.cpu_pct = cpu_pct
        self.ram_pct = ram_pct
        self.gpu_pct = gpu_pct
        self.fan_rpm = fan_rpm


# ---------------------------------------------------------------------------
# Rack hardware profiles
#
# Each rack (besides Rack 1, the laptop mirror) gets a FIXED set of
# per-rack multipliers, assigned once per job from a seeded RNG keyed on
# rack index, so a given rack index behaves consistently rack-to-rack and
# run-to-run is still varied by job. This models real fleet heterogeneity
# (different hardware generations, airflow, cooling) rather than pure
# per-tick randomness.
# ---------------------------------------------------------------------------
def _make_rack_profile(rack_index: int, rng: random.Random) -> dict:
    if rack_index == 1:
        # Rack 1 is the exact laptop mirror — no distortion applied.
        return {
            "cpu_factor": 1.0,
            "gpu_factor": 1.0,
            "ram_factor": 1.0,
            "cooling_efficiency": 1.0,
            "hardware_age": 1.0,
        }
    return {
        "cpu_factor": rng.uniform(0.85, 1.15),
        "gpu_factor": rng.uniform(0.85, 1.15),
        "ram_factor": rng.uniform(0.90, 1.10),
        "cooling_efficiency": rng.uniform(0.90, 1.05),
        "hardware_age": rng.uniform(0.95, 1.20),
    }


def _workload_drift(tick: int, rng: random.Random) -> float:
    """
    Small tick-over-tick drift factor so utilisation still evolves over the
    course of the simulation, instead of being frozen at the single laptop
    reading for every tick. Centered at 1.0.
    """
    return 1.0 + 0.05 * (rng.uniform(-1, 1)) + 0.03 * (tick % 5 - 2) / 2.0


def _get_latest_laptop_reading(db) -> "models.Telemetry | None":
    """
    Fetches the most recent laptop-sourced telemetry row to use as the
    digital twin's reference baseline (Rack 1). Falls back to None if no
    laptop telemetry exists yet, in which case callers should use safe
    idle defaults rather than fail the job.
    """
    return (
        db.query(models.Telemetry)
        .filter(models.Telemetry.source == "laptop")
        .order_by(models.Telemetry.telemetry_id.desc())
        .first()
    )


def _derive_reading(base_cpu: float, base_ram: float, base_gpu, profile: dict,
                     tick: int, rng: random.Random) -> _SyntheticReading:
    drift = _workload_drift(tick, rng)

    cpu = _clamp(base_cpu * profile["cpu_factor"] * drift + rng.uniform(-2, 2))
    ram = _clamp(base_ram * profile["ram_factor"] * drift + rng.uniform(-2, 2))
    gpu = None
    if base_gpu is not None:
        gpu = _clamp(base_gpu * profile["gpu_factor"] * drift + rng.uniform(-2, 2))

    return _SyntheticReading(cpu_pct=cpu, ram_pct=ram, gpu_pct=gpu)


def _run_job(job_id: str, spec: dict) -> None:
    db = SessionLocal()
    try:
        job = db.get(SimulationJob, job_id)
        job.status = "running"
        db.commit()

        mode = spec.get("mode", "opendc")
        # Use fleet size from settings if not specified
        num_racks = max(1, int(spec.get("num_racks", settings.FLEET_SIZE)))
        ticks = max(1, int(spec.get("duration_ticks", 20)))

        # Deterministic-per-job RNG seed so rack profiles are stable across
        # a single run's ticks but still vary run-to-run.
        rng = random.Random(spec.get("seed", job_id))

        # --- Digital twin baseline: real laptop telemetry -----------------
        laptop_reading = _get_latest_laptop_reading(db)
        if laptop_reading is not None:
            base_cpu = laptop_reading.cpu_pct or 0.0
            base_ram = laptop_reading.ram_pct or 0.0
            base_gpu = laptop_reading.gpu_pct  # may be None
        else:
            # No laptop telemetry collected yet — safe idle fallback so the
            # job doesn't crash, but this should be rare/transient.
            base_cpu, base_ram, base_gpu = 5.0, 10.0, None

        # All racks in this job share one ambient weather reading — they're
        # in the same simulated facility, not fetched per-rack/per-tick.
        weather = get_current_weather(db)
        ambient_temp = weather["temperature"]
        humidity = weather["humidity"]

        site = Site(
            name=spec.get("site_name") or f"{mode}-site-{job_id[:8]}",
            region=spec.get("region") or "sim-region-1",
        )
        db.add(site)
        db.commit()
        db.refresh(site)

        rack_results = []
        total_ticks = num_racks * ticks

        for r in range(num_racks):
            rack_index = r + 1
            profile = _make_rack_profile(rack_index, rng)

            rack = models.Rack(
                capacity_kw=spec.get("capacity_kw", 8.0),
                node_count=spec.get("node_count", 4),
                location=site.name,
                site_id=site.site_id,
            )
            db.add(rack)
            db.commit()
            db.refresh(rack)
            db.add(models.RackConfig(
                rack_id=rack.rack_id,
                mode=mode,
                sim_params={**spec, "rack_profile": profile, "is_laptop_mirror": rack_index == 1},
            ))
            db.commit()

            twin = DigitalTwinEngine(
                RackProfile.load_config(rack.rack_id, rack.capacity_kw, rack.node_count), mode=mode
            )
            # Use consistent device_id format for all racks
            device_id = f"{settings.RACK_PREFIX}-{rack_index:03d}" if rack_index > 1 else "rack-01-primary"

            last_twin_state = None
            last_water_out = None

            for t in range(ticks):
                reading = _derive_reading(base_cpu, base_ram, base_gpu, profile, t, rng)
                twin_state = twin.simulate(reading)

                row = models.Telemetry(
                    rack_id=rack.rack_id,
                    device_id=device_id,
                    site_id=site.site_id,
                    cpu_pct=reading.cpu_pct,
                    ram_pct=reading.ram_pct,
                    gpu_pct=reading.gpu_pct,
                    source=mode,
                    weather_temp=ambient_temp,
    humidity=humidity,
                )
                db.add(row)
                db.commit()
                db.refresh(row)

                water = WaterModel(
                    ambient_temp=ambient_temp,
                    humidity=humidity,
                    pue_thermal_overhead=settings.PUE_THERMAL_OVERHEAD,
                )
                # Cooling efficiency of this rack's hardware profile feeds
                # into thermal load before the water model sees it.
                thermal_load_kw = twin_state.get("thermal_load_kw") if isinstance(twin_state, dict) else twin_state.thermal_load_kw
                utilisation_pct = twin_state.get("utilisation_pct") if isinstance(twin_state, dict) else twin_state.utilisation_pct
                power_draw_kw = twin_state.get("power_draw_kw") if isinstance(twin_state, dict) else twin_state.power_draw_kw
                
                adjusted_thermal_kw = thermal_load_kw / max(0.5, profile["cooling_efficiency"])
                water_out = water.compute_water_usage(adjusted_thermal_kw)
                db.add(
                    models.WaterModelResult(
                        telemetry_id=row.telemetry_id,
                        wue_factor=water_out["wue_factor"],
                        cooling_load_kw=water_out["cooling_load_kw"],
                        water_l_per_hr=water_out["water_l_per_hr"],
                        pue=water_out["pue"],
                        utilisation_pct=utilisation_pct,
                        thermal_load_kw=adjusted_thermal_kw,
                        power_draw_kw=power_draw_kw,
                    )
                )
                if utilisation_pct >= 85:
                    from app.memory_engine.summarise import summarise_incident
                    from app.mcp.client import mcp_client

                    incident = models.Incident(
                        device_id=device_id,  # Add device_id
                        telemetry_id=row.telemetry_id,
                        severity="HIGH",
                        description=f"[{mode}] {device_id} utilisation critical at {utilisation_pct:.1f}%",
                        root_cause=(
                            f"Rack profile cooling_efficiency={profile['cooling_efficiency']:.2f}, "
                            f"hardware_age={profile['hardware_age']:.2f} under ambient {ambient_temp:.1f}\u00b0C"
                        ),
                    )
                    db.add(incident)
                    db.commit()
                    db.refresh(incident)

                    summary = summarise_incident(
                        severity=incident.severity,
                        description=incident.description,
                        root_cause=incident.root_cause,
                        rack_id=rack.rack_id,
                        created_at=incident.created_at.isoformat(),
                    )
                    mcp_client.store_agent_memory(db, "incident", incident.incident_id, summary, device_id=device_id)
                db.commit()

                last_twin_state = twin_state
                last_water_out = water_out

                # Checkpointed partial progress (Section 15.3) — visible via GET before completion
                done_ticks = (r * ticks) + (t + 1)
                job.progress_pct = round(done_ticks / total_ticks * 100, 1)
                job.result = {
                    "partial": True,
                    "racks_completed": r,
                    "current_rack": device_id,
                    "current_tick": t + 1,
                }
                job.updated_at = datetime.utcnow()
                db.commit()

            # Handle both dict and object for last_twin_state
            if isinstance(last_twin_state, dict):
                final_util = last_twin_state.get("utilisation_pct", 0)
                final_thermal = last_twin_state.get("thermal_load_kw", 0)
            else:
                final_util = last_twin_state.utilisation_pct
                final_thermal = last_twin_state.thermal_load_kw
                
            rack_results.append(
                {
                    "rack_id": rack.rack_id,
                    "device_id": device_id,
                    "is_laptop_mirror": rack_index == 1,
                    "rack_profile": profile,
                    "final_utilisation_pct": final_util,
                    "final_thermal_load_kw": final_thermal,
                    "final_water_model": last_water_out,
                }
            )

        fleet_thermal_kw = sum(r["final_thermal_load_kw"] for r in rack_results)
        fleet_water_l_per_hr = sum(r["final_water_model"]["water_l_per_hr"] for r in rack_results)

        job.status = "completed"
        job.progress_pct = 100.0
        job.result = {
            "partial": False,
            "site_id": site.site_id,
            "site_name": site.name,
            "num_racks": num_racks,
            "baseline_source": "laptop" if laptop_reading is not None else "idle_fallback",
            "baseline_reading": {"cpu_pct": base_cpu, "ram_pct": base_ram, "gpu_pct": base_gpu},
            "weather": {"ambient_temp": ambient_temp, "humidity": humidity, "source": weather.get("source")},
            "racks": rack_results,
            "fleet_thermal_load_kw": round(fleet_thermal_kw, 3),
            "fleet_water_l_per_hr": round(fleet_water_l_per_hr, 3),
        }
        job.updated_at = datetime.utcnow()
        db.commit()

    except Exception as exc:  # a failed simulation job must not crash the service
        job = db.get(SimulationJob, job_id)
        if job:
            job.status = "failed"
            job.result = {"error": str(exc)}
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def submit_job(db, spec: dict) -> SimulationJob:
    """
    Creates the SimulationJob row and kicks off the (synchronous-looking
    but background-threaded) simulation. In AWS, this POST instead enqueues
    an AWS Batch job (Section 4.1); the polling contract to the client is
    identical either way.
    """
    job = SimulationJob(mode=spec.get("mode", "opendc"), spec=spec, status="queued", progress_pct=0.0)
    db.add(job)
    db.commit()
    db.refresh(job)

    thread = threading.Thread(target=_run_job, args=(job.job_id, spec), daemon=True)
    thread.start()
    return job


def simulate_scaled_racks(db, laptop_telemetry: "models.Telemetry", num_racks: int = 100, device_lat: float = None, device_lon: float = None) -> dict:
    """
    Scales single laptop telemetry (Rack 1) across Racks 2 to num_racks
    using the same fixed-per-rack-profile approach as _run_job, instead of
    unbounded per-call randomness. Calculates aggregated fleet thermal
    load, GPU power draw, and water consumption.

    Prefers the real weather already attached to laptop_telemetry (set at
    collection time); calling get_current_weather here as a fallback
    keeps the Weather table populated even for telemetry rows collected
    before weather was wired in.

    Args:
        db: Database session
        laptop_telemetry: Real laptop telemetry to base simulations on
        num_racks: Number of racks to simulate (default 100)
        device_lat: Optional device latitude for weather (overrides config)
        device_lon: Optional device longitude for weather (overrides config)
    """
    base_cpu = laptop_telemetry.cpu_pct or 0.0
    base_gpu = laptop_telemetry.gpu_pct or 0.0
    base_water = laptop_telemetry.predicted_water_usage or 1.2

    if laptop_telemetry.weather_temp is None or laptop_telemetry.humidity is None or (device_lat and device_lon):
        get_current_weather(db, lat=device_lat, lon=device_lon, ignore_cached_telemetry=True)

    rng = random.Random(f"scaled-{laptop_telemetry.telemetry_id}")

    racks = []
    total_water = 0.0
    total_thermal_kw = 0.0

    for r in range(1, num_racks + 1):
        profile = _make_rack_profile(r, rng)
        if r == 1:
            rack_cpu = base_cpu
            rack_gpu = base_gpu
        else:
            rack_cpu = _clamp(base_cpu * profile["cpu_factor"] + rng.uniform(-2, 2))
            rack_gpu = _clamp(base_gpu * profile["gpu_factor"] + rng.uniform(-2, 2))

        thermal_kw = (rack_cpu * 0.03 + rack_gpu * 0.05) / max(0.5, profile["cooling_efficiency"]) + 2.0
        water_l_hr = base_water * (0.8 + 0.4 * (rack_gpu / 100.0))
        total_water += water_l_hr
        total_thermal_kw += thermal_kw

        racks.append({
            "rack_id": f"Rack-{r}",
            "is_laptop": (r == 1),
            "cpu_pct": round(rack_cpu, 1),
            "gpu_pct": round(rack_gpu, 1),
            "thermal_kw": round(thermal_kw, 2),
            "water_l_hr": round(water_l_hr, 2),
        })

    return {
        "rack_count": num_racks,
        "rack_1_laptop": racks[0],
        "fleet_total_water_l_hr": round(total_water, 2),
        "fleet_total_thermal_kw": round(total_thermal_kw, 2),
        "racks_sample": racks[:10],
    }