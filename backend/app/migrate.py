"""
Database migration for multi-device support and rack reasoning persistence.

Adds device_id columns to tables for device-specific data isolation.
Creates rack_reasoning_results table for fleet dashboard persistence.
Removes foreign key constraint from episodes.rack_id to support fleet reasoning.
"""
import logging
from app.database import SessionLocal, engine
from sqlalchemy import text

logger = logging.getLogger("aquamind.migrate")

def run_migration():
    """Add device_id columns to relevant tables and create rack reasoning results table."""
    db = SessionLocal()
    try:
        # Add device_id to memory_embeddings
        try:
            db.execute(text("ALTER TABLE memory_embeddings ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_embeddings_device_id ON memory_embeddings(device_id)"))
            print("Added device_id to memory_embeddings")
        except Exception as e:
            print(f"Error adding device_id to memory_embeddings: {e}")

        # Add device_id to episodes
        try:
            db.execute(text("ALTER TABLE episodes ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_episodes_device_id ON episodes(device_id)"))
            print("Added device_id to episodes")
        except Exception as e:
            print(f"Error adding device_id to episodes: {e}")

        # Add device_id to recommendations
        try:
            db.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_recommendations_device_id ON recommendations(device_id)"))
            print("Added device_id to recommendations")
        except Exception as e:
            print(f"Error adding device_id to recommendations: {e}")

        # Remove foreign key constraint from episodes.rack_id to support fleet reasoning
        try:
            # Drop the foreign key constraint if it exists
            db.execute(text("ALTER TABLE episodes DROP CONSTRAINT IF EXISTS episodes_rack_id_fkey"))
            print("Removed foreign key constraint from episodes.rack_id")
        except Exception as e:
            print(f"Error removing foreign key constraint: {e}")

        # Create rack_reasoning_results table
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS rack_reasoning_results (
                    result_id STRING PRIMARY KEY,
                    rack_id STRING NOT NULL,
                    device_id STRING NOT NULL,
                    is_laptop BOOLEAN NOT NULL DEFAULT FALSE,
                    success BOOLEAN NOT NULL DEFAULT FALSE,
                    cpu_factor FLOAT,
                    gpu_factor FLOAT,
                    ram_factor FLOAT,
                    cooling_efficiency FLOAT,
                    hardware_age FLOAT,
                    recommendation STRING,
                    rationale STRING,
                    expected_water_saving FLOAT,
                    confidence FLOAT,
                    reasoning_time_ms FLOAT,
                    run_id STRING,
                    api_response JSON,
                    reasoning_logs JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    INDEX idx_rack_reasoning_results_rack_id (rack_id),
                    INDEX idx_rack_reasoning_results_run_id (run_id)
                )
            """))
            print("Created rack_reasoning_results table")
        except Exception as e:
            print(f"Error creating rack_reasoning_results table: {e}")

        db.commit()
        print("Migration completed successfully")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

def run_migrations():
    """Legacy function name for compatibility - disabled since device_id migration already completed."""
    pass

if __name__ == "__main__":
    run_migration()