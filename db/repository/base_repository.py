"""
Module: Base Repository
Purpose: Common CRUD operations for all models
Dependencies: SQLAlchemy, database
"""

from db.database import get_db_session, close_db_session


class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, model_class):
        self.model_class = model_class

    def create(self, **kwargs):
        """Create new record"""
        session = get_db_session()
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    def get_by_id(self, record_id):
        """Get record by ID"""
        session = get_db_session()
        try:
            return session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).first()
        finally:
            close_db_session(session)

    def get_all(self, limit=100):
        """Get all records with limit"""
        session = get_db_session()
        try:
            return session.query(self.model_class).limit(limit).all()
        finally:
            close_db_session(session)

    def update(self, record_id, **kwargs):
        """Update record"""
        session = get_db_session()
        try:
            session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).update(kwargs)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    def delete(self, record_id):
        """Delete record"""
        session = get_db_session()
        try:
            session.query(self.model_class).filter(
                self.model_class.id == record_id
            ).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)