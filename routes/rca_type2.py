"""
Module: Simple Network Troubleshooting RCA (Type 2)
Purpose: Network-based anomaly analysis and device troubleshooting
Dependencies: config, db, utils, trigger_response route
"""

import logging
import random
from datetime import datetime

from config import Config
from db.database import get_db_session, close_db_session
from db.models.events import Event

logger = logging.getLogger(__name__)


def analyze_network_troubleshooting(log_id):
    """Analyze network issues using device troubleshooting"""
    try:
        # Get network metadata from database
        session = get_db_session()
        event = session.query(Event).filter(Event.log_id == log_id).first()

        if not event:
            close_db_session(session)
            return {'success': False, 'error': 'Event not found'}

        # Identify target device
        target_device = identify_target_device(event.src_ip, event.dst_ip)

        # Run network troubleshooting simulation
        troubleshoot_result = run_troubleshooting_simulation(target_device, event)

        close_db_session(session)

        if troubleshoot_result['anomaly_type']:
            logger.info(f"RCA Type 2 - Detected {troubleshoot_result['anomaly_type']} for log_id: {log_id}")

            # Forward to response system
            response_result = forward_to_response2(log_id, troubleshoot_result['anomaly_type'])

            return {
                'success': True,
                'anomaly_type': troubleshoot_result['anomaly_type'],
                'target_device': target_device,
                'troubleshoot_output': troubleshoot_result['output'],
                'response_triggered': response_result
            }
        else:
            logger.debug(f"RCA Type 2 - No network issues detected for log_id: {log_id}")
            return {
                'success': True,
                'anomaly_type': 'none',
                'target_device': target_device
            }

    except Exception as e:
        logger.error(f"Error in RCA Type 2 analysis: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def identify_target_device(src_ip, dst_ip):
    """Identify target device for troubleshooting"""
    try:
        # Check if source IP matches a known device
        device_name, device_config = Config.get_device_by_ip(src_ip)
        if device_name:
            return {
                'name': device_name,
                'ip': src_ip,
                'type': device_config['type'],
                'management_ip': device_config['management_ip']
            }

        # Check if destination IP matches a known device
        device_name, device_config = Config.get_device_by_ip(dst_ip)
        if device_name:
            return {
                'name': device_name,
                'ip': dst_ip,
                'type': device_config['type'],
                'management_ip': device_config['management_ip']
            }

        # Check VLAN membership
        vlan_name, vlan_config = Config.get_vlan_by_ip(src_ip)
        if vlan_name:
            return {
                'name': f"{vlan_name}_Device",
                'ip': src_ip,
                'type': 'vlan_device',
                'vlan': vlan_name,
                'router': vlan_config['router']
            }

        # Default to source IP
        return {
            'name': 'Unknown_Device',
            'ip': src_ip,
            'type': 'unknown'
        }

    except Exception as e:
        logger.error(f"Error identifying target device: {str(e)}")
        return {
            'name': 'Unknown_Device',
            'ip': src_ip,
            'type': 'unknown'
        }


def run_troubleshooting_simulation(target_device, event):
    """Simulate network troubleshooting execution"""
    try:
        # Simulate running different troubleshooting checks
        checks = [
            check_latency(target_device),
            check_error_rates(target_device),
            check_connectivity(target_device),
            check_packet_loss(target_device),
            check_interface_flapping(target_device)
        ]

        # Find the first anomaly detected
        for check in checks:
            if check['anomaly_detected']:
                return {
                    'anomaly_type': check['anomaly_type'],
                    'output': check['output'],
                    'severity': check['severity']
                }

        # No anomalies detected
        return {
            'anomaly_type': None,
            'output': 'All network checks passed - no issues detected',
            'severity': 'normal'
        }

    except Exception as e:
        logger.error(f"Error in troubleshooting simulation: {str(e)}")
        return {
            'anomaly_type': None,
            'output': f'Troubleshooting failed: {str(e)}',
            'severity': 'error'
        }


def check_latency(target_device):
    """Simulate latency check"""
    # Simulate ping results with some randomness
    avg_latency = random.uniform(1, 200)  # 1-200ms

    if avg_latency > 100:  # High latency threshold
        return {
            'anomaly_detected': True,
            'anomaly_type': 'high_latency',
            'output': f'High latency detected: {avg_latency:.2f}ms average',
            'severity': 'high' if avg_latency > 150 else 'medium'
        }

    return {
        'anomaly_detected': False,
        'output': f'Latency normal: {avg_latency:.2f}ms average'
    }


def check_error_rates(target_device):
    """Simulate error rate check"""
    # Simulate interface error rates
    error_rate = random.uniform(0, 10)  # 0-10% error rate

    if error_rate > 2:  # High error rate threshold
        return {
            'anomaly_detected': True,
            'anomaly_type': 'high_error_rates',
            'output': f'High error rate detected: {error_rate:.2f}% on interfaces',
            'severity': 'high' if error_rate > 5 else 'medium'
        }

    return {
        'anomaly_detected': False,
        'output': f'Error rates normal: {error_rate:.2f}%'
    }


def check_connectivity(target_device):
    """Simulate connectivity check"""
    # Simulate connectivity issues
    connectivity_success = random.choice([True, True, True, False])  # 75% success rate

    if not connectivity_success:
        return {
            'anomaly_detected': True,
            'anomaly_type': 'connectivity_issues',
            'output': f'Connectivity issues detected to {target_device["ip"]}',
            'severity': 'high'
        }

    return {
        'anomaly_detected': False,
        'output': f'Connectivity to {target_device["ip"]} is normal'
    }


def check_packet_loss(target_device):
    """Simulate packet loss check"""
    # Simulate packet loss percentage
    packet_loss = random.uniform(0, 15)  # 0-15% packet loss

    if packet_loss > 3:  # High packet loss threshold
        return {
            'anomaly_detected': True,
            'anomaly_type': 'packet_loss',
            'output': f'High packet loss detected: {packet_loss:.2f}%',
            'severity': 'high' if packet_loss > 8 else 'medium'
        }

    return {
        'anomaly_detected': False,
        'output': f'Packet loss normal: {packet_loss:.2f}%'
    }


def check_interface_flapping(target_device):
    """Simulate interface flapping check"""
    # Simulate interface stability
    flapping_detected = random.choice([False, False, False, True])  # 25% chance

    if flapping_detected:
        interface = random.choice(['GigabitEthernet0/1', 'FastEthernet1/0', 'eth0'])
        return {
            'anomaly_detected': True,
            'anomaly_type': 'flapping_links',
            'output': f'Interface flapping detected on {interface}',
            'severity': 'medium'
        }

    return {
        'anomaly_detected': False,
        'output': 'All interfaces stable - no flapping detected'
    }


def forward_to_response2(log_id, anomaly_type):
    """Forward to trigger_response2 route"""
    try:
        from routes.trigger_response import trigger_response2_internal
        return trigger_response2_internal(log_id, anomaly_type)

    except Exception as e:
        logger.error(f"Error forwarding to response2: {str(e)}")
        return {'error': str(e)}


def get_network_statistics():
    """Get network troubleshooting statistics"""
    try:
        from db.database import get_db_session, close_db_session
        from db.models.response import Response

        session = get_db_session()

        # Count responses by anomaly type 2
        type2_stats = {}

        latency_count = session.query(Response).filter(
            Response.anomaly_type2 == 'high_latency'
        ).count()

        error_count = session.query(Response).filter(
            Response.anomaly_type2 == 'high_error_rates'
        ).count()

        connectivity_count = session.query(Response).filter(
            Response.anomaly_type2 == 'connectivity_issues'
        ).count()

        packet_loss_count = session.query(Response).filter(
            Response.anomaly_type2 == 'packet_loss'
        ).count()

        flapping_count = session.query(Response).filter(
            Response.anomaly_type2 == 'flapping_links'
        ).count()

        type2_stats = {
            'high_latency': latency_count,
            'high_error_rates': error_count,
            'connectivity_issues': connectivity_count,
            'packet_loss': packet_loss_count,
            'flapping_links': flapping_count,
            'total': latency_count + error_count + connectivity_count + packet_loss_count + flapping_count
        }

        close_db_session(session)

        return {
            'success': True,
            'type2_statistics': type2_stats,
            'devices_monitored': len(Config.NETWORK_DEVICES),
            'vlans_monitored': len(Config.VLANS)
        }

    except Exception as e:
        logger.error(f"Error getting network statistics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }