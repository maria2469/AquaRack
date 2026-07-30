"""
Water Thermodynamic Model (SDD Section 13).
Converts the Digital Twin's thermal load into cooling energy demand and an
estimated water consumption rate, using standard data-centre efficiency
metrics (PUE, WUE) plus a simplified psychrometric evaporation factor.
"""
from dataclasses import dataclass

# Simplified ASHRAE-derived lookup table: f(ambient_temp_C, humidity_pct)
# Higher temp / lower humidity -> higher evaporative water demand.
_PSYCHRO_TABLE = [
    # (temp_C_upper_bound, humidity_pct_upper_bound, factor)
    (15, 100, 0.6),
    (20, 100, 0.75),
    (25, 70, 0.9),
    (25, 100, 0.8),
    (30, 50, 1.2),
    (30, 100, 1.0),
    (35, 40, 1.5),
    (35, 100, 1.2),
    (999, 999, 1.6),
]


def psychrometric_factor(ambient_temp: float, humidity: float) -> float:
    for temp_bound, hum_bound, factor in _PSYCHRO_TABLE:
        if ambient_temp <= temp_bound and humidity <= hum_bound:
            return factor
    return 1.6


@dataclass
class WaterModelInput:
    cpu_pct: float
    gpu_pct: float
    ambient_temp: float
    humidity: float
    wind_speed: float = 5.0
    pressure: float = 1013.25
    thermal_load_kw: float = 5.0
    cooling_strategy: str = "hybrid_evaporative"  # hybrid_evaporative | chilled_water | direct_liquid
    historical_efficiency: float = 1.0
    pue_thermal_overhead: float = 0.4
    wue_base: float = 1.0  # L/kWh baseline


class WaterModel:
    """
    Enhanced Thermodynamic Water & Cooling Model for AI Data Centers.
    Calculates evaporative losses, heat dissipation from CPU/GPU, environmental factors (wind, pressure),
    and cooling savings based on AI-selected cooling strategy.
    """

    STRATEGY_DISCOUNTS = {
        "hybrid_evaporative": 0.18,  # 18% savings
        "chilled_water": 0.08,        # 8% savings
        "direct_liquid": 0.32,        # 32% savings
    }

    def __init__(
        self,
        ambient_temp: float,
        humidity: float,
        wind_speed: float = 5.0,
        pressure: float = 1013.25,
        pue_thermal_overhead: float = 0.4,
        cooling_strategy: str = "hybrid_evaporative",
    ):
        self.ambient_temp = ambient_temp
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.pressure = pressure
        self.pue_thermal_overhead = pue_thermal_overhead
        self.cooling_strategy = cooling_strategy

    def compute_cooling_demand(self, thermal_load_kw: float) -> float:
        """Q_cooling (kW) = thermal_load_kw * (1 + PUE_thermal_overhead)"""
        return thermal_load_kw * (1 + self.pue_thermal_overhead)

    def compute_pue(self) -> float:
        return round(1 + self.pue_thermal_overhead, 3)

    def compute_wue_factor(self) -> float:
        factor = psychrometric_factor(self.ambient_temp, self.humidity)
        # Higher wind accelerates evaporation slightly, pressure compensates
        wind_adj = 1.0 + (self.wind_speed / 100.0)
        wue = 0.8 * (factor / 1.0) * wind_adj
        return round(max(0.5, min(2.5, wue)), 4)

    def compute_water_usage(self, thermal_load_kw: float, cpu_pct: float = 50.0, gpu_pct: float = 50.0) -> dict:
        """
        Calculates IT Thermal Load, Water Consumption (L/hr), Cooling Demand (kW),
        Cooling Cost ($/hr), and Expected Water Savings (%).
        """
        # Dynamic thermal load calculation based on CPU and GPU utilization if provided
        effective_load = thermal_load_kw * (0.3 + 0.3 * (cpu_pct / 100.0) + 0.4 * (gpu_pct / 100.0))
        cooling_load_kw = self.compute_cooling_demand(effective_load)
        wue = self.compute_wue_factor()
        f_factor = psychrometric_factor(self.ambient_temp, self.humidity)
        
        raw_water_l_hr = wue * effective_load * f_factor
        
        # Apply cooling strategy reduction
        saving_pct = self.STRATEGY_DISCOUNTS.get(self.cooling_strategy, 0.15) * 100.0
        optimized_water_l_hr = raw_water_l_hr * (1.0 - (saving_pct / 100.0))
        
        # Estimated cost per 1000 Liters + electricity cost ($0.005/L water + $0.12/kWh cooling)
        cooling_cost = (optimized_water_l_hr * 0.005) + (cooling_load_kw * 0.12)
        
        return {
            "cooling_load_kw": round(cooling_load_kw, 4),
            "wue_factor": wue,
            "water_l_per_hr": round(optimized_water_l_hr, 4),
            "baseline_water_l_per_hr": round(raw_water_l_hr, 4),
            "water_saving_pct": round(saving_pct, 2),
            "cooling_cost_usd": round(cooling_cost, 2),
            "pue": self.compute_pue(),
            "ambient_temp": self.ambient_temp,
            "humidity": self.humidity,
        }

