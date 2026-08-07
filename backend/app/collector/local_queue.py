"""
CockroachDB-based telemetry queue.
Buffers telemetry readings if the API is unreachable and replays them,
in order, once connectivity returns.
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

Base = declarative_base()


class QueueItem(Base):
    __tablename__ = "telemetry_queue"
    
    id = Column(Integer, primary_key=True)
    payload = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)


class CockroachDBQueue:
    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=engine)
        self._init_db()
    
    def _init_db(self):
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def _get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def enqueue(self, payload: dict):
        with self._get_session() as session:
            item = QueueItem(
                payload=json.dumps(payload),
                created_at=datetime.utcnow()
            )
            session.add(item)
    
    def peek_batch(self, limit: int = 50):
        with self._get_session() as session:
            items = session.query(QueueItem).order_by(QueueItem.id.asc()).limit(limit).all()
            return [(item.id, json.loads(item.payload)) for item in items]
    
    def remove(self, row_id: int):
        with self._get_session() as session:
            session.query(QueueItem).filter(QueueItem.id == row_id).delete()
    
    def size(self) -> int:
        with self._get_session() as session:
            return session.query(QueueItem).count()
