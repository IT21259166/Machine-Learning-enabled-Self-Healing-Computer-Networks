"""
Module: Simple Error Management
Purpose: Error handling decorators and retry logic
Dependencies: functools, time, logging
"""

import functools
import time
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def handle_exceptions(logger_instance=None):
    """Decorator to handle exceptions gracefully"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log = logger_instance or logger
                log.error(f"Error in {func.__name__}: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'function': func.__name__
                }

        return wrapper

    return decorator


def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """Decorator to retry function on failure"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1

                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise

                    logger.warning(f"Function {func.__name__} failed (attempt {retries}/{max_retries}): {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None

        return wrapper

    return decorator


def safe_execute(func, default_return=None, log_errors=True):
    """Safely execute a function with error handling"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execution failed: {str(e)}")
        return default_return


def validate_and_execute(validation_func, execution_func, *args, **kwargs):
    """Validate input then execute function"""
    try:
        # Run validation
        is_valid, validation_result = validation_func(*args, **kwargs)

        if not is_valid:
            return {
                'success': False,
                'error': f'Validation failed: {validation_result}'
            }

        # Execute main function
        result = execution_func(*args, **kwargs)
        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        logger.error(f"Validate and execute failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def timeout_handler(timeout_seconds):
    """Decorator to add timeout to functions"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal

            def timeout_callback(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")

            # Set timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_callback)
            signal.alarm(timeout_seconds)

            try:
                result = func(*args, **kwargs)
                return result
            except TimeoutError:
                logger.error(f"Function {func.__name__} timed out")
                raise
            finally:
                # Reset signal
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        return wrapper

    return decorator


def log_performance(func):
    """Decorator to log function performance"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # ms

            if execution_time > 1000:  # Log if > 1 second
                logger.warning(f"Slow execution: {func.__name__} took {execution_time:.2f}ms")
            else:
                logger.debug(f"Performance: {func.__name__} took {execution_time:.2f}ms")

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Function {func.__name__} failed after {execution_time:.2f}ms: {str(e)}")
            raise

    return wrapper


class ErrorCollector:
    """Simple error collection for batch operations"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, message, context=None):
        """Add an error"""
        error_entry = {
            'message': str(message),
            'context': context,
            'timestamp': time.time()
        }
        self.errors.append(error_entry)
        logger.error(f"Error collected: {message}")

    def add_warning(self, message, context=None):
        """Add a warning"""
        warning_entry = {
            'message': str(message),
            'context': context,
            'timestamp': time.time()
        }
        self.warnings.append(warning_entry)
        logger.warning(f"Warning collected: {message}")

    def has_errors(self):
        """Check if any errors were collected"""
        return len(self.errors) > 0

    def has_warnings(self):
        """Check if any warnings were collected"""
        return len(self.warnings) > 0

    def get_summary(self):
        """Get error summary"""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }

    def clear(self):
        """Clear all collected errors and warnings"""
        self.errors.clear()
        self.warnings.clear()


def safe_database_operation(operation_func, *args, **kwargs):
    """Safely execute database operations with rollback"""
    from db.database import get_db_session, close_db_session

    session = None
    try:
        session = get_db_session()
        result = operation_func(session, *args, **kwargs)
        session.commit()
        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Database operation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        if session:
            close_db_session(session)


def circuit_breaker(failure_threshold=5, recovery_timeout=60):
    """Simple circuit breaker pattern"""

    def decorator(func):
        func._failure_count = 0
        func._last_failure_time = 0
        func._state = 'closed'  # closed, open, half-open

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()

            # Check if circuit should recover
            if (func._state == 'open' and
                    current_time - func._last_failure_time > recovery_timeout):
                func._state = 'half-open'
                logger.info(f"Circuit breaker for {func.__name__} entering half-open state")

            # If circuit is open, fail fast
            if func._state == 'open':
                raise Exception(f"Circuit breaker open for {func.__name__}")

            try:
                result = func(*args, **kwargs)

                # Success - reset failure count
                if func._state == 'half-open':
                    func._state = 'closed'
                    func._failure_count = 0
                    logger.info(f"Circuit breaker for {func.__name__} closed")

                return result

            except Exception as e:
                func._failure_count += 1
                func._last_failure_time = current_time

                # Open circuit if threshold reached
                if func._failure_count >= failure_threshold:
                    func._state = 'open'
                    logger.error(f"Circuit breaker for {func.__name__} opened after {failure_threshold} failures")

                raise

        return wrapper

    return decorator


# Global error collector instance
error_collector = ErrorCollector()