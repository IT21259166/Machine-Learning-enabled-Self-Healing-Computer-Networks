"""
Module: Essential Utilities
Purpose: Logger, state manager, helper functions
Dependencies: logging, threading, datetime
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
import uuid

def setup_logger(level='INFO', log_dir=None):
    """Simple logger setup"""
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger('watchdog').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQL logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logging

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'app.log' if log_dir else 'app.log')
        ]
    )
    return logging.getLogger('anbd')

class StateManager:
    """Simple state management for monitoring status"""

    def __init__(self):
        self._monitoring = False
        self._lock = threading.Lock()
        self._start_time = None

    def is_monitoring(self):
        """Check if monitoring is active"""
        with self._lock:
            return self._monitoring

    def set_monitoring(self, status):
        """Set monitoring status"""
        with self._lock:
            self._monitoring = status
            if status:
                self._start_time = datetime.utcnow()
            else:
                self._start_time = None

    def get_status(self):
        """Get current status"""
        with self._lock:
            return 'running' if self._monitoring else 'stopped'

    def get_uptime(self):
        """Get uptime in seconds"""
        with self._lock:
            if self._start_time:
                return (datetime.utcnow() - self._start_time).total_seconds()
            return 0

def generate_log_id():
    """Generate unique log ID"""
    return f"log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

def generate_anomaly_id():
    """Generate unique anomaly ID"""
    return f"anomaly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

def format_timestamp(timestamp=None):
    """Format timestamp for display"""
    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def validate_ip(ip_address):
    """Simple IP validation"""
    import ipaddress
    try:
        ipaddress.ip_address(ip_address)
        return True
    except:
        return False

def sanitize_string(text, max_length=255):
    """Basic string sanitization"""
    if not isinstance(text, str):
        text = str(text)

    # Remove dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')

    return text[:max_length].strip()

def safe_int(value, default=0):
    """Safely convert to integer"""
    try:
        return int(value)
    except:
        return default

def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        return float(value)
    except:
        return default

class SimpleCache:
    """Basic in-memory cache"""

    def __init__(self, max_size=1000):
        self._cache = {}
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key):
        """Get value from cache"""
        with self._lock:
            return self._cache.get(key)

    def set(self, key, value):
        """Set value in cache"""
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Remove oldest item
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = value

    def clear(self):
        """Clear cache"""
        with self._lock:
            self._cache.clear()

# Global instances
state_manager = StateManager()
cache = SimpleCache()