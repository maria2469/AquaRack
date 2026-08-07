from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE memory_embeddings ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_embeddings_device_id ON memory_embeddings(device_id)"))
    print("Added device_id to memory_embeddings")
    
    db.execute(text("ALTER TABLE episodes ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_episodes_device_id ON episodes(device_id)"))
    print("Added device_id to episodes")
    
    db.execute(text("ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS device_id STRING NOT NULL DEFAULT 'device-default'"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_recommendations_device_id ON recommendations(device_id)"))
    print("Added device_id to recommendations")
    
    db.commit()
    print("Migration completed successfully")
except Exception as e:
    db.rollback()
    print(f"Migration failed: {e}")
finally:
    db.close()