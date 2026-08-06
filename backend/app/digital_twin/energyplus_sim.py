"""
EnergyPlus Data Center Digital Twin Simulator & Google Cluster Trace Workload Generator.
Simulates facility HVAC, CRAH (Computer Room Air Handler), chilled water loops, and PUE dynamics.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional


class GoogleClusterTraceGenerator:
    """
    Simulates server workload dynamics based on Google Cluster Trace v2 patterns:
    combines diurnal cyclic load baseline with stochastic task arrival bursts.
    """

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def generate_step(self, step_idx: int) -> Dict[str, float]:
        """Generates CPU %, GPU %, and Memory % for step_idx (minute/tick)."""
        # 24-hour diurnal cycle (1440 ticks per day)
        hour = (step_idx % 1440) / 60.0
        diurnal = 0.45 + 0.35 * math.sin((hour - 8.0) * math.pi / 12.0)  # Peak around 14:00

        # Poisson burst simulation (batch jobs)
        burst = random.expovariate(0.2) if random.random() < 0.15 else 0.0

        cpu_pct = max(10.0, min(99.0, (diurnal * 70.0) + (burst * 15.0) + random.uniform(-3.0, 3.0)))
        gpu_pct = max(5.0, min(100.0, (diurnal * 80.0) + (burst * 25.0) + random.uniform(-5.0, 5.0)))
        ram_pct = max(20.0, min(95.0, (diurnal * 60.0) + random.uniform(-2.0, 2.0)))

        return {
            "step": step_idx,
            "hour": round(hour, 2),
            "cpu_pct": round(cpu_pct, 2),
            "gpu_pct": round(gpu_pct, 2),
            "ram_pct": round(ram_pct, 2),
        }


class EnergyPlusDigitalTwinSimulator:
    """
    Digital Twin adapter modeling EnergyPlus DataCenterHVAC parameters.
    Simulates CRAH supply air temperature, chiller COP, cooling tower fan power, and facility PUE.
    """

    def __init__(self, rack_capacity_kw: float = 5.0, num_racks: int = 10):
        self.rack_capacity_kw = rack_capacity_kw
        self.num_racks = num_racks
        self.workload_gen = GoogleClusterTraceGenerator()
        # EnergyPlus IDF DataCenterHVAC template baseline parameters
        self.crah_supply_temp_c = 18.0
        self.chiller_cop_baseline = 4.5  # Coefficient of Performance
        self.chilled_water_setpoint_c = 7.0

    def simulate_step(
        self,
        step_idx: int,
        ambient_temp_c: float = 25.0,
        humidity_pct: float = 50.0,
    ) -> Dict[str, Any]:
        """Runs one physics simulation step of the facility."""
        workload = self.workload_gen.generate_step(step_idx)

        # Total IT Power (kW) across racks
        rack_load_pct = (workload["cpu_pct"] * 0.4 + workload["gpu_pct"] * 0.6) / 100.0
        it_power_kw = self.rack_capacity_kw * self.num_racks * (0.2 + 0.8 * rack_load_pct)

        # EnergyPlus Chiller COP model adjust based on ambient temp & return water temp
        cop_adj = max(2.5, self.chiller_cop_baseline - 0.05 * max(0.0, ambient_temp_c - 20.0))
        chiller_power_kw = it_power_kw / cop_adj

        # CRAH fan power (proportional to cube of airflow rate)
        crah_fan_power_kw = 0.05 * it_power_kw * (1.0 + 0.2 * (workload["cpu_pct"] / 100.0) ** 3)

        total_facility_power_kw = it_power_kw + chiller_power_kw + crah_fan_power_kw
        pue = total_facility_power_kw / max(0.1, it_power_kw)

        return {
            "step": step_idx,
            "workload": workload,
            "it_power_kw": round(it_power_kw, 2),
            "chiller_power_kw": round(chiller_power_kw, 2),
            "crah_fan_power_kw": round(crah_fan_power_kw, 2),
            "total_facility_power_kw": round(total_facility_power_kw, 2),
            "pue": round(pue, 3),
            "chiller_cop": round(cop_adj, 2),
            "crah_supply_temp_c": self.crah_supply_temp_c,
            "ambient_temp_c": ambient_temp_c,
            "humidity_pct": humidity_pct,
        }


energyplus_sim = EnergyPlusDigitalTwinSimulator()
