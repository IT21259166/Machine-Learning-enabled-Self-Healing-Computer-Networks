"""
Module: Simple Preprocessing Route
Purpose: Read CSV files, extract features, save to DB, forward to prediction
Dependencies: pandas, db models, utils, routes
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import threading
import time

from db.database import get_db_session, close_db_session
from db.models.events import Event
from utils.core import generate_log_id, state_manager
from utils.data_generator import DataGenerator

logger = logging.getLogger(__name__)


class PreprocessingEngine:
    """Simple preprocessing engine for CSV files"""

    def __init__(self, data_directory, important_features):
        self.data_directory = Path(data_directory)
        self.important_features = important_features
        self.processing = False
        self.thread = None
        self.last_processed = None

    def start_processing(self):
        """Start preprocessing loop"""
        if self.processing:
            return True

        self.processing = True
        self.thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.thread.start()
        logger.info("Preprocessing started")
        return True

    def stop_processing(self):
        """Stop preprocessing loop"""
        self.processing = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Preprocessing stopped")

    def _processing_loop(self):
        """Main processing loop - checks for new CSV files"""
        while self.processing:
            try:
                if state_manager.is_monitoring():
                    self._process_latest_csv()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                time.sleep(30)  # Wait longer on error

    def _process_latest_csv(self):
        """Process the latest CSV file"""
        try:
            # Get latest CSV file
            csv_files = list(self.data_directory.glob('network_data_*.csv'))
            if not csv_files:
                return

            latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)

            # Skip if already processed
            if self.last_processed == latest_file:
                return

            logger.info(f"Processing file: {latest_file.name}")

            # Read and process CSV
            results = self.process_csv_file(latest_file)

            if results['success']:
                self.last_processed = latest_file
                logger.info(f"Processed {results['processed_count']} rows from {latest_file.name}")

        except Exception as e:
            logger.error(f"Error processing latest CSV: {str(e)}")

    def process_csv_file(self, file_path):
        """Process single CSV file"""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            logger.info(f"Read CSV with {len(df)} rows")

            processed_count = 0
            anomaly_count = 0

            session = get_db_session()

            for _, row in df.iterrows():
                try:
                    # Extract network metadata
                    metadata = self._extract_metadata(row)

                    # Extract important features
                    imp_features = self._extract_important_features(row)

                    # Generate unique log ID
                    log_id = generate_log_id()

                    # Save to database
                    event = Event(
                        log_id=log_id,
                        timestamp=metadata.get('timestamp', datetime.utcnow()),
                        src_ip=metadata.get('src_ip'),
                        dst_ip=metadata.get('dst_ip'),
                        src_port=metadata.get('src_port'),
                        dst_port=metadata.get('dst_port'),
                        is_anomalous=False  # Will be updated by prediction
                    )

                    session.add(event)
                    session.commit()

                    # Forward to prediction
                    prediction_result = self._forward_to_prediction(log_id, imp_features)

                    if prediction_result and prediction_result.get('is_anomalous'):
                        anomaly_count += 1
                        # Update event with anomaly status
                        event.is_anomalous = True
                        session.commit()

                    processed_count += 1

                except Exception as e:
                    logger.error(f"Error processing row: {str(e)}")
                    session.rollback()
                    continue

            close_db_session(session)

            # Send real-time update
            self._send_processing_update(processed_count, anomaly_count)

            return {
                'success': True,
                'processed_count': processed_count,
                'anomaly_count': anomaly_count
            }

        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _extract_metadata(self, row):
        """Extract network metadata from CSV row"""
        try:
            # Parse timestamp
            timestamp = datetime.utcnow()
            if 'Timestamp' in row and pd.notna(row['Timestamp']):
                try:
                    timestamp = pd.to_datetime(row['Timestamp'])
                except:
                    pass

            return {
                'timestamp': timestamp,
                'src_ip': str(row.get('Src IP', '')),
                'dst_ip': str(row.get('Dst IP', '')),
                'src_port': int(row.get('Src Port', 0)) if pd.notna(row.get('Src Port')) else None,
                'dst_port': int(row.get('Dst Port', 0)) if pd.notna(row.get('Dst Port')) else None
            }

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                'timestamp': datetime.utcnow(),
                'src_ip': 'unknown',
                'dst_ip': 'unknown',
                'src_port': None,
                'dst_port': None
            }

    def _extract_important_features(self, row):
        """Extract the 35 important features for ML model"""
        features = {}

        for feature in self.important_features:
            try:
                value = row.get(feature, 0.0)
                # Convert to float, handle NaN/inf
                if pd.isna(value) or value in [float('inf'), float('-inf')]:
                    value = 0.0
                features[feature] = float(value)
            except:
                features[feature] = 0.0

        return features

    def _forward_to_prediction(self, log_id, imp_features):
        """Forward features to prediction route"""
        try:
            from routes.predict_anomaly import predict_anomaly_internal
            return predict_anomaly_internal(log_id, imp_features)

        except Exception as e:
            logger.error(f"Error forwarding to prediction: {str(e)}")
            return None

    def _send_processing_update(self, processed_count, anomaly_count):
        """Send real-time update via WebSocket"""
        try:
            from app import send_real_time_update

            send_real_time_update('processing_update', {
                'processed_count': processed_count,
                'anomaly_count': anomaly_count,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error sending update: {str(e)}")


# Global preprocessing engine
preprocessing_engine = None


def init_preprocessing(data_directory, important_features):
    """Initialize preprocessing engine"""
    global preprocessing_engine

    preprocessing_engine = PreprocessingEngine(data_directory, important_features)
    logger.info("Preprocessing engine initialized")


def start_preprocessing():
    """Start preprocessing"""
    if preprocessing_engine:
        return preprocessing_engine.start_processing()
    return False


def stop_preprocessing():
    """Stop preprocessing"""
    if preprocessing_engine:
        preprocessing_engine.stop_processing()


def process_single_file(file_path):
    """Process single CSV file (for testing)"""
    if preprocessing_engine:
        return preprocessing_engine.process_csv_file(file_path)
    return {'success': False, 'error': 'Preprocessing engine not initialized'}


def is_processing():
    """Check if preprocessing is active"""
    if preprocessing_engine:
        return preprocessing_engine.processing
    return False