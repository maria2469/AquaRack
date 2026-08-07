"""
CoolProp Real Physics Water Model for Data Center Cooling Thermodynamics.
Uses thermodynamic equations of state (CoolProp PropsSI) to compute real fluid heat capacities (Cp),
densities (rho), mass flow rates (m_dot), and latent heat evaporation rates.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("aquamind.coolprop")

try:
    import CoolProp.CoolProp as CP
    HAS_COOLPROP = True
except ImportError:
    HAS_COOLPROP = False
    logger.info("CoolProp python package not installed. Using pure thermodynamic physics fallback engine.")


class CoolPropWaterEngine:
    """
    Thermodynamic water model using real fluid equations of state.
    Calculates exact mass flow rate, enthalpy changes, and evaporative water consumption.
    """

    def __init__(self, fluid: str = "Water"):
        self.fluid = fluid

    def get_water_properties(self, temp_c: float, pressure_pa: float = 101325.0) -> Dict[str, float]:
        """
        Returns (specific_heat_J_kgK, density_kg_m3, enthalpy_J_kg) for water at given temperature and pressure.
        """
        temp_k = temp_c + 273.15
        if HAS_COOLPROP:
            try:
                cp = CP.PropsSI("C", "T", temp_k, "P", pressure_pa, self.fluid)
                rho = CP.PropsSI("D", "T", temp_k, "P", pressure_pa, self.fluid)
                h = CP.PropsSI("H", "T", temp_k, "P", pressure_pa, self.fluid)
                return {"cp": cp, "density": rho, "enthalpy": h, "coolprop_used": True}
            except Exception as exc:
                logger.warning("CoolProp calculation failed for T=%.1fC: %s. Using thermo fallback.", temp_c, exc)

        # Pure thermodynamic physics fallback
        # Cp of liquid water is ~4.184 kJ/kg.K, Density is ~997 kg/m^3
        cp_fallback = 4184.0 + (temp_c - 20.0) * 0.5  # Slight thermal variance
        rho_fallback = 997.0 - (temp_c - 20.0) * 0.25
        h_fallback = cp_fallback * temp_c
        return {"cp": cp_fallback, "density": rho_fallback, "enthalpy": h_fallback, "coolprop_used": False}

    def compute_thermodynamic_cooling(
        self,
        cooling_load_kw: float,
        inlet_temp_c: float = 18.0,
        outlet_temp_c: float = 28.0,
        ambient_temp_c: float = 25.0,
        relative_humidity_pct: float = 50.0,
        pressure_pa: float = 101325.0,
    ) -> Dict[str, Any]:
        """
        Computes fluid mass flow rate (kg/s), liquid circulation (L/hr),
        and latent evaporative water loss rate (L/hr) based on real fluid enthalpy.
        """
        # Validate inputs
        cooling_load_kw = max(0.0, cooling_load_kw)
        inlet_temp_c = max(0.0, min(100.0, inlet_temp_c))
        outlet_temp_c = max(0.0, min(100.0, outlet_temp_c))
        ambient_temp_c = max(-50.0, min(60.0, ambient_temp_c))
        relative_humidity_pct = max(0.0, min(100.0, relative_humidity_pct))
        pressure_pa = max(1000.0, pressure_pa)
        
        props_in = self.get_water_properties(inlet_temp_c, pressure_pa)
        props_out = self.get_water_properties(outlet_temp_c, pressure_pa)

        avg_cp = (props_in["cp"] + props_out["cp"]) / 2.0  # J / kg.K
        avg_density = (props_in["density"] + props_out["density"]) / 2.0  # kg / m^3

        # Prevent division by zero
        avg_cp = max(1000.0, avg_cp)  # Minimum realistic Cp
        avg_density = max(100.0, avg_density)  # Minimum realistic density
        
        delta_t = max(1.0, outlet_temp_c - inlet_temp_c)
        q_watts = cooling_load_kw * 1000.0

        # Mass flow rate m_dot = Q / (Cp * Delta_T) (kg / s)
        mass_flow_kg_s = q_watts / (avg_cp * delta_t)

        # Volumetric liquid circulation rate (L / hr) = (mass_flow / density) * 3600 * 1000
        volumetric_flow_l_hr = (mass_flow_kg_s / avg_density) * 3600.0 * 1000.0

        # Evaporative water loss estimation using latent heat of vaporization h_fg (~2260 kJ/kg)
        h_fg = 2260.0 * 1000.0  # J/kg
        # Evaporation fraction is proportional to wet bulb depression and cooling tower load
        evap_fraction = min(0.05, max(0.005, 0.015 * (1.0 + (ambient_temp_c - 20.0) / 30.0) * (1.0 - relative_humidity_pct / 100.0)))
        evaporative_water_l_hr = (q_watts / h_fg) * 3600.0 * 1000.0 * (1.0 + evap_fraction)

        wue_real = evaporative_water_l_hr / max(0.1, cooling_load_kw)

        return {
            "cooling_load_kw": round(cooling_load_kw, 4),
            "mass_flow_kg_s": round(mass_flow_kg_s, 4),
            "liquid_circulation_l_hr": round(volumetric_flow_l_hr, 2),
            "evaporative_water_l_hr": round(evaporative_water_l_hr, 2),
            "wue_real_physics": round(wue_real, 4),
            "cp_avg_j_kgk": round(avg_cp, 2),
            "water_density_kg_m3": round(avg_density, 2),
            "delta_t_c": delta_t,
            "coolprop_enabled": props_in["coolprop_used"],
        }


coolprop_engine = CoolPropWaterEngine()
