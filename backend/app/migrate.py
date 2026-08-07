"""
Database migration for multi-device support.

Adds device_id columns to tables for device-specific data isolation.
"""
import logging
from app.database import SessionLocal, engine
from sqlalchemy import text

logger = logging.getLogger("aquamind.migrate")

def run_migration():
    """Add device_id columns to relevant tables."""
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