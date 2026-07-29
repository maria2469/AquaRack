"""
Digital Twin Engine (Phase 1 — laptop mode).
The same interface (simulate / estimate_utilisation / estimate_thermal_load)
is designed to be reused unchanged when Phase 2 adds an 'opendc' / 'cloudsim'
mode, per SDD Section 12.
"""
from dataclasses import dataclass

from app.schemas import TwinState


@dataclass
class RackProfile:
    rack_id: str
    capacity_kw: float
    node_count: int

    @classmethod
    def load_config(cls, rack_id: str, capacity_kw: float, node_count: int) -> "RackProfile":
        return cls(rack_id=rack_id, capacity_kw=capacity_kw, node_count=node_count)


class DigitalTwinEngine:
    """
    Scales a single device's utilisation into an equivalent rack-level
    thermal/power figure using a configurable synthetic RackProfile
    (SDD Section 12.2).
    """

    def __init__(self, rack_config: RackProfile, mode: str = "laptop"):
        self.rack_config = rack_config
        self.mode = mode
        self._last_reading = None

    def simulate(self, reading) -> TwinState:
        """
        reading: an object/row with cpu_pct, gpu_pct, ram_pct, fan_rpm attributes.
        """
        self._last_reading = reading
        utilisation = self.estimate_utilisation()
        thermal_load = self.estimate_thermal_load()
        power_draw = self._estimate_power_draw()
        return TwinState(
            rack_id=self.rack_config.rack_id,
            utilisation_pct=round(utilisation, 2),
            thermal_load_kw=round(thermal_load, 4),
            power_draw_kw=round(power_draw, 4),
            mode=self.mode,
        )

    def estimate_utilisation(self) -> float:
        """
        Blended utilisation signal: weighted average of CPU, GPU (if present)
        and RAM load — a simple but effective proxy for overall rack load.
        """
        if self._last_reading is None:
            return 0.0
        r = self._last_reading
        cpu = r.cpu_pct or 0.0
        ram = r.ram_pct or 0.0
        gpu = r.gpu_pct
        if gpu is not None:
            utilisation = (0.5 * cpu) + (0.3 * gpu) + (0.2 * ram)
        else:
            utilisation = (0.7 * cpu) + (0.3 * ram)
        return max(0.0, min(100.0, utilisation))

    def estimate_thermal_load(self) -> float:
        """
        thermal_load_kw is directly proportional to utilisation, scaled by
        the notional rack capacity (SDD Section 12.2 example: 80% CPU on a
        5kW/1-node profile -> proportional thermal load).
        """
        utilisation = self.estimate_utilisation()
        capacity = self.rack_config.capacity_kw * max(1, self.rack_config.node_count)
        return (utilisation / 100.0) * capacity

    def _estimate_power_draw(self) -> float:
        # Under steady state, IT power draw ~= thermal load (heat produced by
        # electrical work), consistent with the Water Model's assumption
        # in SDD Section 13.1.
        return self.estimate_thermal_load()
