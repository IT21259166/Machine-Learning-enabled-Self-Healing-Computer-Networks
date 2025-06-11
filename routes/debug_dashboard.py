"""
Module: Debug Dashboard
Purpose: Development debugging interface with HTML templates
Dependencies: Flask, db, utils
"""

from flask import Blueprint, render_template, jsonify, request
from db.database import get_database_stats, check_database_health
from utils.core import state_manager
from model.model import get_model_status
import logging

logger = logging.getLogger(__name__)
debug_bp = Blueprint('debug', __name__)


@debug_bp.route('/')
def dashboard():
    """Main debug dashboard HTML"""
    return render_template('debug/dashboard.html')


@debug_bp.route('/system')
def system_status():
    """System status information"""
    try:
        import psutil
        import os

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Process info
        process = psutil.Process(os.getpid())

        return jsonify({
            'system': {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used_mb': memory.used // (1024 * 1024),
                'memory_total_mb': memory.total // (1024 * 1024),
                'disk_percent': round(disk.percent, 1),
                'disk_used_gb': disk.used // (1024 * 1024 * 1024),
                'disk_total_gb': disk.total // (1024 * 1024 * 1024)
            },
            'process': {
                'pid': process.pid,
                'memory_mb': process.memory_info().rss // (1024 * 1024),
                'cpu_percent': round(process.cpu_percent(), 1),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            },
            'monitoring': {
                'status': state_manager.get_status(),
                'uptime_seconds': round(state_manager.get_uptime(), 1)
            }
        })

    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/database')
def database_status():
    """Database status and statistics"""
    try:
        health = check_database_health()
        stats = get_database_stats()

        return jsonify({
            'health': health,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/model')
def model_status():
    """ML model status"""
    try:
        status = get_model_status()
        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting model status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/logs')
def get_logs():
    """Get recent log entries"""
    try:
        log_level = request.args.get('level', 'INFO')
        lines = int(request.args.get('lines', 50))

        # Read log file (simplified)
        from pathlib import Path
        log_file = Path('logs/app.log')

        if log_file.exists():
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-lines:]

            # Filter by log level if specified
            if log_level != 'ALL':
                log_lines = [line for line in log_lines if log_level in line]

            return jsonify({
                'logs': log_lines,
                'total_lines': len(log_lines),
                'log_level': log_level
            })
        else:
            return jsonify({
                'logs': ['No log file found'],
                'total_lines': 0,
                'message': 'Log file not found'
            })

    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/test/prediction')
def test_prediction():
    """Test ML prediction"""
    try:
        from routes.predict_anomaly import test_prediction
        result = test_prediction()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error testing prediction: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/test/rca1')
def test_rca1():
    """Test RCA Type 1"""
    try:
        from routes.rca_type1 import test_rule_classification
        result = test_rule_classification()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error testing RCA1: {str(e)}")
        return jsonify({'error': str(e)}), 500


@debug_bp.route('/clear/database')
def clear_database():
    """Clear database (development only)"""
    try:
        from db.database import reset_database

        # Only allow in development
        from config import get_config
        config = get_config()

        if not config.DEBUG:
            return jsonify({'error': 'Database reset only allowed in debug mode'}), 403

        success = reset_database()

        if success:
            return jsonify({'message': 'Database cleared successfully'})
        else:
            return jsonify({'error': 'Failed to clear database'}), 500

    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        return jsonify({'error': str(e)}), 500