"""
CloudSim adapter (SDD Phase 2, Section 13/15).

CloudSim-simulated workloads flow through the identical adapter pipeline as
OpenDC (same TelemetryReading/TwinState contract, same job lifecycle) —
only the `mode` tag on the resulting rows/job differs ('cloudsim' instead
of 'opendc'), which is exactly the pattern the ER diagram's `racks_config`
notes describe ("mode = laptop|opendc|cloudsim").
"""
from app.digital_twin.opendc_adapter import submit_job as _submit_job


def submit_job(db, spec: dict):
    spec = dict(spec)
    spec["mode"] = "cloudsim"
    return _submit_job(db, spec)
