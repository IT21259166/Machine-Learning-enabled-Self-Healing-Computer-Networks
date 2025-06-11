"""
Module: Response Repository
Purpose: Response-specific database operations
Dependencies: base_repository, response model
"""

from db.repository.base_repository import BaseRepository
from db.models.response import Response
from db.database import get_db_session, close_db_session


class ResponseRepository(BaseRepository):
    """Repository for Response table operations"""

    def __init__(self):
        super().__init__(Response)

    def get_by_anomaly_id(self, anomaly_id):
        """Get response by anomaly ID"""
        session = get_db_session()
        try:
            return session.query(Response).filter(Response.anomaly_id == anomaly_id).first()
        finally:
            close_db_session(session)

    def get_by_log_id(self, log_id):
        """Get response by log ID"""
        session = get_db_session()
        try:
            return session.query(Response).filter(Response.log_id == log_id).first()
        finally:
            close_db_session(session)

    def get_paginated(self, page=1, per_page=20, filters=None):
        """Get paginated responses with filters"""
        session = get_db_session()
        try:
            query = session.query(Response)

            # Apply filters
            if filters:
                if filters.get('type') == 'type1':
                    query = query.filter(Response.anomaly_type1.isnot(None))
                elif filters.get('type') == 'type2':
                    query = query.filter(Response.anomaly_type2.isnot(None))

                if filters.get('status') == 'success':
                    query = query.filter(Response.success == True)
                elif filters.get('status') == 'failed':
                    query = query.filter(Response.success == False)

            total = query.count()
            offset = (page - 1) * per_page
            responses = query.order_by(Response.timestamp.desc()).offset(offset).limit(per_page).all()

            return {
                'responses': responses,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        finally:
            close_db_session(session)

    def get_success_rate(self):
        """Get overall success rate"""
        session = get_db_session()
        try:
            total = session.query(Response).count()
            successful = session.query(Response).filter(Response.success == True).count()

            if total == 0:
                return 0.0

            return (successful / total) * 100
        finally:
            close_db_session(session)

    def get_average_duration(self):
        """Get average response duration"""
        from sqlalchemy import func

        session = get_db_session()
        try:
            avg_duration = session.query(func.avg(Response.duration_ms)).scalar()
            return avg_duration or 0.0
        finally:
            close_db_session(session)


# Global instance
response_repo = ResponseRepository()