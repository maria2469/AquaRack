"""
Scenario Management API

Run realistic data center scenarios to demonstrate AquaRack AI capabilities
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.database import get_db
from app import models
from app.digital_twin.scenarios import ScenarioGenerator, DataCenterScenario
from app.water_model.thermo import WaterModel
from app.digital_twin.laptop_mode import DigitalTwinEngine, RackProfile

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])
logger = logging.getLogger(__name__)


@router.get("/list")
def list_scenarios() -> List[Dict[str, Any]]:
    """List all available data center scenarios"""
    scenarios = ScenarioGenerator.get_all_scenarios()
    return [
        {
            "name": scenario.name,
            "description": scenario.description,
            "duration_minutes": scenario.duration_minutes,
            "num_racks": scenario.num_racks,
            "workload_pattern": scenario.workload_pattern,
            "expected_problems": scenario.expected_problems,
        }
        for scenario in scenarios
    ]


@router.post("/run/{scenario_name}")
def run_scenario(
    scenario_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run a specific data center scenario
    
    This generates realistic telemetry data that demonstrates the problem
    AquaRack AI is designed to solve.
    """
    scenarios = ScenarioGenerator.get_all_scenarios()
    scenario = next((s for s in scenarios if s.name.lower() == scenario_name.lower()), None)
    
    if not scenario:
        available = [s.name for s in scenarios]
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Available: {available}"
        )
    
    logger.info(f"Running scenario: {scenario.name}")
    
    # Create site for this scenario
    from app.models_ext import Site
    site = Site(
        name=f"scenario-{scenario.name.lower().replace(' ', '-')}",
        region="test-region",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    
    # Create racks with realistic profiles
    racks = []
    for rack_profile in scenario.rack_profiles:
        rack_type = ScenarioGenerator.RACK_TYPES[rack_profile["type"]]
        rack = models.Rack(
            capacity_kw=rack_type["capacity_kw"],
            node_count=rack_type["node_count"],
            location=site.name,
            site_id=site.site_id,
        )
        db.add(rack)
        db.commit()
        db.refresh(rack)
        racks.append({
            "rack": rack,
            "profile": rack_profile,
            "type": rack_type
        })
    
    # Generate telemetry for the scenario duration
    telemetry_data = []
    water_model_data = []
    
    for minute in range(scenario.duration_minutes):
        for rack_data in racks:
            rack = rack_data["rack"]
            profile = rack_data["profile"]
            rack_type = rack_data["type"]
            
            # Generate realistic workload for this minute
            workload_curve = ScenarioGenerator.generate_workload_curve(
                scenario.workload_pattern,
                scenario.duration_minutes,
                profile["initial_cpu"]
            )
            
            current_cpu = workload_curve[minute]
            current_gpu = profile["initial_gpu"] * (current_cpu / profile["initial_cpu"])
            
            # Simulate thermal effects
            thermal_load = rack_type["base_thermal_load"] * (current_cpu / 100.0)
            
            # Apply scenario-specific conditions
            if scenario.initial_conditions.get("cooling_failure"):
                thermal_load *= 1.3  # Higher thermal load due to cooling failure
            
            # Create telemetry record
            telemetry = models.Telemetry(
                rack_id=rack.rack_id,
                device_id=f"{profile['id']}",
                site_id=site.site_id,
                cpu_pct=current_cpu,
                gpu_pct=current_gpu,
                ram_pct=current_cpu * 0.8,  # RAM usually follows CPU
                source="scenario",
                weather_temp=scenario.initial_conditions["ambient_temp_c"],
                humidity=scenario.initial_conditions["humidity_pct"],
            )
            db.add(telemetry)
            db.commit()
            db.refresh(telemetry)
            
            # Run water model
            water_model = WaterModel(
                ambient_temp=scenario.initial_conditions["ambient_temp_c"],
                humidity=scenario.initial_conditions["humidity_pct"],
                pue_thermal_overhead=0.4,
            )
            
            water_result = water_model.compute_water_usage(
                thermal_load_kw=thermal_load,
                cpu_pct=current_cpu,
                gpu_pct=current_gpu
            )
            
            water_model_result = models.WaterModelResult(
                telemetry_id=telemetry.telemetry_id,
                wue_factor=water_result["wue_factor"],
                cooling_load_kw=water_result["cooling_load_kw"],
                water_l_per_hr=water_result["water_l_per_hr"],
                pue=water_result["pue"],
                utilisation_pct=current_cpu,
                thermal_load_kw=thermal_load,
            )
            db.add(water_model_result)
            db.commit()
            
            telemetry_data.append({
                "minute": minute,
                "rack_id": profile["id"],
                "cpu_pct": current_cpu,
                "gpu_pct": current_gpu,
                "thermal_load_kw": thermal_load,
                "water_l_per_hr": water_result["water_l_per_hr"],
            })
    
    # Create incidents if scenario expects them
    if "temperature" in " ".join(scenario.expected_problems).lower():
        incident = models.Incident(
            severity="HIGH",
            description=f"Thermal issue detected during {scenario.name}",
            telemetry_id=telemetry_data[-1].get("telemetry_id") if telemetry_data else None,
        )
        db.add(incident)
        db.commit()
    
    logger.info(f"Scenario '{scenario.name}' completed: {len(telemetry_data)} telemetry records generated")
    
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "site_id": site.site_id,
        "racks_created": len(racks),
        "telemetry_records": len(telemetry_data),
        "duration_minutes": scenario.duration_minutes,
        "expected_problems": scenario.expected_problems,
        "next_steps": [
            "1. Run AquaRack AI reasoning to address the identified problems",
            "2. Monitor the Memory Dashboard for episode creation",
            "3. Check the Reasoning Trace for AI decision-making process",
            "4. Verify water savings and thermal improvements after AI intervention"
        ]
    }


@router.get("/status/{site_id}")
def get_scenario_status(site_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get status of a running scenario"""
    from app.models_ext import Site
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Get telemetry for this site
    telemetry_count = db.query(models.Telemetry).filter(
        models.Telemetry.site_id == site_id
    ).count()
    
    # Get incidents
    incidents = db.query(models.Incident).join(models.Telemetry).filter(
        models.Telemetry.site_id == site_id
    ).all()
    
    # Get latest thermal data
    latest_telemetry = db.query(models.Telemetry).filter(
        models.Telemetry.site_id == site_id
    ).order_by(models.Telemetry.timestamp.desc()).first()
    
    return {
        "site_id": site_id,
        "site_name": site.name,
        "telemetry_records": telemetry_count,
        "incidents": len(incidents),
        "latest_thermal_load": latest_telemetry.cpu_pct if latest_telemetry else None,
        "incidents_list": [
            {"severity": inc.severity, "description": inc.description}
            for inc in incidents
        ]
    }