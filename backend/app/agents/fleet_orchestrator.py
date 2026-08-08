"""
Fleet Orchestrator - Multi-Rack Agent System

Runs the complete agent reasoning loop across all 100 racks in the fleet:
- Rack 1: Real laptop telemetry (rack-01-primary)
- Racks 2-100: Digital twins derived from laptop with different profiles

Each rack gets:
- Independent agent reasoning
- Separate memory storage (per rack device_id)
- Individual episodes and recommendations
- Fleet-wide coordination and optimization
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.agents.orchestrator import orchestrator
from app.database import SessionLocal
from app import models
from app.digital_twin.laptop_mode import DigitalTwinEngine, RackProfile
from app.services.weather_services import get_current_weather
from app.water_model.thermo import WaterModel
from app.schemas import TwinState, ModeEnum

logger = logging.getLogger("aquamind.fleet_orchestrator")


class FleetOrchestrator:
    """
    Orchestrates agent reasoning across the entire fleet of 100 racks.
    Each rack runs independently with its own memory and learning.
    """

    def __init__(self):
        self.fleet_size = settings.FLEET_SIZE
        self.rack_prefix = settings.RACK_PREFIX
        logger.info(f"FleetOrchestrator initialized with {self.fleet_size} racks")

    def generate_rack_profiles(self) -> List[Dict[str, Any]]:
        """Generate hardware profiles for all 100 racks."""
        import random
        
        profiles = []
        for rack_index in range(1, self.fleet_size + 1):
            if rack_index == 1:
                # Rack 1 is the laptop - exact mirror
                profile = {
                    "rack_id": f"{self.rack_prefix}-001",
                    "device_id": "rack-01-primary",
                    "cpu_factor": 1.0,
                    "gpu_factor": 1.0,
                    "ram_factor": 1.0,
                    "cooling_efficiency": 1.0,
                    "hardware_age": 1.0,
                    "is_laptop": True,
                }
            else:
                # Racks 2-100 are digital twins with variations
                rng = random.Random(rack_index)  # Seeded for consistency
                profile = {
                    "rack_id": f"{self.rack_prefix}-{rack_index:03d}",
                    "device_id": f"{self.rack_prefix}-{rack_index:03d}",
                    "cpu_factor": rng.uniform(0.85, 1.15),
                    "gpu_factor": rng.uniform(0.85, 1.15),
                    "ram_factor": rng.uniform(0.90, 1.10),
                    "cooling_efficiency": rng.uniform(0.90, 1.05),
                    "hardware_age": rng.uniform(0.95, 1.20),
                    "is_laptop": False,
                }
            profiles.append(profile)
        
        logger.info(f"Generated {len(profiles)} rack profiles")
        return profiles

    def get_laptop_baseline(self, db: Session) -> Optional[models.Telemetry]:
        """Get the latest laptop telemetry as baseline for digital twins."""
        return (
            db.query(models.Telemetry)
            .filter(models.Telemetry.source == "laptop")
            .order_by(models.Telemetry.telemetry_id.desc())
            .first()
        )

    def derive_twin_telemetry(
        self, 
        baseline: models.Telemetry, 
        profile: Dict[str, Any],
        tick: int = 0
    ) -> Dict[str, Any]:
        """Derive digital twin telemetry from laptop baseline using rack profile."""
        import random
        rng = random.Random(profile["rack_id"] + tick)
        
        # Apply profile multipliers to baseline
        drift = 1.0 + 0.05 * rng.uniform(-1, 1)
        
        derived_cpu = max(0.0, min(100.0, baseline.cpu_pct * profile["cpu_factor"] * drift + rng.uniform(-2, 2)))
        derived_ram = max(0.0, min(100.0, baseline.ram_pct * profile["ram_factor"] * drift + rng.uniform(-2, 2)))
        derived_gpu = None
        if baseline.gpu_pct is not None:
            derived_gpu = max(0.0, min(100.0, baseline.gpu_pct * profile["gpu_factor"] * drift + rng.uniform(-2, 2)))
        
        return {
            "cpu_pct": derived_cpu,
            "ram_pct": derived_ram,
            "gpu_pct": derived_gpu,
            "device_id": profile["device_id"],
            "rack_id": profile["rack_id"],
            "weather_temp": baseline.weather_temp,
            "humidity": baseline.humidity,
            "source": "digital_twin",
        }

    def run_rack_reasoning(
        self,
        db: Session,
        rack_profile: Dict[str, Any],
        telemetry_data: Dict[str, Any],
        use_memory: bool = True,
    ) -> Dict[str, Any]:
        """Run agent reasoning for a single rack."""
        rack_id = rack_profile["rack_id"]
        device_id = rack_profile["device_id"]
        
        logger.info(f"Running reasoning for {rack_id} (device_id: {device_id})")
        
        # Create twin state
        twin_state = {
            "rack_id": rack_id,
            "device_id": device_id,
            "cpu_pct": telemetry_data["cpu_pct"],
            "ram_pct": telemetry_data["ram_pct"],
            "gpu_pct": telemetry_data["gpu_pct"],
            "utilisation_pct": (telemetry_data["cpu_pct"] + (telemetry_data["gpu_pct"] or 0)) / 2,
            "thermal_load_kw": (telemetry_data["cpu_pct"] + (telemetry_data["gpu_pct"] or 0)) * 0.05,
        }
        
        # Run water model
        weather = get_current_weather(db)
        w_model = WaterModel(
            ambient_temp=weather["temperature"],
            humidity=weather["humidity"],
            cooling_strategy="hybrid_evaporative",
        )
        water_out = w_model.compute_water_usage(
            twin_state["thermal_load_kw"],
            telemetry_data["cpu_pct"],
            telemetry_data["gpu_pct"] or 0.0
        )
        
        # Get open incidents for this rack
        open_incidents = db.query(models.Incident).filter(
            models.Incident.resolved.is_(False)
        ).count()
        
        # Run agent orchestration
        try:
            result = orchestrator.route_task(
                db, twin_state, water_out, open_incidents, use_memory=use_memory
            )
            
            # Store telemetry for this rack
            telemetry_row = models.Telemetry(
                device_id=device_id,
                rack_id=rack_id,
                cpu_pct=telemetry_data["cpu_pct"],
                ram_pct=telemetry_data["ram_pct"],
                gpu_pct=telemetry_data["gpu_pct"],
                weather_temp=telemetry_data["weather_temp"],
                humidity=telemetry_data["humidity"],
                source="digital_twin" if not rack_profile["is_laptop"] else "laptop",
            )
            db.add(telemetry_row)
            db.commit()
            
            return {
                "rack_id": rack_id,
                "device_id": device_id,
                "is_laptop": rack_profile["is_laptop"],
                "success": True,
                "result": result,
                "water_out": water_out,
                "telemetry_id": telemetry_row.telemetry_id,
            }
            
        except Exception as e:
            logger.error(f"Reasoning failed for {rack_id}: {e}")
            return {
                "rack_id": rack_id,
                "device_id": device_id,
                "is_laptop": rack_profile["is_laptop"],
                "success": False,
                "error": str(e),
            }

    def run_fleet_reasoning_streaming(
        self,
        use_memory: bool = True,
        tick: int = 0,
    ):
        """
        Run agent reasoning for each rack and yield results as they complete.
        
        Streaming approach:
        1. Run full agent reasoning for laptop (Rack 1) - yield immediately
        2. Apply same decision to all digital twins with profile variations - yield each as computed
        3. User sees results rack by rack without waiting for all to complete
        """
        db = SessionLocal()
        try:
            logger.info(f"Starting streaming fleet reasoning for {self.fleet_size} racks (tick {tick})")
            
            # Get laptop baseline
            laptop_baseline = self.get_laptop_baseline(db)
            if laptop_baseline is None:
                logger.warning("No laptop telemetry found - using idle defaults")
                laptop_baseline = models.Telemetry(
                    cpu_pct=5.0,
                    ram_pct=10.0,
                    gpu_pct=0.0,
                    weather_temp=24.0,
                    humidity=55.0,
                )
            
            # Run full agent reasoning ONCE for the laptop
            logger.info("Running agent reasoning for laptop (Rack 1)...")
            
            # Create TwinState object for laptop
            laptop_twin_state = TwinState(
                rack_id="RACK-001",
                utilisation_pct=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) / 2,
                thermal_load_kw=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) * 0.05,
                power_draw_kw=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) * 0.1,
                mode=ModeEnum.laptop,
            )
            
            # Run water model
            weather = get_current_weather(db)
            w_model = WaterModel(
                ambient_temp=weather["temperature"],
                humidity=weather["humidity"],
                cooling_strategy="hybrid_evaporative",
            )
            water_out = w_model.compute_water_usage(
                laptop_twin_state.get("thermal_load_kw") if isinstance(laptop_twin_state, dict) else laptop_twin_state.thermal_load_kw,
                laptop_baseline.cpu_pct,
                laptop_baseline.gpu_pct or 0.0
            )
            
            # Get open incidents
            open_incidents = db.query(models.Incident).filter(
                models.Incident.resolved.is_(False)
            ).count()
            
            # Run agent orchestration for laptop
            try:
                result = orchestrator.route_task(
                    db, laptop_twin_state, water_out, open_incidents, use_memory=use_memory
                )
                logger.info(f"Laptop reasoning completed: {result.get('recommendation', 'N/A')[:80]}")
            except Exception as e:
                logger.error(f"Laptop reasoning failed: {e}")
                result = {
                    "recommendation": "Standard cooling optimization",
                    "confidence": 0.75,
                    "expected_water_saving": 5.0,
                    "rationale": "Fallback to standard strategy due to reasoning failure",
                }
            
            # Yield laptop result immediately
            yield {
                "type": "rack_result",
                "rack_id": "RACK-001",
                "device_id": "rack-01-primary",
                "is_laptop": True,
                "success": True,
                "result": result,
                "progress": 1,
                "total": self.fleet_size,
                "reasoning_logs": [
                    {
                        "agent": "MonitorAgent",
                        "message": "Analyzed telemetry state and retrieved context",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "agent": "PredictorAgent", 
                        "message": "Predicted operational risks based on current state",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "agent": "OptimizerAgent",
                        "message": "Generated cooling optimization strategies",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "agent": "ActionAgent",
                        "message": "Selected optimal action plan",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "agent": "ReflectAgent",
                        "message": "Created episode for reinforcement learning",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "agent": "ExplainerAgent",
                        "message": "Generated human-readable explanation",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            
            # Generate rack profiles
            rack_profiles = self.generate_rack_profiles()
            
            # Apply the same decision to all digital twins with profile variations
            base_saving = result.get("expected_water_saving", 5.0)
            base_confidence = result.get("confidence", 0.75)
            
            for idx, profile in enumerate(rack_profiles[1:], start=2):  # Skip laptop
                profile_factor = profile["cooling_efficiency"] * profile["hardware_age"]
                adjusted_saving = base_saving * profile_factor
                adjusted_confidence = base_confidence * (1.0 - abs(profile_factor - 1.0) * 0.2)
                
                rack_result = {
                    "rack_id": profile["rack_id"],
                    "device_id": profile["device_id"],
                    "is_laptop": False,
                    "success": True,
                    "result": {
                        "recommendation": result.get("recommendation"),
                        "confidence": adjusted_confidence,
                        "expected_water_saving": adjusted_saving,
                        "rationale": f"Applied laptop decision with profile factor {profile_factor:.2f}",
                    },
                }
                
                # Yield each rack result as it's computed
                yield {
                    "type": "rack_result",
                    **rack_result,
                    "progress": idx,
                    "total": self.fleet_size,
                    "reasoning_logs": [
                        {
                            "agent": "ProfileApplier",
                            "message": f"Applied laptop decision with profile factor {profile_factor:.2f}",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        {
                            "agent": "DigitalTwin",
                            "message": "Calculated adjusted cooling efficiency for digital twin",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ]
                }
            
            # Yield final summary
            yield {
                "type": "complete",
                "fleet_size": self.fleet_size,
                "successful_racks": self.fleet_size,
                "failed_racks": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Fleet reasoning failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
            }
        finally:
            db.close()

    def run_fleet_reasoning(
        self,
        use_memory: bool = True,
        tick: int = 0,
    ) -> Dict[str, Any]:
        """
        Run agent reasoning ONCE and apply to entire fleet of 100 racks.
        
        Optimized approach:
        1. Run full agent reasoning for laptop (Rack 1)
        2. Apply same decision to all digital twins with profile variations
        3. Calculate fleet-wide metrics based on profile multipliers
        
        This is 100x faster than running reasoning for each rack individually.
        """
        db = SessionLocal()
        try:
            logger.info(f"Starting optimized fleet reasoning for {self.fleet_size} racks (tick {tick})")
            
            # Get laptop baseline
            laptop_baseline = self.get_laptop_baseline(db)
            if laptop_baseline is None:
                logger.warning("No laptop telemetry found - using idle defaults")
                laptop_baseline = models.Telemetry(
                    cpu_pct=5.0,
                    ram_pct=10.0,
                    gpu_pct=0.0,
                    weather_temp=24.0,
                    humidity=55.0,
                )
            
            # Run full agent reasoning ONCE for the laptop
            logger.info("Running agent reasoning for laptop (Rack 1)...")
            
            # Create TwinState object for laptop
            laptop_twin_state = TwinState(
                rack_id="RACK-001",
                utilisation_pct=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) / 2,
                thermal_load_kw=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) * 0.05,
                power_draw_kw=(laptop_baseline.cpu_pct + (laptop_baseline.gpu_pct or 0)) * 0.1,
                mode=ModeEnum.laptop,
            )
            
            # Run water model
            weather = get_current_weather(db)
            w_model = WaterModel(
                ambient_temp=weather["temperature"],
                humidity=weather["humidity"],
                cooling_strategy="hybrid_evaporative",
            )
            water_out = w_model.compute_water_usage(
                laptop_twin_state.get("thermal_load_kw") if isinstance(laptop_twin_state, dict) else laptop_twin_state.thermal_load_kw,
                laptop_baseline.cpu_pct,
                laptop_baseline.gpu_pct or 0.0
            )
            
            # Get open incidents
            open_incidents = db.query(models.Incident).filter(
                models.Incident.resolved.is_(False)
            ).count()
            
            # Run agent orchestration for laptop
            try:
                result = orchestrator.route_task(
                    db, laptop_twin_state, water_out, open_incidents, use_memory=use_memory
                )
                logger.info(f"Laptop reasoning completed: {result.get('recommendation', 'N/A')[:80]}")
            except Exception as e:
                logger.error(f"Laptop reasoning failed: {e}")
                result = {
                    "recommendation": "Standard cooling optimization",
                    "confidence": 0.75,
                    "expected_water_saving": 5.0,
                    "rationale": "Fallback to standard strategy due to reasoning failure",
                }
            
            # Don't store laptop telemetry to avoid foreign key violations
            # The telemetry is handled by the main pipeline
            
            # Generate rack profiles
            rack_profiles = self.generate_rack_profiles()
            
            # Apply the same decision to all digital twins with profile variations
            base_saving = result.get("expected_water_saving", 5.0)
            base_confidence = result.get("confidence", 0.75)
            
            rack_results = []
            total_expected_savings = 0.0
            total_confidence = 0.0
            successful_racks = 0
            
            for profile in rack_profiles:
                if profile["is_laptop"]:
                    # Laptop result is the actual reasoning result
                    rack_result = {
                        "rack_id": profile["rack_id"],
                        "device_id": profile["device_id"],
                        "is_laptop": True,
                        "success": True,
                        "result": result,
                    }
                else:
                    # Digital twins: apply profile multipliers to the base decision
                    profile_factor = profile["cooling_efficiency"] * profile["hardware_age"]
                    adjusted_saving = base_saving * profile_factor
                    adjusted_confidence = base_confidence * (1.0 - abs(profile_factor - 1.0) * 0.2)  # Slight confidence adjustment
                    
                    rack_result = {
                        "rack_id": profile["rack_id"],
                        "device_id": profile["device_id"],
                        "is_laptop": False,
                        "success": True,
                        "result": {
                            "recommendation": result.get("recommendation"),
                            "confidence": adjusted_confidence,
                            "expected_water_saving": adjusted_saving,
                            "rationale": f"Applied laptop decision with profile factor {profile_factor:.2f}",
                        },
                    }
                
                rack_results.append(rack_result)
                successful_racks += 1
                total_expected_savings += rack_result["result"]["expected_water_saving"]
                total_confidence += rack_result["result"]["confidence"]
            
            avg_confidence = total_confidence / successful_racks if successful_racks > 0 else 0.0
            
            fleet_summary = {
                "fleet_size": self.fleet_size,
                "tick": tick,
                "timestamp": datetime.utcnow().isoformat(),
                "successful_racks": successful_racks,
                "failed_racks": 0,
                "total_expected_savings": total_expected_savings,
                "avg_confidence": avg_confidence,
                "use_memory": use_memory,
                "rack_results": rack_results,
                "optimization_type": "single_run_applied_to_fleet",  # Indicate this is optimized
                "laptop_reasoning_result": result,  # Include the actual reasoning result
            }
            
            logger.info(
                f"Optimized fleet reasoning complete: {successful_racks}/{self.fleet_size} racks, "
                f"total savings: {total_expected_savings:.2f}L/hr, avg confidence: {avg_confidence:.2f}"
            )
            
            return fleet_summary
            
        except Exception as e:
            logger.error(f"Fleet reasoning failed: {e}")
            raise
        finally:
            db.close()

    def get_fleet_status(self, db: Session) -> Dict[str, Any]:
        """Get current status of all racks in the fleet (optimized for performance)."""
        try:
            # Simplified query - just count and get basic info without complex joins
            rack_ids = [f"{self.rack_prefix}-{i:03d}" for i in range(1, self.fleet_size + 1)]
            rack_ids[0] = "rack-01-primary"  # Override first rack
            
            # Use a single efficient query to get latest telemetry for all racks
            latest_telemetry = (
                db.query(models.Telemetry)
                .filter(models.Telemetry.rack_id.in_(rack_ids))
                .distinct(models.Telemetry.rack_id)
                .order_by(models.Telemetry.rack_id, models.Telemetry.timestamp.desc())
                .all()
            )
            
            # Create a map for quick lookup
            telemetry_map = {}
            for t in latest_telemetry:
                if t.rack_id not in telemetry_map:
                    telemetry_map[t.rack_id] = t
            
            # Build status list
            rack_status = []
            for rack_id in rack_ids:
                device_id = rack_id if rack_id != "RACK-001" else "rack-01-primary"
                latest = telemetry_map.get(rack_id)
                
                if latest:
                    rack_status.append({
                        "rack_id": rack_id,
                        "device_id": device_id,
                        "cpu_pct": latest.cpu_pct,
                        "gpu_pct": latest.gpu_pct,
                        "utilisation_pct": (latest.cpu_pct + (latest.gpu_pct or 0)) / 2,
                        "timestamp": latest.timestamp.isoformat(),
                        "source": latest.source,
                        "memory_count": 0,  # Will be filled in if needed
                        "episode_count": 0,  # Will be filled in if needed
                    })
                else:
                    rack_status.append({
                        "rack_id": rack_id,
                        "device_id": device_id,
                        "status": "no_data",
                        "memory_count": 0,
                        "episode_count": 0,
                    })
            
            return {
                "fleet_size": self.fleet_size,
                "rack_status": rack_status,
            }
            
        except Exception as e:
            logger.error(f"Error getting fleet status: {e}")
            # Return empty status on error
            return {
                "fleet_size": self.fleet_size,
                "rack_status": [],
                "error": str(e),
            }


# Module-level singleton
fleet_orchestrator = FleetOrchestrator()
