"""
Module: Main Flask Application
Purpose: Application factory, WebSocket server, route registration
Security: CORS configuration, error handling, input validation
Dependencies: Flask, Flask-SocketIO, config, routes, db
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
import logging
from datetime import datetime
import threading
import signal
import atexit

from config import get_config, validate_config
from db.database import init_db, get_db_session, close_db_session
from utils.core import setup_logger, StateManager
from utils.error_handler import handle_exceptions
from utils.data_generator import DataGenerator

# Global objects
socketio = None
state_manager = None
data_generator = None
logger = None

def create_app(config_name=None):
    """
    Application factory pattern for Flask app creation
    """
    global socketio, state_manager, logger

    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Validate configuration
    validate_config(config_class)

    # Initialize logging
    logger = setup_logger(app.config['LOG_LEVEL'], app.config['LOG_DIR'])
    logger.info("Starting ANBD Flask application")

    # Initialize database
    init_db(app)

    # Initialize state manager
    state_manager = StateManager()

    # Configure CORS
    CORS(app, origins=["http://localhost:*", "https://localhost:*"])

    # Initialize SocketIO with security settings
    socketio = SocketIO(
        app,
        cors_allowed_origins=["*"],  # Allow all origins for now
        logger=True,  # Enable SocketIO logging for debugging
        engineio_logger=True,
        async_mode='threading',  # Use threading mode for better compatibility
        transports=['websocket', 'polling'],  # Add this line
        allow_upgrades=True,  # Add this line
        ping_timeout=60,
        ping_interval=25
    )

    # Register routes
    register_routes(app)

    # Register WebSocket events
    register_websocket_events()

    # Register error handlers
    register_error_handlers(app)

    # Initialize background services
    initialize_services(app)

    # Register shutdown handlers
    register_shutdown_handlers(app)

    logger.info("ANBD Flask application created successfully")
    return app

def register_routes(app):
    """Register all application routes"""
    try:
        # Import and register route blueprints
        from routes.api import api_bp
        from routes.debug_dashboard import debug_bp

        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(debug_bp, url_prefix='/debug')

        # Health check endpoint
        @app.route('/health')
        def health_check():
            """Application health check endpoint"""
            try:
                # Check database connection
                from sqlalchemy import text
                session = get_db_session()
                session.execute(text('SELECT 1'))
                close_db_session(session)

                # Check state manager
                status = state_manager.get_status() if state_manager else 'unknown'

                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'monitoring_status': status,
                    'version': '1.0.0'
                }), 200

            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        # Root endpoint
        @app.route('/', methods=['GET', 'POST'])
        def index():
            """Root endpoint with basic info"""
            try:
                return jsonify({
                    'service': 'ANBD Backend',
                    'version': '1.0.0',
                    'status': 'running',
                    'message': 'ANBD Backend is running successfully',
                    'endpoints': {
                        'health': '/health',
                        'api': '/api',
                        'debug': '/debug',
                        'websocket': f"http://localhost:3000"
                    }
                }), 200
            except Exception as e:
                logger.error(f"Error in root endpoint: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        logger.info("Routes registered successfully")

    except Exception as e:
        logger.error(f"Failed to register routes: {str(e)}")
        raise

def register_websocket_events():
    """Register WebSocket event handlers"""
    global socketio, state_manager, logger

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        client_id = request.sid
        logger.info(f"Client connected: {client_id}")

        # Send connection confirmation
        emit('connection_status', {
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.utcnow().isoformat()
        })

        # Send current monitoring status
        if state_manager:
            status = state_manager.get_status()
            emit('monitoring_status', {
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            })

        # Send initial system status
        emit('status_update', {
            'totalEvents': 0,
            'eventsToday': 0,
            'totalAnomalies': 0,
            'anomaliesHour': 0,
            'totalResponses': 0,
            'successRate': 0
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        client_id = request.sid
        logger.info(f"Client disconnected: {client_id}")

    @socketio.on('start_monitoring')
    @handle_exceptions(logger)
    def handle_start_monitoring(data):
        """Handle start monitoring request"""
        try:
            client_id = request.sid
            logger.info(f"Start monitoring request from {client_id}")

            if state_manager.is_monitoring():
                emit('error', {
                    'message': 'Monitoring already active',
                    'timestamp': datetime.utcnow().isoformat()
                })
                return

            # Start monitoring process
            success = start_monitoring_process()

            if success:
                state_manager.set_monitoring(True)

                # Notify all clients
                socketio.emit('monitoring_started', {
                    'status': 'started',
                    'timestamp': datetime.utcnow().isoformat()
                })

                logger.info("Monitoring started successfully")
            else:
                emit('error', {
                    'message': 'Failed to start monitoring',
                    'timestamp': datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error starting monitoring: {str(e)}")
            emit('error', {
                'message': f'Start monitoring failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('stop_monitoring')
    @handle_exceptions(logger)
    def handle_stop_monitoring(data):
        """Handle stop monitoring request"""
        try:
            client_id = request.sid
            logger.info(f"Stop monitoring request from {client_id}")

            if not state_manager.is_monitoring():
                emit('error', {
                    'message': 'Monitoring not active',
                    'timestamp': datetime.utcnow().isoformat()
                })
                return

            # Stop monitoring process
            success = stop_monitoring_process()

            if success:
                state_manager.set_monitoring(False)

                # Notify all clients
                socketio.emit('monitoring_stopped', {
                    'status': 'stopped',
                    'timestamp': datetime.utcnow().isoformat()
                })

                logger.info("Monitoring stopped successfully")
            else:
                emit('error', {
                    'message': 'Failed to stop monitoring',
                    'timestamp': datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error stopping monitoring: {str(e)}")
            emit('error', {
                'message': f'Stop monitoring failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('get_events')
    @handle_exceptions(logger)
    def handle_get_events(data):
        """Handle get events request"""
        try:
            from routes.api import get_paginated_events

            page = data.get('page', 1)
            per_page = min(data.get('perPage', 20), 100)  # Max 100 items
            filters = data.get('filters', {})

            events_data = get_paginated_events(page, per_page, filters)

            emit('events_data', events_data)

        except Exception as e:
            logger.error(f"Error getting events: {str(e)}")
            emit('error', {
                'message': f'Failed to get events: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('get_responses')
    @handle_exceptions(logger)
    def handle_get_responses(data):
        """Handle get responses request"""
        try:
            from routes.api import get_paginated_responses

            page = data.get('page', 1)
            per_page = min(data.get('perPage', 20), 100)  # Max 100 items
            filters = data.get('filters', {})

            responses_data = get_paginated_responses(page, per_page, filters)

            emit('responses_data', responses_data)

        except Exception as e:
            logger.error(f"Error getting responses: {str(e)}")
            emit('error', {
                'message': f'Failed to get responses: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('heartbeat')
    def handle_heartbeat():
        """Handle client heartbeat"""
        emit('heartbeat_ack', {
            'timestamp': datetime.utcnow().isoformat()
        })

    logger.info("WebSocket events registered successfully")

def start_monitoring_process():
    """Start the monitoring process"""
    try:
        global data_generator

        # Start data generation if not already running
        if data_generator and not data_generator.is_running():
            data_generator.start()

        # Start preprocessing
        from routes.preprocess import start_preprocessing
        start_preprocessing()

        logger.info("Monitoring process started")
        return True

    except Exception as e:
        logger.error(f"Failed to start monitoring process: {str(e)}")
        return False

def stop_monitoring_process():
    """Stop the monitoring process"""
    try:
        global data_generator

        # Stop data generation
        if data_generator and data_generator.is_running():
            data_generator.stop()

        # Stop preprocessing
        from routes.preprocess import stop_preprocessing
        stop_preprocessing()

        logger.info("Monitoring process stopped")
        return True

    except Exception as e:
        logger.error(f"Failed to stop monitoring process: {str(e)}")
        return False

def register_error_handlers(app):
    """Register application error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        # Log request details for debugging
        logger.warning(f"Bad request from {request.remote_addr}: {request.method} {request.path}")
        logger.warning(f"Headers: {dict(request.headers)}")
        logger.warning(f"Error details: {error}")

        return jsonify({
            'error': 'Bad Request',
            'message': 'The request was malformed or invalid',
            'path': request.path,
            'method': request.method,
            'timestamp': datetime.utcnow().isoformat()
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'timestamp': datetime.utcnow().isoformat()
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {str(e)}")
        return jsonify({
            'error': 'Server Error',
            'message': 'An error occurred while processing your request',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

    logger.info("Error handlers registered successfully")

def initialize_services(app):
    """Initialize background services"""
    global data_generator

    try:
        # Initialize ML model first
        from model.model import load_model
        model_path = app.config['MODEL_PATH']
        scaler_path = app.config.get('SCALER_PATH')
        threshold = app.config.get('ANOMALY_THRESHOLD', 0.5)

        # Try to load model (don't fail if model files missing)
        try:
            load_model(model_path, scaler_path, threshold)
            logger.info("ML model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load ML model: {str(e)} - continuing without model")

        # Initialize data generator
        data_generator = DataGenerator(
            interval=app.config['DATA_GENERATION_INTERVAL'],
            data_dir=app.config['DATA_DIRECTORY'],
            max_files=app.config['MAX_CSV_FILES'],
            network_devices=app.config['NETWORK_DEVICES'],
            vlans=app.config['VLANS']
        )

        # Set up data generator callbacks for real-time updates
        def on_new_data(data):
            if socketio:
                socketio.emit('new_data_generated', {
                    'timestamp': datetime.utcnow().isoformat(),
                    'filename': data.get('filename', ''),
                    'row_count': data.get('row_count', 0)
                })

        data_generator.set_callback(on_new_data)

        # Initialize preprocessing
        from routes.preprocess import init_preprocessing
        init_preprocessing(app.config['DATA_DIRECTORY'], app.config['IMPORTANT_FEATURES'])

        logger.info("Background services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        # Don't raise - continue without some services

def register_shutdown_handlers(app):
    """Register application shutdown handlers"""

    def cleanup():
        """Cleanup function called on shutdown"""
        global data_generator, state_manager

        logger.info("Shutting down ANBD application")

        try:
            # Stop monitoring
            if state_manager and state_manager.is_monitoring():
                stop_monitoring_process()

            # Stop data generator
            if data_generator:
                data_generator.stop()

            # Close database sessions
            close_db_session()

            logger.info("Application shutdown completed")

        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

    # Register cleanup for different shutdown scenarios
    atexit.register(cleanup)

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def send_real_time_update(event_type, data):
    """Send real-time updates to connected clients"""
    global socketio

    if socketio:
        socketio.emit(event_type, {
            **data,
            'timestamp': datetime.utcnow().isoformat()
        })

# Application factory
def run_app(config_name=None, host=None, port=None, debug=None):
    """Run the Flask application with SocketIO"""
    global socketio

    app = create_app(config_name)

    # Use config values if not provided, but default to port 3000
    host = host or app.config.get('WEBSOCKET_HOST', '0.0.0.0')
    port = port or 3000  # Changed default port to 3000
    debug = debug if debug is not None else app.config.get('DEBUG', False)

    logger.info(f"Starting ANBD server on {host}:{port}")

    try:
        # Run with SocketIO
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True  # For development only
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'development')

    # Run the application on port 3000
    run_app(config_name=config_name, port=3000)