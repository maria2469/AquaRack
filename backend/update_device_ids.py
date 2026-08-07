from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("UPDATE memory_embeddings SET device_id = 'device-brown-laptop' WHERE device_id = 'device-default'"))
    db.execute(text("UPDATE episodes SET device_id = 'device-brown-laptop' WHERE device_id = 'device-default'"))
    db.execute(text("UPDATE recommendations SET device_id = 'device-brown-laptop' WHERE device_id = 'device-default'"))
    db.commit()
    print("Updated existing records to device-brown-laptop")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()