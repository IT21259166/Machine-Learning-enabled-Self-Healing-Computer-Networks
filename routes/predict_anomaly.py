"""
Module: Simple Prediction Route
Purpose: ML anomaly prediction and RCA forwarding
Dependencies: model, db, utils, RCA routes
"""

import logging
from datetime import datetime

from model.model import predict_anomaly, get_model_status
from db.database import get_db_session, close_db_session
from db.models.events import Event
from utils.core import generate_anomaly_id

logger = logging.getLogger(__name__)


def predict_anomaly_internal(log_id, imp_features):
    """Internal prediction function called by preprocessing"""
    try:
        # Use ML model to predict anomaly
        prediction_result = predict_anomaly(imp_features)

        if prediction_result.get('is_anomalous', False):
            logger.info(f"Anomaly detected for log_id: {log_id}")

            # Extract reduced features for RCA analysis
            re_features = extract_reduced_features(imp_features)

            # Forward to RCA routes in parallel
            rca_results = forward_to_rca(log_id, re_features)

            # Send real-time update
            send_anomaly_update(log_id, prediction_result)

            return {
                'is_anomalous': True,
                'prediction': prediction_result,
                'rca_initiated': rca_results
            }
        else:
            logger.debug(f"Normal traffic for log_id: {log_id}")
            return {
                'is_anomalous': False,
                'prediction': prediction_result
            }

    except Exception as e:
        logger.error(f"Error in anomaly prediction: {str(e)}")
        return {
            'is_anomalous': False,
            'error': str(e)
        }


def extract_reduced_features(imp_features):
    """Extract 9 features for RCA Type 1 analysis"""
    # RCA Type 1 features from config
    rca_feature_names = [
        'Flow Duration', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
        'Flow Bytes/s', 'Flow Packets/s', 'Fwd Header Length', 'Bwd Header Length',
        'Max Packet Length', 'Packet Length Mean'
    ]

    re_features = {}
    for feature in rca_feature_names:
        re_features[feature] = imp_features.get(feature, 0.0)

    return re_features


def forward_to_rca(log_id, re_features):
    """Forward to both RCA routes in parallel"""
    results = {}

    try:
        # RCA Type 1 (Rule-based analysis)
        from routes.rca_type1 import analyze_rule_based
        rca1_result = analyze_rule_based(log_id, re_features)
        results['rca_type1'] = rca1_result

    except Exception as e:
        logger.error(f"Error in RCA Type 1: {str(e)}")
        results['rca_type1'] = {'error': str(e)}

    try:
        # RCA Type 2 (Network troubleshooting)
        from routes.rca_type2 import analyze_network_troubleshooting
        rca2_result = analyze_network_troubleshooting(log_id)
        results['rca_type2'] = rca2_result

    except Exception as e:
        logger.error(f"Error in RCA Type 2: {str(e)}")
        results['rca_type2'] = {'error': str(e)}

    return results


def send_anomaly_update(log_id, prediction_result):
    """Send real-time anomaly notification"""
    try:
        from app import send_real_time_update

        # Get event details from database
        session = get_db_session()
        event = session.query(Event).filter(Event.log_id == log_id).first()

        if event:
            update_data = {
                'log_id': log_id,
                'src_ip': event.src_ip,
                'dst_ip': event.dst_ip,
                'timestamp': event.timestamp.isoformat() if event.timestamp else None,
                'reconstruction_error': prediction_result.get('reconstruction_error', 0),
                'confidence': prediction_result.get('confidence', 0)
            }

            send_real_time_update('new_anomaly', update_data)

        close_db_session(session)

    except Exception as e:
        logger.error(f"Error sending anomaly update: {str(e)}")


def batch_predict(csv_file_path):
    """Batch prediction for testing (process entire CSV file)"""
    try:
        import pandas as pd
        from config import Config

        # Read CSV
        df = pd.read_csv(csv_file_path)

        results = []
        anomaly_count = 0

        for _, row in df.iterrows():
            # Extract features
            features = {}
            for feature in Config.IMPORTANT_FEATURES:
                features[feature] = row.get(feature, 0.0)

            # Predict
            result = predict_anomaly(features)

            if result.get('is_anomalous', False):
                anomaly_count += 1

            results.append({
                'row_index': len(results),
                'is_anomalous': result.get('is_anomalous', False),
                'reconstruction_error': result.get('reconstruction_error', 0),
                'confidence': result.get('confidence', 0)
            })

        return {
            'total_rows': len(results),
            'anomalies_detected': anomaly_count,
            'anomaly_rate': anomaly_count / len(results) if results else 0,
            'results': results
        }

    except Exception as e:
        logger.error(f"Error in batch prediction: {str(e)}")
        return {'error': str(e)}


def get_prediction_stats():
    """Get prediction statistics"""
    try:
        # Get model status
        model_status = get_model_status()

        # Get database statistics
        session = get_db_session()

        total_events = session.query(Event).count()
        total_anomalies = session.query(Event).filter(Event.is_anomalous == True).count()

        # Calculate statistics
        anomaly_rate = 0
        if total_events > 0:
            anomaly_rate = (total_anomalies / total_events) * 100

        # Get recent statistics (last hour)
        from datetime import timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        recent_events = session.query(Event).filter(Event.timestamp >= one_hour_ago).count()
        recent_anomalies = session.query(Event).filter(
            Event.timestamp >= one_hour_ago,
            Event.is_anomalous == True
        ).count()

        close_db_session(session)

        return {
            'model_status': model_status,
            'total_events': total_events,
            'total_anomalies': total_anomalies,
            'anomaly_rate_percent': round(anomaly_rate, 2),
            'recent_events': recent_events,
            'recent_anomalies': recent_anomalies,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting prediction stats: {str(e)}")
        return {'error': str(e)}


def test_prediction():
    """Test prediction with sample data"""
    try:
        # Sample features for testing
        test_features = {
            'Flow Duration': 120000000,  # 2 minutes in microseconds
            'Total Fwd Packets': 100,
            'Total Backward Packets': 95,
            'Total Length of Fwd Packets': 50000,
            'Total Length of Bwd Packets': 48000,
            'Fwd Packet Length Max': 1500,
            'Fwd Packet Length Mean': 500,
            'Fwd Packet Length Std': 100,
            'Bwd Packet Length Max': 1500,
            'Bwd Packet Length Mean': 505,
            'Bwd Packet Length Std': 98,
            'Flow Bytes/s': 816.67,
            'Flow Packets/s': 1.63,
            'Flow IAT Mean': 1200000,
            'Flow IAT Std': 5000,
            'Flow IAT Max': 15000,
            'Flow IAT Min': 100,
            'Fwd IAT Total': 119000000,
            'Fwd Header Length': 20,
            'Bwd Header Length': 20,
            'Min Packet Length': 64,
            'Max Packet Length': 1500,
            'Packet Length Mean': 502.5,
            'Packet Length Std': 99,
            'Packet Length Variance': 9801,
            'ACK Flag Count': 95,
            'Down/Up Ratio': 0.95,
            'Average Packet Size': 502.5,
            'Avg Bwd Segment Size': 505,
            'Subflow Fwd Bytes': 50000,
            'Init_Win_bytes_forward': 8192,
            'Init_Win_bytes_backward': 8192,
            'Idle Mean': 0,
            'Idle Max': 0,
            'Idle Min': 0
        }

        result = predict_anomaly(test_features)

        return {
            'test_successful': True,
            'prediction_result': result,
            'test_features_count': len(test_features)
        }

    except Exception as e:
        logger.error(f"Error in test prediction: {str(e)}")
        return {
            'test_successful': False,
            'error': str(e)
        }