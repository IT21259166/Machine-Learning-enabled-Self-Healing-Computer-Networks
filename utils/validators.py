"""
Module: Simple Input Validation
Purpose: Validate and sanitize user inputs
Dependencies: ipaddress, re
"""

import ipaddress
import re
import logging

logger = logging.getLogger(__name__)


def validate_ip_address(ip_str):
    """Validate IP address (IPv4 or IPv6)"""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return True, str(ip)
    except ValueError:
        return False, None


def validate_port(port_value):
    """Validate port number (1-65535)"""
    try:
        port = int(port_value)
        if 1 <= port <= 65535:
            return True, port
        return False, None
    except (ValueError, TypeError):
        return False, None


def validate_log_id(log_id):
    """Validate log ID format"""
    if not isinstance(log_id, str):
        return False

    # Check length and basic pattern
    if len(log_id) < 10 or len(log_id) > 100:
        return False

    # Check for valid characters (alphanumeric, underscore, hyphen)
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, log_id))


def sanitize_string(input_str, max_length=255):
    """Sanitize string input"""
    if not isinstance(input_str, str):
        input_str = str(input_str)

    # Remove dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\n', '\r', '\t']
    sanitized = input_str

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    # Limit length
    sanitized = sanitized[:max_length].strip()

    return sanitized


def validate_anomaly_type(anomaly_type):
    """Validate anomaly type"""
    valid_type1 = [
        'bandwidth_saturation', 'throughput_anomaly', 'header_length',
        'packet_size', 'flow_duration'
    ]

    valid_type2 = [
        'high_latency', 'high_error_rates', 'connectivity_issues',
        'packet_loss', 'flapping_links'
    ]

    return anomaly_type in (valid_type1 + valid_type2)


def validate_timestamp(timestamp_str):
    """Validate timestamp format"""
    try:
        from datetime import datetime
        # Try ISO format
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def validate_feature_value(value):
    """Validate numeric feature value"""
    try:
        num_value = float(value)
        # Check for reasonable bounds
        if -1e10 <= num_value <= 1e10:
            return True, num_value
        return False, 0.0
    except (ValueError, TypeError):
        return False, 0.0


def validate_pagination_params(page, per_page):
    """Validate pagination parameters"""
    try:
        page = int(page) if page else 1
        per_page = int(per_page) if per_page else 20

        # Ensure reasonable bounds
        page = max(1, page)
        per_page = max(1, min(per_page, 100))  # Max 100 items per page

        return True, page, per_page
    except (ValueError, TypeError):
        return False, 1, 20


def is_safe_filename(filename):
    """Check if filename is safe"""
    if not isinstance(filename, str):
        return False

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False

    # Check for reasonable length
    if len(filename) > 255:
        return False

    # Check for valid characters
    pattern = r'^[a-zA-Z0-9._-]+$'
    return bool(re.match(pattern, filename))


def validate_filter_params(filters):
    """Validate filter parameters"""
    if not isinstance(filters, dict):
        return {}

    validated = {}

    # Event type filter
    event_type = filters.get('type', 'all')
    if event_type in ['all', 'normal', 'anomalous']:
        validated['type'] = event_type

    # IP filter
    ip_filter = filters.get('ip', '')
    if ip_filter:
        validated['ip'] = sanitize_string(ip_filter, 45)  # Max IP length

    # Status filter
    status = filters.get('status', 'all')
    if status in ['all', 'success', 'failed', 'pending']:
        validated['status'] = status

    return validated


def validate_websocket_message(message):
    """Validate WebSocket message structure"""
    try:
        if not isinstance(message, dict):
            return False, "Message must be a dictionary"

        # Check required fields
        if 'type' not in message:
            return False, "Message must have 'type' field"

        message_type = message['type']
        if not isinstance(message_type, str):
            return False, "Message type must be string"

        # Validate message type
        valid_types = [
            'start_monitoring', 'stop_monitoring', 'get_events',
            'get_responses', 'heartbeat', 'get_overview_data'
        ]

        if message_type not in valid_types:
            return False, f"Invalid message type: {message_type}"

        # Validate data field if present
        if 'data' in message and not isinstance(message['data'], dict):
            return False, "Message data must be a dictionary"

        return True, "Valid message"

    except Exception as e:
        return False, f"Message validation error: {str(e)}"


def clean_csv_data(data_dict):
    """Clean and validate CSV data"""
    cleaned = {}

    for key, value in data_dict.items():
        # Sanitize key
        clean_key = sanitize_string(str(key), 100)

        # Validate and clean value
        if isinstance(value, (int, float)):
            # Numeric value
            is_valid, clean_value = validate_feature_value(value)
            cleaned[clean_key] = clean_value
        elif isinstance(value, str):
            # String value
            if 'ip' in key.lower():
                # IP address
                is_valid, clean_value = validate_ip_address(value)
                cleaned[clean_key] = clean_value if is_valid else 'unknown'
            elif 'port' in key.lower():
                # Port number
                is_valid, clean_value = validate_port(value)
                cleaned[clean_key] = clean_value if is_valid else None
            else:
                # Regular string
                cleaned[clean_key] = sanitize_string(value, 255)
        else:
            # Convert to string and sanitize
            cleaned[clean_key] = sanitize_string(str(value), 255)

    return cleaned


def validate_model_features(features_dict):
    """Validate ML model features"""
    from config import Config

    if not isinstance(features_dict, dict):
        return False, "Features must be a dictionary"

    required_features = Config.IMPORTANT_FEATURES
    validated_features = {}

    for feature in required_features:
        value = features_dict.get(feature, 0.0)
        is_valid, clean_value = validate_feature_value(value)
        validated_features[feature] = clean_value

    return True, validated_features