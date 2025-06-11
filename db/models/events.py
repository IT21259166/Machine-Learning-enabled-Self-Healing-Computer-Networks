"""
Module: Events Table Model
Purpose: SQLAlchemy model for network events
Dependencies: SQLAlchemy, database.py
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from db.database import db
from datetime import datetime

class Event(db.Model):
    """Network events table"""
    __tablename__ = 'events'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Event identification
    log_id = Column(String(50), unique=True, nullable=False, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Network metadata
    src_ip = Column(String(45), nullable=False, index=True)  # IPv4/IPv6
    dst_ip = Column(String(45), nullable=False, index=True)
    src_port = Column(Integer)
    dst_port = Column(Integer)

    # Anomaly status
    is_anomalous = Column(Boolean, default=False, index=True)

    def __repr__(self):
        return f'<Event {self.log_id}: {self.src_ip}->{self.dst_ip}>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'is_anomalous': self.is_anomalous
        }