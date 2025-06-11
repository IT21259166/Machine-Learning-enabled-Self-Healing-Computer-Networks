"""
Module: Simple Rule-based RCA (Type 1)
Purpose: Threshold-based anomaly classification
Dependencies: config, utils, trigger_response route
"""

import logging
from config import Config

logger = logging.getLogger(__name__)


def analyze_rule_based(log_id, re_features):
    """Analyze features using rule-based thresholds"""
    try:
        # Get thresholds from config
        thresholds = Config.RCA_TYPE1_THRESHOLDS

        anomaly_type = classify_anomaly_type(re_features, thresholds)

        if anomaly_type:
            logger.info(f"RCA Type 1 - Detected {anomaly_type} for log_id: {log_id}")

            # Forward to response system
            response_result = forward_to_response1(log_id, anomaly_type, re_features)

            return {
                'success': True,
                'anomaly_type': anomaly_type,
                'features_analyzed': re_features,
                'response_triggered': response_result
            }
        else:
            logger.debug(f"RCA Type 1 - No specific anomaly type identified for log_id: {log_id}")
            return {
                'success': True,
                'anomaly_type': 'unknown',
                'features_analyzed': re_features
            }

    except Exception as e:
        logger.error(f"Error in RCA Type 1 analysis: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def classify_anomaly_type(features, thresholds):
    """Classify anomaly type based on feature thresholds"""

    # Check bandwidth saturation
    if (features.get('Flow Bytes/s', 0) > thresholds['bandwidth_saturation']['flow_bytes_per_sec'] or
            features.get('Flow Packets/s', 0) > thresholds['bandwidth_saturation']['flow_packets_per_sec']):
        return 'bandwidth_saturation'

    # Check throughput anomalies
    if (features.get('Total Length of Fwd Packets', 0) > thresholds['throughput_anomalies']['total_fwd_packets'] or
            features.get('Total Length of Bwd Packets', 0) > thresholds['throughput_anomalies']['total_bwd_packets']):
        return 'throughput_anomaly'

    # Check unusual header length
    if (features.get('Fwd Header Length', 0) > thresholds['unusual_header_length']['fwd_header_length'] or
            features.get('Bwd Header Length', 0) > thresholds['unusual_header_length']['bwd_header_length']):
        return 'header_length'

    # Check unusual packet size
    if (features.get('Max Packet Length', 0) > thresholds['unusual_packet_size']['max_packet_length'] or
            features.get('Packet Length Mean', 0) > thresholds['unusual_packet_size']['packet_length_mean']):
        return 'packet_size'

    # Check unusual flow duration
    if features.get('Flow Duration', 0) > thresholds['unusual_flow_duration']['flow_duration']:
        return 'flow_duration'

    # No specific type identified
    return None


def forward_to_response1(log_id, anomaly_type, re_features):
    """Forward to trigger_response1 route"""
    try:
        from routes.trigger_response import trigger_response1_internal
        return trigger_response1_internal(log_id, anomaly_type, re_features)

    except Exception as e:
        logger.error(f"Error forwarding to response1: {str(e)}")
        return {'error': str(e)}


def get_rule_statistics():
    """Get statistics about rule-based classifications"""
    try:
        from db.database import get_db_session, close_db_session
        from db.models.response import Response

        session = get_db_session()

        # Count responses by anomaly type 1
        type1_stats = {}

        bandwidth_count = session.query(Response).filter(
            Response.anomaly_type1 == 'bandwidth_saturation'
        ).count()

        throughput_count = session.query(Response).filter(
            Response.anomaly_type1 == 'throughput_anomaly'
        ).count()

        header_count = session.query(Response).filter(
            Response.anomaly_type1 == 'header_length'
        ).count()

        packet_count = session.query(Response).filter(
            Response.anomaly_type1 == 'packet_size'
        ).count()

        duration_count = session.query(Response).filter(
            Response.anomaly_type1 == 'flow_duration'
        ).count()

        type1_stats = {
            'bandwidth_saturation': bandwidth_count,
            'throughput_anomaly': throughput_count,
            'header_length': header_count,
            'packet_size': packet_count,
            'flow_duration': duration_count,
            'total': bandwidth_count + throughput_count + header_count + packet_count + duration_count
        }

        close_db_session(session)

        return {
            'success': True,
            'type1_statistics': type1_stats,
            'thresholds_used': Config.RCA_TYPE1_THRESHOLDS
        }

    except Exception as e:
        logger.error(f"Error getting rule statistics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def test_rule_classification():
    """Test rule classification with sample data"""
    try:
        # Test data for each anomaly type
        test_cases = [
            {
                'name': 'bandwidth_saturation',
                'features': {
                    'Flow Bytes/s': 2000000,  # Exceeds threshold
                    'Flow Packets/s': 2000,  # Exceeds threshold
                    'Total Length of Fwd Packets': 1000,
                    'Total Length of Bwd Packets': 1000,
                    'Fwd Header Length': 20,
                    'Bwd Header Length': 20,
                    'Max Packet Length': 1500,
                    'Packet Length Mean': 500,
                    'Flow Duration': 60000000
                }
            },
            {
                'name': 'throughput_anomaly',
                'features': {
                    'Flow Bytes/s': 50000,
                    'Flow Packets/s': 100,
                    'Total Length of Fwd Packets': 20000,  # Exceeds threshold
                    'Total Length of Bwd Packets': 15000,  # Exceeds threshold
                    'Fwd Header Length': 20,
                    'Bwd Header Length': 20,
                    'Max Packet Length': 1500,
                    'Packet Length Mean': 500,
                    'Flow Duration': 60000000
                }
            },
            {
                'name': 'normal_traffic',
                'features': {
                    'Flow Bytes/s': 50000,
                    'Flow Packets/s': 100,
                    'Total Length of Fwd Packets': 5000,
                    'Total Length of Bwd Packets': 4800,
                    'Fwd Header Length': 20,
                    'Bwd Header Length': 20,
                    'Max Packet Length': 1500,
                    'Packet Length Mean': 500,
                    'Flow Duration': 60000000
                }
            }
        ]

        results = []

        for test_case in test_cases:
            classified_type = classify_anomaly_type(test_case['features'], Config.RCA_TYPE1_THRESHOLDS)

            results.append({
                'test_name': test_case['name'],
                'classified_as': classified_type,
                'expected_match': classified_type == test_case['name'] or
                                  (test_case['name'] == 'normal_traffic' and classified_type is None)
            })

        return {
            'test_successful': True,
            'test_results': results,
            'thresholds_tested': Config.RCA_TYPE1_THRESHOLDS
        }

    except Exception as e:
        logger.error(f"Error in rule classification test: {str(e)}")
        return {
            'test_successful': False,
            'error': str(e)
        }