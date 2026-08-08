"""
Realistic Data Center Scenarios for AquaRack Demonstration

These scenarios demonstrate real data center problems that AquaRack AI solves:
- Thermal hotspots
- Efficiency optimization
- Capacity planning
- Emergency response
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class DataCenterScenario:
    """A realistic data center scenario for testing RackPulse AI"""
    name: str
    description: str
    duration_minutes: int
    num_racks: int
    initial_conditions: Dict[str, Any]
    workload_pattern: str  # "steady", "spike", "gradual", "variable"
    expected_problems: List[str]
    rack_profiles: List[Dict[str, Any]]
    
class ScenarioGenerator:
    """Generates realistic data center scenarios"""
    
    # Realistic rack hardware profiles based on actual data center equipment
    RACK_TYPES = {
        "high_density_gpu": {
            "capacity_kw": 20.0,
            "node_count": 8,
            "base_thermal_load": 15.0,
            "cooling_requirement": "high",
            "typical_usage": "AI/ML workloads"
        },
        "standard_compute": {
            "capacity_kw": 8.0,
            "node_count": 4,
            "base_thermal_load": 5.0,
            "cooling_requirement": "medium",
            "typical_usage": "General computing"
        },
        "storage_heavy": {
            "capacity_kw": 5.0,
            "node_count": 2,
            "base_thermal_load": 3.0,
            "cooling_requirement": "low",
            "typical_usage": "Data storage"
        }
    }
    
    @staticmethod
    def thermal_hotspot_scenario() -> DataCenterScenario:
        """
        Scenario: Thermal Hotspot Emergency
        Problem: GPU rack reaches dangerous temperatures during AI training job
        Expected AI Action: Increase cooling, redistribute workload
        """
        return DataCenterScenario(
            name="Thermal Hotspot Emergency",
            description="GPU-intensive AI training causes thermal hotspot in high-density rack",
            duration_minutes=5,  # Reduced for faster testing
            num_racks=3,  # Reduced for faster testing
            initial_conditions={
                "ambient_temp_c": 28.0,  # High ambient temperature
                "humidity_pct": 65.0,
                "cooling_efficiency": 0.85,  # Degraded cooling
            },
            workload_pattern="spike",
            expected_problems=[
                "GPU rack temperature exceeding 85°C",
                "Risk of thermal throttling",
                "Localized pressure on cooling system"
            ],
            rack_profiles=[
                {"type": "high_density_gpu", "id": "rack-gpu-01", "initial_cpu": 85.0, "initial_gpu": 95.0},
                {"type": "standard_compute", "id": "rack-cpu-01", "initial_cpu": 45.0, "initial_gpu": 10.0},
                {"type": "storage_heavy", "id": "rack-storage-01", "initial_cpu": 20.0, "initial_gpu": 5.0},
            ]
        )
    
    @staticmethod
    def efficiency_optimization_scenario() -> DataCenterScenario:
        """
        Scenario: Efficiency Optimization
        Problem: High WUE during off-peak hours due to inefficient cooling
        Expected AI Action: Reduce cooling intensity, maintain thermal safety
        """
        return DataCenterScenario(
            name="Efficiency Optimization",
            description="Optimize water usage during low-utilization periods while maintaining thermal safety",
            duration_minutes=10,  # Reduced for faster testing
            num_racks=4,  # Reduced for faster testing
            initial_conditions={
                "ambient_temp_c": 22.0,  # Moderate ambient
                "humidity_pct": 50.0,
                "cooling_efficiency": 0.95,  # Good cooling
            },
            workload_pattern="variable",
            expected_problems=[
                "Excessive water usage during low load",
                "Suboptimal PUE (1.8+)",
                "High operational costs"
            ],
            rack_profiles=[
                {"type": "high_density_gpu", "id": "rack-gpu-01", "initial_cpu": 30.0, "initial_gpu": 25.0},
                {"type": "standard_compute", "id": "rack-cpu-01", "initial_cpu": 25.0, "initial_gpu": 10.0},
                {"type": "storage_heavy", "id": "rack-storage-01", "initial_cpu": 15.0, "initial_gpu": 5.0},
                {"type": "standard_compute", "id": "rack-cpu-02", "initial_cpu": 20.0, "initial_gpu": 8.0},
            ]
        )
    
    @staticmethod
    def capacity_planning_scenario() -> DataCenterScenario:
        """
        Scenario: Capacity Planning
        Problem: Gradual load increase over hours requires proactive cooling management
        Expected AI Action: Predictive cooling adjustments, workload distribution
        """
        return DataCenterScenario(
            name="Capacity Planning",
            description="Manage gradual workload increase while preventing thermal issues",
            duration_minutes=15,  # Reduced for faster testing
            num_racks=4,  # Reduced for faster testing
            initial_conditions={
                "ambient_temp_c": 24.0,
                "humidity_pct": 55.0,
                "cooling_efficiency": 0.90,
            },
            workload_pattern="gradual",
            expected_problems=[
                "Thermal buildup over time",
                "Risk of cooling capacity exhaustion",
                "Need for predictive management"
            ],
            rack_profiles=[
                {"type": "high_density_gpu", "id": "rack-gpu-01", "initial_cpu": 40.0, "initial_gpu": 35.0},
                {"type": "standard_compute", "id": "rack-cpu-01", "initial_cpu": 35.0, "initial_gpu": 15.0},
                {"type": "storage_heavy", "id": "rack-storage-01", "initial_cpu": 20.0, "initial_gpu": 5.0},
                {"type": "standard_compute", "id": "rack-cpu-02", "initial_cpu": 25.0, "initial_gpu": 8.0},
            ]
        )
    
    @staticmethod
    def emergency_response_scenario() -> DataCenterScenario:
        """
        Scenario: Emergency Response
        Problem: Cooling system partial failure requires immediate AI intervention
        Expected AI Action: Emergency cooling protocols, workload prioritization
        """
        return DataCenterScenario(
            name="Emergency Response",
            description="Respond to cooling system failure with immediate AI intervention",
            duration_minutes=5,  # Reduced for faster testing
            num_racks=3,  # Reduced for faster testing
            initial_conditions={
                "ambient_temp_c": 30.0,  # High ambient due to cooling issue
                "humidity_pct": 70.0,
                "cooling_efficiency": 0.60,  # Severely degraded cooling
                "cooling_failure": True,
            },
            workload_pattern="steady",
            expected_problems=[
                "Rapid temperature rise",
                "Risk of equipment damage",
                "Need for immediate intervention"
            ],
            rack_profiles=[
                {"type": "high_density_gpu", "id": "rack-gpu-01", "initial_cpu": 70.0, "initial_gpu": 65.0},
                {"type": "standard_compute", "id": "rack-cpu-01", "initial_cpu": 60.0, "initial_gpu": 20.0},
                {"type": "storage_heavy", "id": "rack-storage-01", "initial_cpu": 30.0, "initial_gpu": 8.0},
            ]
        )
    
    @staticmethod
    def generate_workload_curve(pattern: str, minutes: int, base_load: float) -> List[float]:
        """Generate realistic workload curves for different patterns"""
        workload = []
        
        if pattern == "steady":
            # Steady workload with minor fluctuations
            for i in range(minutes):
                noise = random.uniform(-5, 5)
                workload.append(max(0, min(100, base_load + noise)))
                
        elif pattern == "spike":
            # Sudden spike then recovery
            spike_start = minutes // 3
            spike_duration = minutes // 4
            for i in range(minutes):
                if spike_start <= i < spike_start + spike_duration:
                    spike = 30 + random.uniform(-5, 5)
                    workload.append(max(0, min(100, base_load + spike)))
                else:
                    noise = random.uniform(-3, 3)
                    workload.append(max(0, min(100, base_load + noise)))
                    
        elif pattern == "gradual":
            # Gradual increase over time
            for i in range(minutes):
                gradual_increase = (i / minutes) * 20
                noise = random.uniform(-2, 2)
                workload.append(max(0, min(100, base_load + gradual_increase + noise)))
                
        elif pattern == "variable":
            # Realistic variable workload (diurnal pattern)
            for i in range(minutes):
                # Simulate daily cycle
                cycle = 10 * (1 + 0.5 * ((i / minutes) * 2 * 3.14159))
                noise = random.uniform(-8, 8)
                workload.append(max(0, min(100, base_load + cycle + noise)))
        
        return workload
    
    @staticmethod
    def get_all_scenarios() -> List[DataCenterScenario]:
        """Get all available scenarios"""
        return [
            ScenarioGenerator.thermal_hotspot_scenario(),
            ScenarioGenerator.efficiency_optimization_scenario(),
            ScenarioGenerator.capacity_planning_scenario(),
            ScenarioGenerator.emergency_response_scenario(),
        ]