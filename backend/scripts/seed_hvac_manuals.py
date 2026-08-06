import sys
import os
import logging
from sqlalchemy.orm import Session

# Ensure we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, init_db
from app.models_ext import HVACManual
from app.lib.embedder import embed_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MANUALS = [
    {
        "title": "HVAC SOP - Thermal Runaway Prevention",
        "content": "In the event of thermal runaway where GPU temperatures exceed 85°C and cooling load drops, immediately throttle HVAC fans to maximum (3000 RPM) and lower chiller setpoint to 18°C. Do not rely solely on fan speed if ambient temps are high."
    },
    {
        "title": "Data Center Workload Migration Policy",
        "content": "When a specific rack experiences persistent thermal throttling despite maximum HVAC output, the primary remediation strategy is workload migration. Move high-compute jobs (e.g., LLM Inference) from the stressed rack to a rack with lower utilization (< 50%) to balance thermal load."
    }
]

def seed_manuals():
    logger.info("Initializing database...")
    init_db()
    
    db: Session = SessionLocal()
    try:
        existing = db.query(HVACManual).count()
        if existing > 0:
            logger.info(f"Database already contains {existing} HVAC manuals. Skipping seed.")
            return

        logger.info("Seeding HVAC manuals for Operational RAG...")
        for m in MANUALS:
            embedding = embed_text(m["content"])
            manual = HVACManual(
                title=m["title"],
                content=m["content"],
                embedding=embedding
            )
            db.add(manual)
        
        db.commit()
        logger.info("Successfully seeded HVAC manuals.")
    except Exception as e:
        logger.error(f"Error seeding manuals: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_manuals()
