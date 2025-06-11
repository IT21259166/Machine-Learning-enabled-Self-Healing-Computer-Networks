"""
Module: Response Table Model
Purpose: SQLAlchemy model for response actions
Dependencies: SQLAlchemy, database.py
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from db.database import db
from datetime import datetime
import json

class Response(db.Model):
    """Response actions table"""
    __tablename__ = 'responses'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Reference IDs
    log_id = Column(String(50), nullable=False, index=True)
    anomaly_id = Column(String(50), nullable=False, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Network metadata
    src_ip = Column(String(45), nullable=False)
    dst_ip = Column(String(45), nullable=False)
    src_port = Column(Integer)
    dst_port = Column(Integer)

    # RCA Type 1 (Rule-based)
    anomaly_type1 = Column(String(100))
    re_features = Column(Text)  # JSON string
    res_type1 = Column(String(100))

    # RCA Type 2 (Network troubleshooting)
    anomaly_type2 = Column(String(100))
    res_type2 = Column(String(100))

    # Execution status
    success = Column(Boolean, default=False)
    duration_ms = Column(Integer)  # Execution time in milliseconds

    def __repr__(self):
        return f'<Response {self.anomaly_id}: {self.anomaly_type1}/{self.anomaly_type2}>'

    def set_features(self, features_dict):
        """Set reFeatures as JSON string"""
        self.re_features = json.dumps(features_dict) if features_dict else None

    def get_features(self):
        """Get reFeatures as dictionary"""
        try:
            return json.loads(self.re_features) if self.re_features else {}
        except:
            return {}

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'log_id': self.log_id,
            'anomaly_id': self.anomaly_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'anomaly_type1': self.anomaly_type1,
            're_features': self.get_features(),
            'res_type1': self.res_type1,
            'anomaly_type2': self.anomaly_type2,
            'res_type2': self.res_type2,
            'success': self.success,
            'duration_ms': self.duration_ms
        }