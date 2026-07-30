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
    thermal_load_kw: float
    ambient_temp: float
    humidity: float
    pue_thermal_overhead: float = 0.4
    wue_base: float = 1.0  # L/kWh baseline, industry benchmark ~0.5-2.0


class WaterModel:
    """
    compute_water_usage(load) and compute_cooling_demand() per the SDD
    Section 7 class diagram (WaterModel.compute_water_usage /
    compute_cooling_demand).
    """

    def __init__(self, ambient_temp: float, humidity: float, pue_thermal_overhead: float = 0.4):
        self.ambient_temp = ambient_temp
        self.humidity = humidity
        self.pue_thermal_overhead = pue_thermal_overhead

    def compute_cooling_demand(self, thermal_load_kw: float) -> float:
        """Q_cooling (kW) = thermal_load_kw * (1 + PUE_thermal_overhead)"""
        return thermal_load_kw * (1 + self.pue_thermal_overhead)

    def compute_pue(self) -> float:
        return round(1 + self.pue_thermal_overhead, 3)

    def compute_wue_factor(self) -> float:
        # WUE scales mildly with ambient conditions; base ~1.0 L/kWh,
        # clamped to the plausible industry band (0.5-2.0 L/kWh).
        factor = psychrometric_factor(self.ambient_temp, self.humidity)
        wue = 0.8 * (factor / 1.0)
        return round(max(0.5, min(2.0, wue)), 4)

    def compute_water_usage(self, thermal_load_kw: float) -> dict:
        """
        Water_L_per_hr = WUE * IT_Energy_kWh * f(ambient_temp, humidity)
        Returns the full set of derived metrics for persistence.
        """
        cooling_load_kw = self.compute_cooling_demand(thermal_load_kw)
        wue = self.compute_wue_factor()
        f_factor = psychrometric_factor(self.ambient_temp, self.humidity)
        # thermal_load_kw treated as IT_Equipment_Energy_kWh for a 1-hour window
        water_l_per_hr = wue * thermal_load_kw * f_factor
        return {
            "cooling_load_kw": round(cooling_load_kw, 4),
            "wue_factor": wue,
            "water_l_per_hr": round(water_l_per_hr, 4),
            "pue": self.compute_pue(),
        }
