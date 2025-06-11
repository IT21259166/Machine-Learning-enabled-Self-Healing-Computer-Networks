"""
Module: Simple ML Model Handler
Purpose: Load LSTM-VAE model and make predictions
Dependencies: tensorflow, sklearn, pandas, numpy
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.impute import KNNImputer
from scipy.stats.mstats import winsorize
import joblib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Custom sampling function (must match training)
@tf.keras.utils.register_keras_serializable()
def sampling(args):
    """Sampling function for the VAE."""
    z_mean, z_log_var = args
    epsilon = tf.random.normal(tf.shape(z_mean), 0, 1, dtype=tf.float32)
    return z_mean + tf.exp(z_log_var / 2) * epsilon

# Custom VAE loss function (must match training)
@tf.keras.utils.register_keras_serializable()
def custom_vae_loss(y_true, y_pred):
    """Custom VAE loss function with KL divergence and reconstruction error."""
    # Note: This is a placeholder - actual loss calculation happens during training
    reconstruction_loss = tf.reduce_mean(tf.reduce_sum(tf.square(y_true - y_pred), axis=(1, 2)))
    return reconstruction_loss

class ANBDModel:
    """LSTM-VAE model for anomaly detection"""

    def __init__(self, model_path=None, scaler_path=None):
        self.model = None
        self.scaler = None
        self.seq_len = 10  # From training code
        self.input_dim = 35  # 35 features from config
        self.threshold = 0.5  # Default threshold
        self.is_loaded = False

        if model_path:
            self.load_model(model_path, scaler_path)

    def load_model(self, model_path, scaler_path=None):
        """Load trained model and scaler"""
        try:
            # Load the trained model
            self.model = keras.models.load_model(
                model_path,
                custom_objects={
                    'sampling': sampling,
                    'custom_vae_loss': custom_vae_loss
                }
            )

            # Load scaler if available
            if scaler_path and Path(scaler_path).exists():
                self.scaler = joblib.load(scaler_path)
            else:
                # Create default scaler
                self.scaler = MinMaxScaler()
                logger.warning("Scaler not found, using default MinMaxScaler")

            self.is_loaded = True
            logger.info("Model and scaler loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def preprocess_features(self, features_dict):
        """Preprocess features using the same pipeline as training"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([features_dict])

            # Ensure we have all 35 features
            required_features = [
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

            # Add missing features with default values
            for feature in required_features:
                if feature not in df.columns:
                    df[feature] = 0.0

            # Select only required features in correct order
            df = df[required_features]

            # Convert to numeric
            df = df.apply(pd.to_numeric, errors='coerce')

            # Replace infinities with NaN
            df.replace([np.inf, -np.inf], np.nan, inplace=True)

            # Winsorization (cap extreme values)
            for col in df.columns:
                df[col] = winsorize(df[col], limits=[0.01, 0.01])

            # Handle missing values
            imputer = KNNImputer(n_neighbors=5)
            df_imputed = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)

            # Scale features
            if self.scaler:
                df_scaled = pd.DataFrame(
                    self.scaler.transform(df_imputed),
                    columns=df_imputed.columns
                )
            else:
                # Fallback: simple min-max scaling
                scaler = MinMaxScaler()
                df_scaled = pd.DataFrame(
                    scaler.fit_transform(df_imputed),
                    columns=df_imputed.columns
                )

            return df_scaled.values[0]  # Return first (and only) row

        except Exception as e:
            logger.error(f"Error preprocessing features: {str(e)}")
            # Return zero array as fallback
            return np.zeros(self.input_dim)

    def predict_anomaly(self, features_dict):
        """Predict if network traffic is anomalous"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        try:
            # Preprocess features
            preprocessed_features = self.preprocess_features(features_dict)

            # Reshape for model input (batch_size=1, seq_len, input_dim)
            # Repeat the single sample to create sequence
            input_data = np.tile(preprocessed_features, (self.seq_len, 1))
            input_data = input_data.reshape(1, self.seq_len, self.input_dim)

            # Get reconstruction from model
            reconstruction = self.model.predict(input_data, verbose=0)

            # Calculate reconstruction error
            mse = np.mean(np.square(input_data - reconstruction))

            # Determine if anomalous based on threshold
            is_anomalous = mse > self.threshold

            return {
                'is_anomalous': bool(is_anomalous),
                'reconstruction_error': float(mse),
                'confidence': float(min(mse / self.threshold, 2.0))  # Confidence score
            }

        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            return {
                'is_anomalous': False,
                'reconstruction_error': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }

    def set_threshold(self, threshold):
        """Set anomaly detection threshold"""
        self.threshold = max(0.01, float(threshold))  # Minimum threshold of 0.01
        logger.info(f"Anomaly threshold set to {self.threshold}")

    def get_model_info(self):
        """Get model information"""
        if not self.is_loaded:
            return {'status': 'not_loaded'}

        return {
            'status': 'loaded',
            'input_shape': (self.seq_len, self.input_dim),
            'threshold': self.threshold,
            'model_summary': str(self.model.summary()) if self.model else None
        }

# Global model instance
model_instance = None

def load_model(model_path, scaler_path=None, threshold=0.5):
    """Load the global model instance"""
    global model_instance

    try:
        # Check if model file exists
        from pathlib import Path
        if not Path(model_path).exists():
            logger.warning(f"Model file not found: {model_path}")
            # Create a dummy model instance that will return safe defaults
            model_instance = ANBDModel()
            model_instance.is_loaded = False
            return True

        model_instance = ANBDModel(model_path, scaler_path)
        model_instance.set_threshold(threshold)
        logger.info("Global model loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to load global model: {str(e)}")
        # Create dummy instance
        model_instance = ANBDModel()
        model_instance.is_loaded = False
        return False

def predict_anomaly(features_dict):
    """Predict anomaly using global model instance"""
    if model_instance is None or not model_instance.is_loaded:
        # Return safe default when model not loaded
        logger.warning("Model not loaded - returning default non-anomalous result")
        return {
            'is_anomalous': False,
            'reconstruction_error': 0.0,
            'confidence': 0.0,
            'note': 'Model not loaded'
        }

    return model_instance.predict_anomaly(features_dict)

def get_model_status():
    """Get status of global model"""
    if model_instance is None:
        return {'status': 'not_initialized'}

    return model_instance.get_model_info()

def set_anomaly_threshold(threshold):
    """Set anomaly detection threshold"""
    if model_instance is None:
        raise RuntimeError("Model not initialized")

    model_instance.set_threshold(threshold)