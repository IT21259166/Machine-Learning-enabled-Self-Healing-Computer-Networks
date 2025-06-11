"""
Module: Configuration Management
Purpose: Centralized configuration for ANBD system
Security: Environment variables, secure defaults
Dependencies: os, pathlib
"""

import os
from pathlib import Path
from datetime import timedelta

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Base configuration class with secure defaults"""

    # Application Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'anbd-dev-key-change-in-production'
    DEBUG = False
    TESTING = False

    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/anbd.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL  # Flask-SQLAlchemy requires this key
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }

    # WebSocket Configuration
    WEBSOCKET_HOST = os.environ.get('WEBSOCKET_HOST') or 'localhost'
    WEBSOCKET_PORT = int(os.environ.get('WEBSOCKET_PORT') or 5000)
    WEBSOCKET_CORS_ALLOWED_ORIGINS = ['http://localhost:*', 'https://localhost:*']
    WEBSOCKET_PING_TIMEOUT = 60
    WEBSOCKET_PING_INTERVAL = 25

    # Data Generation Settings
    DATA_GENERATION_INTERVAL = int(os.environ.get('DATA_GENERATION_INTERVAL') or 120)  # 2 minutes
    DATA_DIRECTORY = BASE_DIR / 'data' / 'network_data'
    MAX_CSV_FILES = int(os.environ.get('MAX_CSV_FILES') or 100)

    # ML Model Configuration
    MODEL_PATH = BASE_DIR / 'model' / 'lstm_vae_model.keras'
    SCALER_PATH = BASE_DIR / 'model' / 'scaler.pkl'
    ANOMALY_THRESHOLD = float(os.environ.get('ANOMALY_THRESHOLD') or 0.5)
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE') or 32)

    # Feature Configuration (35 features for model)
    IMPORTANT_FEATURES = [
        'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
        'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
        'Fwd Packet Length Max', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
        'Bwd Packet Length Max', 'Bwd Packet Length Mean', 'Bwd Packet Length Std',
        'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean', 'Flow IAT Std',
        'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Total', 'Fwd Header Length',
        'Bwd Header Length', 'Min Packet Length', 'Max Packet Length',
        'Packet Length Mean', 'Packet Length Std', 'Packet Length Variance',
        'ACK Flag Count', 'Down/Up Ratio', 'Average Packet Size',
        'Avg Bwd Segment Size', 'Subflow Fwd Bytes', 'Init_Win_bytes_forward',
        'Init_Win_bytes_backward', 'Idle Mean', 'Idle Max', 'Idle Min'
    ]

    # RCA Type 1 Features (subset for rule-based analysis)
    RCA_TYPE1_FEATURES = [
        'Flow Duration', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
        'Flow Bytes/s', 'Flow Packets/s', 'Fwd Header Length', 'Bwd Header Length',
        'Max Packet Length', 'Packet Length Mean'
    ]

    # RCA Configuration
    RCA_TYPE1_THRESHOLDS = {
        'bandwidth_saturation': {
            'flow_bytes_per_sec': 1000000,  # 1MB/s
            'flow_packets_per_sec': 1000
        },
        'throughput_anomalies': {
            'total_fwd_packets': 10000,
            'total_bwd_packets': 10000
        },
        'unusual_header_length': {
            'fwd_header_length': 100,
            'bwd_header_length': 100
        },
        'unusual_packet_size': {
            'max_packet_length': 1500,
            'packet_length_mean': 1000
        },
        'unusual_flow_duration': {
            'flow_duration': 300000000  # 5 minutes in microseconds
        }
    }

    # Network Device Configuration
    NETWORK_DEVICES = {
        'CORE-RO-1': {
            'type': 'cisco_router',
            'management_ip': '192.168.61.1',
            'interfaces': {
                'FastEthernet0/0': '192.168.60.2',
                'FastEthernet1/0': '192.168.60.14',
                'FastEthernet1/1': '192.168.60.17',
                'FastEthernet2/0': '192.168.60.25',
                'FastEthernet2/1': '192.168.60.29',
                'FastEthernet3/0': '192.168.61.1'
            }
        },
        'CORE-RO-2': {
            'type': 'cisco_router',
            'management_ip': '192.168.60.26',
            'interfaces': {
                'FastEthernet1/0': '192.168.60.6',
                'FastEthernet0/0': '192.168.60.10',
                'FastEthernet1/1': '192.168.60.21',
                'FastEthernet2/0': '192.168.60.26',
                'FastEthernet2/1': '192.168.60.30'
            }
        },
        'DT-RO-1': {
            'type': 'cisco_router',
            'management_ip': '192.168.60.1',
            'interfaces': {
                'FastEthernet1/0': '192.168.60.1',
                'FastEthernet1/1': '192.168.60.5'
            }
        },
        'DT-RO-2': {
            'type': 'cisco_router',
            'management_ip': '192.168.60.9',
            'interfaces': {
                'FastEthernet1/0': '192.168.60.9',
                'FastEthernet1/1': '192.168.60.13'
            }
        },
        'EDGE-FW': {
            'type': 'cisco_asa',
            'management_ip': '192.168.60.18',
            'interfaces': {
                'GigabitEthernet0/0': '192.168.60.18',
                'GigabitEthernet0/1': '192.168.60.22',
                'GigabitEthernet0/2': '192.168.137.2'
            }
        },
        'Ubuntu-Gateway': {
            'type': 'linux_server',
            'management_ip': '192.168.61.2',
            'interfaces': {
                'eth0': '192.168.61.2'
            }
        }
    }

    # VLAN Configuration
    VLANS = {
        'VLAN10': {
            'subnet': '192.168.10.0/24',
            'gateway': '192.168.10.1',
            'devices': ['192.168.10.1', '192.168.10.2'],
            'switch': 'AC-SW-1',
            'router': 'DT-RO-1'
        },
        'VLAN20': {
            'subnet': '192.168.20.0/24',
            'gateway': '192.168.20.1',
            'devices': ['192.168.20.1', '192.168.20.2'],
            'switch': 'AC-SW-2',
            'router': 'DT-RO-1'
        },
        'VLAN30': {
            'subnet': '192.168.30.0/24',
            'gateway': '192.168.30.1',
            'devices': ['192.168.30.1', '192.168.30.2'],
            'switch': 'AC-SW-3',
            'router': 'DT-RO-2'
        },
        'VLAN40': {
            'subnet': '192.168.40.0/24',
            'gateway': '192.168.40.1',
            'devices': ['192.168.40.1', '192.168.40.2'],
            'switch': 'AC-SW-4',
            'router': 'DT-RO-2'
        }
    }

    # Playbook Configuration
    TROUBLESHOOT_PLAYBOOKS = {
        'high_latency': 'rca/troubleshoot_engine/playbooks/high_latency.yml',
        'high_error_rates': 'rca/troubleshoot_engine/playbooks/high_error_rates.yml',
        'flapping_links': 'rca/troubleshoot_engine/playbooks/flapping_links.yml',
        'connectivity_issues': 'rca/troubleshoot_engine/playbooks/connectivity_issues.yml',
        'packet_loss': 'rca/troubleshoot_engine/playbooks/packet_loss.yml'
    }

    RESPONSE_PLAYBOOKS = {
        'type1': {
            'bandwidth_saturation': 'response/playbooks/type1/bandwidth_saturation_fix.yml',
            'throughput_anomaly': 'response/playbooks/type1/throughput_anomaly_fix.yml',
            'header_length': 'response/playbooks/type1/header_length_fix.yml',
            'packet_size': 'response/playbooks/type1/packet_size_fix.yml',
            'flow_duration': 'response/playbooks/type1/flow_duration_fix.yml'
        },
        'type2': {
            'latency': 'response/playbooks/type2/latency_fix.yml',
            'error_rate': 'response/playbooks/type2/error_rate_fix.yml',
            'flapping_links': 'response/playbooks/type2/flapping_links_fix.yml',
            'connectivity': 'response/playbooks/type2/connectivity_fix.yml',
            'packet_loss': 'response/playbooks/type2/packet_loss_fix.yml'
        }
    }

    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_DIR = BASE_DIR / 'logs'
    LOG_FILES = {
        'app': LOG_DIR / 'app.log',
        'error': LOG_DIR / 'error.log',
        'playbook': LOG_DIR / 'playbook_execution.log',
        'performance': LOG_DIR / 'performance.log'
    }
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Security Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    SESSION_TIMEOUT = timedelta(hours=24)
    RATE_LIMIT_PER_MINUTE = 60

    # Processing Configuration
    MAX_CONCURRENT_PROCESSES = int(os.environ.get('MAX_CONCURRENT_PROCESSES') or 4)
    PROCESS_TIMEOUT = int(os.environ.get('PROCESS_TIMEOUT') or 300)  # 5 minutes
    QUEUE_MAX_SIZE = int(os.environ.get('QUEUE_MAX_SIZE') or 1000)

    # Monitoring Configuration
    HEALTH_CHECK_INTERVAL = 30  # seconds
    METRICS_RETENTION_DAYS = 30
    ALERT_THRESHOLDS = {
        'memory_usage_percent': 85,
        'disk_usage_percent': 90,
        'cpu_usage_percent': 80,
        'error_rate_percent': 5
    }

    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration"""
        # Create required directories
        cls.DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Ensure model directory exists
        cls.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_device_by_ip(cls, ip_address):
        """Get device configuration by IP address"""
        for device_name, device_config in cls.NETWORK_DEVICES.items():
            if device_config['management_ip'] == ip_address:
                return device_name, device_config
            for interface_ip in device_config['interfaces'].values():
                if interface_ip == ip_address:
                    return device_name, device_config
        return None, None

    @classmethod
    def get_vlan_by_ip(cls, ip_address):
        """Get VLAN configuration by IP address"""
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_address)
            for vlan_name, vlan_config in cls.VLANS.items():
                network = ipaddress.ip_network(vlan_config['subnet'])
                if ip in network:
                    return vlan_name, vlan_config
        except ValueError:
            pass
        return None, None

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'INFO'  # Changed from DEBUG to reduce noise

    # Relaxed thresholds for testing
    RCA_TYPE1_THRESHOLDS = {
        'bandwidth_saturation': {
            'flow_bytes_per_sec': 100000,  # 100KB/s
            'flow_packets_per_sec': 100
        },
        'throughput_anomalies': {
            'total_fwd_packets': 1000,
            'total_bwd_packets': 1000
        },
        'unusual_header_length': {
            'fwd_header_length': 50,
            'bwd_header_length': 50
        },
        'unusual_packet_size': {
            'max_packet_length': 1000,
            'packet_length_mean': 500
        },
        'unusual_flow_duration': {
            'flow_duration': 60000000  # 1 minute in microseconds
        }
    }

    # More frequent data generation for testing
    DATA_GENERATION_INTERVAL = 30  # 30 seconds

    # Shorter timeouts for testing
    PROCESS_TIMEOUT = 60  # 1 minute
    WEBSOCKET_PING_TIMEOUT = 30

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

    # Enhanced security for production
    SESSION_TIMEOUT = timedelta(hours=8)
    RATE_LIMIT_PER_MINUTE = 30

    # Performance optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20
    }

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

    # Use in-memory database for testing
    DATABASE_URL = 'sqlite:///:memory:'

    # Minimal intervals for testing
    DATA_GENERATION_INTERVAL = 5  # 5 seconds
    HEALTH_CHECK_INTERVAL = 5

    # Relaxed limits for testing
    MAX_CSV_FILES = 10
    QUEUE_MAX_SIZE = 100

# Configuration selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class by name"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    return config.get(config_name, config['default'])

def validate_config(config_class):
    """Validate configuration settings"""
    errors = []

    # Check required paths exist
    if not config_class.MODEL_PATH.parent.exists():
        errors.append(f"Model directory does not exist: {config_class.MODEL_PATH.parent}")

    # Validate network configuration
    for device_name, device_config in config_class.NETWORK_DEVICES.items():
        if 'type' not in device_config:
            errors.append(f"Device {device_name} missing type")
        if 'management_ip' not in device_config:
            errors.append(f"Device {device_name} missing management_ip")

    # Validate thresholds
    for anomaly_type, thresholds in config_class.RCA_TYPE1_THRESHOLDS.items():
        if not isinstance(thresholds, dict):
            errors.append(f"Invalid thresholds for {anomaly_type}")

    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    return True