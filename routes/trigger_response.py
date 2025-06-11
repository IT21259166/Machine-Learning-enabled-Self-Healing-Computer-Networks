"""
Module: Simple Response System
Purpose: Execute response playbooks for both RCA types
Dependencies: config, db, utils
"""

import logging
import random
import time
from datetime import datetime

from config import Config
from db.database import get_db_session, close_db_session
from db.models.events import Event
from db.models.response import Response
from utils.core import generate_anomaly_id

logger = logging.getLogger(__name__)


def trigger_response1_internal(log_id, anomaly_type, re_features):
    """Internal function for RCA Type 1 responses"""
    try:
        # Get network metadata from database
        session = get_db_session()
        event = session.query(Event).filter(Event.log_id == log_id).first()

        if not event:
            close_db_session(session)
            return {'success': False, 'error': 'Event not found'}

        # Generate anomaly ID
        anomaly_id = generate_anomaly_id()

        # Execute Type 1 response playbook
        response_result = execute_type1_response(anomaly_type, event)

        # Create response record
        response = Response(
            log_id=log_id,
            anomaly_id=anomaly_id,
            timestamp=datetime.utcnow(),
            src_ip=event.src_ip,
            dst_ip=event.dst_ip,
            src_port=event.src_port,
            dst_port=event.dst_port,
            anomaly_type1=anomaly_type,
            res_type1=response_result['response_type'],
            success=response_result['success'],
            duration_ms=response_result['duration_ms']
        )

        # Set reFeatures as JSON
        response.set_features(re_features)

        session.add(response)
        session.commit()

        close_db_session(session)

        # Send real-time update
        send_response_update(anomaly_id, response_result, 'type1')

        logger.info(f"Type 1 response completed for anomaly_id: {anomaly_id}")

        return {
            'success': True,
            'anomaly_id': anomaly_id,
            'response_result': response_result
        }

    except Exception as e:
        logger.error(f"Error in trigger_response1: {str(e)}")
        return {'success': False, 'error': str(e)}


def trigger_response2_internal(log_id, anomaly_type):
    """Internal function for RCA Type 2 responses"""
    try:
        # Get existing response record by log_id
        session = get_db_session()
        response = session.query(Response).filter(Response.log_id == log_id).first()

        if not response:
            close_db_session(session)
            return {'success': False, 'error': 'Response record not found'}

        # Execute Type 2 response playbook
        response_result = execute_type2_response(anomaly_type, response)

        # Update response record with Type 2 data
        response.anomaly_type2 = anomaly_type
        response.res_type2 = response_result['response_type']

        # Update success status (both types must succeed)
        if not response_result['success']:
            response.success = False

        session.commit()
        close_db_session(session)

        # Send real-time update
        send_response_update(response.anomaly_id, response_result, 'type2')

        logger.info(f"Type 2 response completed for anomaly_id: {response.anomaly_id}")

        return {
            'success': True,
            'anomaly_id': response.anomaly_id,
            'response_result': response_result
        }

    except Exception as e:
        logger.error(f"Error in trigger_response2: {str(e)}")
        return {'success': False, 'error': str(e)}


def execute_type1_response(anomaly_type, event):
    """Execute Type 1 response playbook simulation"""
    try:
        # Get playbook path from config
        playbook_path = Config.RESPONSE_PLAYBOOKS['type1'].get(anomaly_type)

        if not playbook_path:
            return {
                'success': False,
                'response_type': 'unknown',
                'duration_ms': 0,
                'error': f'No playbook found for {anomaly_type}'
            }

        # Simulate playbook execution
        start_time = time.time()

        # Simulate execution delay (1-5 seconds)
        execution_delay = random.uniform(1, 5)
        time.sleep(execution_delay)

        # Simulate response actions based on anomaly type
        response_actions = get_type1_response_actions(anomaly_type)

        # Simulate success/failure (90% success rate)
        success = random.choice([True] * 9 + [False])

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            'success': success,
            'response_type': response_actions['type'],
            'duration_ms': duration_ms,
            'actions_taken': response_actions['actions'],
            'playbook_used': playbook_path
        }

    except Exception as e:
        logger.error(f"Error executing Type 1 response: {str(e)}")
        return {
            'success': False,
            'response_type': 'error',
            'duration_ms': 0,
            'error': str(e)
        }


