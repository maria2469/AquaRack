"""
Memory Lifecycle — "Age and Retire" (SDD Phase 2, Section 12.2):
  Age:   a scheduled job re-tiers memories hot -> warm -> cold based on age.
  Retire: cold memories are exported via CDC to S3 and an audit_log entry
          is recorded for the export.

In AWS this is a scheduled Lambda (Section 4.1 / 23, week 9). Locally it's
a plain function you can invoke on demand, from a cron entry, or wired
into APScheduler — no extra infra required to see the full lifecycle work
end-to-end, consistent with Phase 1's zero-mandatory-cloud-dependency
principle carried into Phase 2.

The S3 export uses the real Amazon S3 service when S3_ENABLED=true and
AWS credentials are configured, with automatic local disk fallback for
development when AWS is unavailable.

Usage (from the repo root, with phase1_standalone importable):
    PYTHONPATH=phase1_standalone:. python -m phase2_distributed.memory_tiering.retier_job
"""
from datetime import datetime, timedelta

from app import models
from app.database import SessionLocal

from app.models_ext import CDCExportLog
from app.lib.s3_client import export_cold_memory

HOT_WINDOW = timedelta(hours=24)
WARM_WINDOW = timedelta(days=90)


def _export_to_lake(memory: models.Memory, now: datetime) -> str:
    """Exports the cold-tier memory to real Amazon S3 (when S3_ENABLED=true and
    boto3/credentials are available) or a local JSON fallback otherwise,
    and returns the s3:// URI recorded in cdc_export_log. See
    app.lib.s3_client for the dual-mode implementation."""
    return export_cold_memory(
        memory_id=memory.memory_id,
        mem_type=memory.type,
        summary_text=memory.summary_text,
        created_at=memory.created_at,
        now=now,
    )


def retier_memories(db=None, now=None) -> dict:
    """
    Re-tiers every memory row by age and exports newly-cold memories to Amazon S3
    (or local fallback when S3 unavailable). Returns a summary dict of counts,
    useful for logging/tests. Safe to call repeatedly (idempotent export — a
    memory is only exported once, tracked via CDCExportLog).
    """
    own_session = db is None
    db = db or SessionLocal()
    now = now or datetime.utcnow()

    counts = {"hot": 0, "warm": 0, "cold": 0, "exported": 0}

    try:
        memories = db.query(models.Memory).all()
        for memory in memories:
            age = now - memory.created_at
            if age <= HOT_WINDOW:
                new_tier = "hot"
            elif age <= WARM_WINDOW:
                new_tier = "warm"
            else:
                new_tier = "cold"

            if new_tier != memory.tier:
                memory.tier = new_tier
            counts[new_tier] += 1

            if new_tier == "cold":
                already_exported = (
                    db.query(CDCExportLog).filter(CDCExportLog.memory_id == memory.memory_id).first()
                )
                if not already_exported:
                    s3_uri = _export_to_lake(memory, now)
                    db.add(CDCExportLog(memory_id=memory.memory_id, s3_uri=s3_uri))
                    db.add(
                        models.AuditLog(
                            actor="cdc_export_job", action="memory.cdc_export", entity_ref=memory.memory_id
                        )
                    )
                    counts["exported"] += 1

        db.commit()
    finally:
        if own_session:
            db.close()

    return counts


if __name__ == "__main__":
    result = retier_memories()
    print(f"[retier_job] Memory tiering complete: {result}")