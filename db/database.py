"""
Module: Database Connection & Management
Purpose: SQLAlchemy setup, session management, connection pooling
Security: Connection security, session cleanup, error handling
Dependencies: SQLAlchemy, Flask-SQLAlchemy, config
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from contextlib import contextmanager
import logging
import threading
from pathlib import Path

# Global SQLAlchemy instance
db = SQLAlchemy()

# Session factory
Session = None
engine = None
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and session management"""

    def __init__(self):
        self.engine = None
        self.Session = None
        self.db = db
        self._lock = threading.Lock()
        self._initialized = False

    def init_app(self, app):
        """Initialize database with Flask app"""
        global engine, Session

        with self._lock:
            if self._initialized:
                logger.warning("Database already initialized")
                return

            try:
                # Configure SQLAlchemy
                self.db.init_app(app)

                # Create engine with connection pooling
                engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})

                # Add security and performance settings
                engine_options.update({
                    'poolclass': QueuePool,
                    'pool_size': engine_options.get('pool_size', 5),
                    'max_overflow': engine_options.get('max_overflow', 10),
                    'pool_timeout': engine_options.get('pool_timeout', 30),
                    'pool_recycle': engine_options.get('pool_recycle', 3600),
                    'pool_pre_ping': engine_options.get('pool_pre_ping', True),
                    'echo': False  # Disable SQL echo to reduce logging
                })

                self.engine = create_engine(
                    app.config['DATABASE_URL'],
                    **engine_options
                )

                # Create session factory
                self.Session = scoped_session(
                    sessionmaker(
                        bind=self.engine,
                        autocommit=False,
                        autoflush=False
                    )
                )

                # Set global references
                engine = self.engine
                Session = self.Session

                # Set up event listeners
                self._setup_event_listeners()

                # Create database directory if using SQLite
                self._ensure_database_directory(app.config['DATABASE_URL'])

                with app.app_context():
                    # Import models so they're registered with SQLAlchemy
                    from db.models.events import Event
                    from db.models.response import Response

                    # Create all tables
                    self.db.create_all()

                    # Verify database connection
                    self._verify_connection()

                self._initialized = True
                logger.info("Database initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                raise

    def _ensure_database_directory(self, database_url):
        """Ensure database directory exists for SQLite"""
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            if '/' in db_path:  # Only create directory if path contains subdirectories
                db_dir = Path(db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Database directory created: {db_dir}")
            else:
                logger.info(f"Database will be created in current directory: {db_path}")

    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for monitoring"""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """Handle new database connections"""
            logger.debug("New database connection established")

            # Enable foreign keys for SQLite
            if 'sqlite' in str(self.engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            logger.debug("Database connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool"""
            logger.debug("Database connection checked in to pool")

        @event.listens_for(self.engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation"""
            logger.warning(f"Database connection invalidated: {exception}")

    def _verify_connection(self):
        """Verify database connection is working"""
        try:
            # Simple connection test using the engine directly
            with self.engine.connect() as conn:
                result = conn.execute(text('SELECT 1'))
                result.close()
            logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Database connection verification failed: {str(e)}")
            raise

    def get_session(self):
        """Get a new database session"""
        if not self._initialized or not self.Session:
            raise RuntimeError("Database not initialized")

        return self.Session()

    def remove_session(self):
        """Remove current session"""
        if self.Session:
            self.Session.remove()

    def close_all_sessions(self):
        """Close all database sessions"""
        if self.Session:
            self.Session.remove()

        if self.engine:
            self.engine.dispose()

    def get_engine_info(self):
        """Get database engine information"""
        if not self.engine:
            return None

        return {
            'url': str(self.engine.url),
            'driver': self.engine.driver,
            'pool_size': self.engine.pool.size(),
            'checked_out': self.engine.pool.checkedout(),
            'overflow': self.engine.pool.overflow(),
            'checked_in': self.engine.pool.checkedin()
        }

# Global database manager instance
db_manager = DatabaseManager()

def init_db(app):
    """Initialize database with Flask app"""
    db_manager.init_app(app)
    return db_manager

def get_db_session():
    """Get a new database session"""
    return db_manager.get_session()

def close_db_session(session=None):
    """Close database session"""
    if session:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
    else:
        db_manager.remove_session()

@contextmanager
def get_db_transaction():
    """Context manager for database transactions"""
    session = get_db_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction failed: {str(e)}")
        raise
    finally:
        close_db_session(session)

def execute_query(query, params=None, fetch_all=False):
    """Execute a raw SQL query safely"""
    with get_db_transaction() as session:
        try:
            if params:
                result = session.execute(text(query), params)
            else:
                result = session.execute(text(query))

            if fetch_all:
                return result.fetchall()
            else:
                return result.fetchone()

        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

def check_database_health():
    """Check database health and connectivity"""
    try:
        with get_db_transaction() as session:
            session.execute(text('SELECT 1'))

        engine_info = db_manager.get_engine_info()

        return {
            'status': 'healthy',
            'engine_info': engine_info,
            'connection_test': 'passed'
        }

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'connection_test': 'failed'
        }

def get_database_stats():
    """Get database statistics"""
    try:
        stats = {}

        # Get table row counts
        with get_db_transaction() as session:
            # Events table count
            try:
                result = session.execute(text('SELECT COUNT(*) FROM events'))
                stats['events_count'] = result.scalar()
            except:
                stats['events_count'] = 0

            # Responses table count
            try:
                result = session.execute(text('SELECT COUNT(*) FROM responses'))
                stats['responses_count'] = result.scalar()
            except:
                stats['responses_count'] = 0

        # Engine statistics
        engine_info = db_manager.get_engine_info()
        if engine_info:
            stats.update(engine_info)

        return stats

    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        return {}

def reset_database():
    """Reset database (drop and recreate all tables)"""
    try:
        logger.warning("Resetting database - all data will be lost")

        # Drop all tables
        db.drop_all()

        # Recreate all tables
        db.create_all()

        logger.info("Database reset completed")
        return True

    except Exception as e:
        logger.error(f"Database reset failed: {str(e)}")
        return False

def backup_database(backup_path):
    """Create database backup (SQLite only)"""
    try:
        if not str(engine.url).startswith('sqlite'):
            raise ValueError("Backup only supported for SQLite databases")

        import shutil

        # Get database file path
        db_path = str(engine.url).replace('sqlite:///', '')
        backup_path = Path(backup_path)

        # Create backup directory
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy database file
        shutil.copy2(db_path, backup_path)

        logger.info(f"Database backup created: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        return False

def restore_database(backup_path):
    """Restore database from backup (SQLite only)"""
    try:
        if not str(engine.url).startswith('sqlite'):
            raise ValueError("Restore only supported for SQLite databases")

        import shutil

        # Get database file path
        db_path = str(engine.url).replace('sqlite:///', '')
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Close all connections
        db_manager.close_all_sessions()

        # Copy backup file
        shutil.copy2(backup_path, db_path)

        # Reinitialize connection
        db_manager._verify_connection()

        logger.info(f"Database restored from: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"Database restore failed: {str(e)}")
        return False

class DatabaseError(Exception):
    """Custom database error class"""
    pass

class ConnectionError(DatabaseError):
    """Database connection error"""
    pass

class TransactionError(DatabaseError):
    """Database transaction error"""
    pass

# Error handling decorators
def handle_db_errors(func):
    """Decorator to handle database errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DisconnectionError as e:
            logger.error(f"Database disconnection error in {func.__name__}: {str(e)}")
            raise ConnectionError(f"Database connection lost: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise

    return wrapper

def retry_on_connection_error(max_retries=3, delay=1):
    """Decorator to retry database operations on connection errors"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (DisconnectionError, ConnectionError) as e:
                    if attempt == max_retries - 1:
                        raise

                    logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(delay * (attempt + 1))  # Exponential backoff

        return wrapper
    return decorator