def execute_type2_response(anomaly_type, response_record):
    """Execute Type 2 response playbook simulation"""
    try:
        # Get playbook path from config
        playbook_path = Config.RESPONSE_PLAYBOOKS['type2'].get(anomaly_type)

        if not playbook_path:
            return {
                'success': False,
                'response_type': 'unknown',
                'duration_ms': 0,
                'error': f'No playbook found for {anomaly_type}'
            }

        # Simulate playbook execution
        start_time = time.time()

        # Simulate execution delay (2-8 seconds for network operations)
        execution_delay = random.uniform(2, 8)
        time.sleep(execution_delay)

        # Simulate response actions based on anomaly type
        response_actions = get_type2_response_actions(anomaly_type)

        # Simulate success/failure (85% success rate for network operations)
        success = random.choice([True] * 85 + [False] * 15)

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            'success': success,
            'response_type': response_actions['type'],
            'duration_ms': duration_ms,
            'actions_taken': response_actions['actions'],
            'playbook_used': playbook_path
        }

    except Exception as e:
        logger.error(f"Error executing Type 2 response: {str(e)}")
        return {
            'success': False,
            'response_type': 'error',
            'duration_ms': 0,
            'error': str(e)
        }


def get_type1_response_actions(anomaly_type):
    """Get simulated response actions for Type 1 anomalies"""
    actions_map = {
        'bandwidth_saturation': {
            'type': 'bandwidth_optimization',
            'actions': ['Applied traffic shaping', 'Enabled QoS policies', 'Increased buffer sizes']
        },
        'throughput_anomaly': {
            'type': 'throughput_optimization',
            'actions': ['Optimized TCP window size', 'Adjusted flow control', 'Updated routing metrics']
        },
        'header_length': {
            'type': 'header_normalization',
            'actions': ['Applied header compression', 'Filtered malformed packets', 'Updated protocol settings']
        },
        'packet_size': {
            'type': 'packet_optimization',
            'actions': ['Configured MTU discovery', 'Applied fragmentation rules', 'Optimized packet sizes']
        },
        'flow_duration': {
            'type': 'flow_management',
            'actions': ['Adjusted connection timeouts', 'Applied flow limits', 'Optimized session handling']
        }
    }

    return actions_map.get(anomaly_type, {
        'type': 'generic_fix',
        'actions': ['Applied generic mitigation']
    })


def get_type2_response_actions(anomaly_type):
    """Get simulated response actions for Type 2 anomalies"""
    actions_map = {
        'high_latency': {
            'type': 'latency_mitigation',
            'actions': ['Optimized routing paths', 'Adjusted interface priorities', 'Applied traffic prioritization']
        },
        'high_error_rates': {
            'type': 'error_correction',
            'actions': ['Reset interface counters', 'Applied error correction', 'Updated interface configuration']
        },
        'connectivity_issues': {
            'type': 'connectivity_restore',
            'actions': ['Restarted network services', 'Cleared ARP tables', 'Applied routing updates']
        },
        'packet_loss': {
            'type': 'loss_prevention',
            'actions': ['Increased buffer sizes', 'Applied packet prioritization', 'Optimized queue management']
        },
        'flapping_links': {
            'type': 'link_stabilization',
            'actions': ['Applied dampening policies', 'Stabilized interface', 'Updated link parameters']
        }
    }

    return actions_map.get(anomaly_type, {
        'type': 'generic_network_fix',
        'actions': ['Applied generic network mitigation']
    })


def send_response_update(anomaly_id, response_result, response_type):
    """Send real-time response update via WebSocket"""
    try:
        from app import send_real_time_update

        update_data = {
            'anomaly_id': anomaly_id,
            'response_type': response_type,
            'success': response_result['success'],
            'duration_ms': response_result['duration_ms'],
            'actions_taken': response_result.get('actions_taken', [])
        }

        send_real_time_update('response_executed', update_data)

    except Exception as e:
        logger.error(f"Error sending response update: {str(e)}")


def get_response_statistics():
    """Get response execution statistics"""
    try:
        session = get_db_session()

        # Overall statistics
        total_responses = session.query(Response).count()
        successful_responses = session.query(Response).filter(Response.success == True).count()

        # Success rate
        success_rate = 0
        if total_responses > 0:
            success_rate = (successful_responses / total_responses) * 100

        # Average duration
        from sqlalchemy import func
        avg_duration = session.query(func.avg(Response.duration_ms)).scalar() or 0

        # Type 1 vs Type 2 counts
        type1_count = session.query(Response).filter(Response.anomaly_type1.isnot(None)).count()
        type2_count = session.query(Response).filter(Response.anomaly_type2.isnot(None)).count()

        close_db_session(session)

        return {
            'total_responses': total_responses,
            'successful_responses': successful_responses,
            'success_rate_percent': round(success_rate, 2),
            'average_duration_ms': round(avg_duration, 2),
            'type1_responses': type1_count,
            'type2_responses': type2_count
        }

    except Exception as e:
        logger.error(f"Error getting response statistics: {str(e)}")
        return {'error': str(e)}