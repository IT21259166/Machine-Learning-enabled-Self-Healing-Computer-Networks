"""
Module: Events Repository
Purpose: Events-specific database operations
Dependencies: base_repository, events model
"""

from db.repository.base_repository import BaseRepository
from db.models.events import Event
from db.database import get_db_session, close_db_session


class EventsRepository(BaseRepository):
    """Repository for Events table operations"""

    def __init__(self):
        super().__init__(Event)

    def get_by_log_id(self, log_id):
        """Get event by log ID"""
        session = get_db_session()
        try:
            return session.query(Event).filter(Event.log_id == log_id).first()
        finally:
            close_db_session(session)

    def get_paginated(self, page=1, per_page=20, filters=None):
        """Get paginated events with filters"""
        session = get_db_session()
        try:
            query = session.query(Event)

            # Apply filters
            if filters:
                if filters.get('type') == 'anomalous':
                    query = query.filter(Event.is_anomalous == True)
                elif filters.get('type') == 'normal':
                    query = query.filter(Event.is_anomalous == False)

                if filters.get('ip'):
                    ip_filter = filters['ip']
                    query = query.filter(
                        (Event.src_ip.contains(ip_filter)) |
                        (Event.dst_ip.contains(ip_filter))
                    )

            total = query.count()
            offset = (page - 1) * per_page
            events = query.order_by(Event.timestamp.desc()).offset(offset).limit(per_page).all()

            return {
                'events': events,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        finally:
            close_db_session(session)

    def get_recent_events(self, hours=1):
        """Get recent events within specified hours"""
        from datetime import datetime, timedelta

        session = get_db_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            return session.query(Event).filter(
                Event.timestamp >= cutoff_time
            ).order_by(Event.timestamp.desc()).all()
        finally:
            close_db_session(session)

    def count_anomalies(self):
        """Count total anomalous events"""
        session = get_db_session()
        try:
            return session.query(Event).filter(Event.is_anomalous == True).count()
        finally:
            close_db_session(session)


# Global instance
events_repo = EventsRepository()