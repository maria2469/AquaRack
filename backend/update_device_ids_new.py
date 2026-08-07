from app.database import SessionLocal
from sqlalchemy import text

# Generate the same device ID as the frontend would
import platform
import hashlib

def generate_device_id():
    system_info = f"{platform.system()}-{platform.machine()}-{platform.processor()}"
    try:
        system_info += f"-{platform.node()}"
    except:
        pass
    device_hash = hashlib.sha256(system_info.encode()).hexdigest()[:16]
    return f"device-{device_hash}"

new_device_id = generate_device_id()
print(f"Generated device ID: {new_device_id}")

db = SessionLocal()
try:
    # Update existing records to use the new device ID
    db.execute(text(f"UPDATE memory_embeddings SET device_id = '{new_device_id}' WHERE device_id = 'device-brown-laptop'"))
    db.execute(text(f"UPDATE episodes SET device_id = '{new_device_id}' WHERE device_id = 'device-brown-laptop'"))
    db.execute(text(f"UPDATE recommendations SET device_id = '{new_device_id}' WHERE device_id = 'device-brown-laptop'"))
    db.commit()
    print(f"Updated existing records to device ID: {new_device_id}")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()