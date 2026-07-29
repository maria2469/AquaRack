"""
OpenDC / CloudSim adapter (SDD Phase 2, Section 13/15).

This is the "new" piece Phase 2 adds behind the existing DigitalTwinEngine
interface (Section 15.2: "only the Digital Twin Engine's adapter layer is
new"). It maps simulated data-centre workloads onto the *exact same*
TelemetryReading / TwinState schema the laptop collector produces, so the
Water Model, Memory Engine, and AI Decision Agent all consume it with zero
changes.

There is no real OpenDC/CloudSim binary bundled here (that's a large Java/
Kotlin simulation framework) — this adapter is a lightweight, dependency-
free stand-in that generates plausible per-tick, per-rack utilisation
curves for a handful of workload archetypes, which is enough to exercise
the full downstream pipeline end-to-end exactly like the SDD describes.
Swapping in real OpenDC/CloudSim output later is a matter of replacing
`WORKLOAD_PROFILES`/`_run_job` internals — the adapter's public contract
(SimulationJob rows + Telemetry rows in the shared schema) does not change.

Jobs run as a background thread (SDD Section 15.3: "asynchronous ...
clients poll GET /api/v1/simulate/opendc/{job_id}"; in AWS this maps to an
AWS Batch job). Progress is checkpointed into SimulationJob.result after
every tick so partial results are visible before completion.
"""
import random
import threading
from datetime import datetime

import phase2_distributed.common.pathsetup  # noqa: F401
from app import models
from app.config import settings
from app.database import SessionLocal
from app.digital_twin.laptop_mode import DigitalTwinEngine, RackProfile
from app.water_model.thermo import WaterModel

from phase2_distributed.common.models_ext import Site, SimulationJob

WORKLOAD_PROFILES = {
    "steady": lambda tick: 45 + random.uniform(-5, 5),
    "bursty": lambda tick: 20 + (55 if tick % 5 == 0 else 0) + random.uniform(-5, 5),
    "cpu_intensive": lambda tick: 82 + random.uniform(-6, 10),
    "idle": lambda tick: 6 + random.uniform(0, 6),
}


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


def _run_job(job_id: str, spec: dict) -> None:
    db = SessionLocal()
    try:
        job = db.get(SimulationJob, job_id)
        job.status = "running"
        db.commit()

        mode = spec.get("mode", "opendc")
        num_racks = max(1, int(spec.get("num_racks", 5)))
        profile_name = spec.get("workload_profile", "steady")
        ticks = max(1, int(spec.get("duration_ticks", 20)))
        profile_fn = WORKLOAD_PROFILES.get(profile_name, WORKLOAD_PROFILES["steady"])

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
            rack = models.Rack(
                capacity_kw=spec.get("capacity_kw", 8.0),
                node_count=spec.get("node_count", 4),
                location=site.name,
                site_id=site.site_id,
            )
            db.add(rack)
            db.commit()
            db.refresh(rack)
            db.add(models.RackConfig(rack_id=rack.rack_id, mode=mode, sim_params=spec))
            db.commit()

            twin = DigitalTwinEngine(
                RackProfile.load_config(rack.rack_id, rack.capacity_kw, rack.node_count), mode=mode
            )
            device_id = f"{mode}-rack-{r + 1}-{job_id[:6]}"

            last_twin_state = None
            last_water_out = None

            for t in range(ticks):
                util_seed = _clamp(profile_fn(t))
                reading = _SyntheticReading(
                    cpu_pct=util_seed,
                    ram_pct=_clamp(util_seed * 0.8 + random.uniform(-3, 3)),
                )
                twin_state = twin.simulate(reading)

                row = models.Telemetry(
                    rack_id=rack.rack_id,
                    device_id=device_id,
                    site_id=site.site_id,
                    cpu_pct=reading.cpu_pct,
                    ram_pct=reading.ram_pct,
                    gpu_pct=None,
                    source=mode,
                )
                db.add(row)
                db.commit()
                db.refresh(row)

                water = WaterModel(
                    ambient_temp=settings.DEFAULT_AMBIENT_TEMP_C,
                    humidity=settings.DEFAULT_HUMIDITY_PCT,
                    pue_thermal_overhead=settings.PUE_THERMAL_OVERHEAD,
                )
                water_out = water.compute_water_usage(twin_state.thermal_load_kw)
                db.add(
                    models.WaterModelResult(
                        telemetry_id=row.telemetry_id,
                        wue_factor=water_out["wue_factor"],
                        cooling_load_kw=water_out["cooling_load_kw"],
                        water_l_per_hr=water_out["water_l_per_hr"],
                        pue=water_out["pue"],
                        utilisation_pct=twin_state.utilisation_pct,
                        thermal_load_kw=twin_state.thermal_load_kw,
                        power_draw_kw=twin_state.power_draw_kw,
                    )
                )
                if twin_state.utilisation_pct >= 85:
                    db.add(
                        models.Incident(
                            telemetry_id=row.telemetry_id,
                            severity="high",
                            description=f"[{mode}] {device_id} utilisation critical at {twin_state.utilisation_pct}%",
                            resolved=False,
                        )
                    )
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

            rack_results.append(
                {
                    "rack_id": rack.rack_id,
                    "device_id": device_id,
                    "final_utilisation_pct": last_twin_state.utilisation_pct,
                    "final_thermal_load_kw": last_twin_state.thermal_load_kw,
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
            "workload_profile": profile_name,
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
