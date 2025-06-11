"""
Module: Simple REST API
Purpose: Basic CRUD endpoints for frontend
Dependencies: Flask, db models, utils
"""

from flask import Blueprint, jsonify, request
from db.database import get_db_session, close_db_session
from db.models.events import Event
from db.models.response import Response
from utils.core import sanitize_string, safe_int
import logging

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)


@api_bp.route('/events')
def get_events():
    """Get events with pagination and filters"""
    try:
        page = safe_int(request.args.get('page', 1), 1)
        per_page = min(safe_int(request.args.get('per_page', 20), 20), 100)
        event_type = sanitize_string(request.args.get('type', 'all'))
        ip_filter = sanitize_string(request.args.get('ip', ''))

        session = get_db_session()
        query = session.query(Event)

        # Apply filters
        if event_type == 'anomalous':
            query = query.filter(Event.is_anomalous == True)
        elif event_type == 'normal':
            query = query.filter(Event.is_anomalous == False)

        if ip_filter:
            query = query.filter(
                (Event.src_ip.contains(ip_filter)) |
                (Event.dst_ip.contains(ip_filter))
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        events = query.order_by(Event.timestamp.desc()).offset(offset).limit(per_page).all()

        result = {
            'events': [event.to_dict() for event in events],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

        close_db_session(session)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
        return jsonify({'error': 'Failed to get events'}), 500


@api_bp.route('/responses')
def get_responses():
    """Get responses with pagination and filters"""
    try:
        page = safe_int(request.args.get('page', 1), 1)
        per_page = min(safe_int(request.args.get('per_page', 20), 20), 100)
        response_type = sanitize_string(request.args.get('type', 'all'))
        status_filter = sanitize_string(request.args.get('status', 'all'))

        session = get_db_session()
        query = session.query(Response)

        # Apply filters
        if response_type == 'type1':
            query = query.filter(Response.anomaly_type1.isnot(None))
        elif response_type == 'type2':
            query = query.filter(Response.anomaly_type2.isnot(None))

        if status_filter == 'success':
            query = query.filter(Response.success == True)
        elif status_filter == 'failed':
            query = query.filter(Response.success == False)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        responses = query.order_by(Response.timestamp.desc()).offset(offset).limit(per_page).all()

        result = {
            'responses': [response.to_dict() for response in responses],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

        close_db_session(session)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting responses: {str(e)}")
        return jsonify({'error': 'Failed to get responses'}), 500


@api_bp.route('/status')
def get_status():
    """Get system status and metrics"""
    try:
        from utils.core import state_manager

        session = get_db_session()

        # Get counts
        total_events = session.query(Event).count()
        total_anomalies = session.query(Event).filter(Event.is_anomalous == True).count()
        total_responses = session.query(Response).count()
        successful_responses = session.query(Response).filter(Response.success == True).count()

        # Calculate success rate
        success_rate = 0
        if total_responses > 0:
            success_rate = round((successful_responses / total_responses) * 100, 1)

        result = {
            'monitoring_status': state_manager.get_status(),
            'uptime_seconds': state_manager.get_uptime(),
            'total_events': total_events,
            'total_anomalies': total_anomalies,
            'total_responses': total_responses,
            'success_rate': success_rate
        }

        close_db_session(session)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': 'Failed to get status'}), 500


@api_bp.route('/metrics')
def get_metrics():
    """Get real-time metrics for charts"""
    try:
        session = get_db_session()

        # Recent events (last hour)
        from datetime import datetime, timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        recent_events = session.query(Event).filter(Event.timestamp >= one_hour_ago).count()
        recent_anomalies = session.query(Event).filter(
            Event.timestamp >= one_hour_ago,
            Event.is_anomalous == True
        ).count()

        # Top source IPs
        from sqlalchemy import func
        top_ips = session.query(
            Event.src_ip,
            func.count(Event.id).label('count')
        ).group_by(Event.src_ip).order_by(func.count(Event.id).desc()).limit(5).all()

        result = {
            'recent_events': recent_events,
            'recent_anomalies': recent_anomalies,
            'packets_per_sec': recent_events // 3600 if recent_events else 0,  # Rough estimate
            'top_ips': [{'ip': ip, 'count': count} for ip, count in top_ips]
        }

        close_db_session(session)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({'error': 'Failed to get metrics'}), 500


def get_paginated_events(page, per_page, filters):
    """Helper function for WebSocket - get paginated events"""
    try:
        session = get_db_session()
        query = session.query(Event)

        # Apply filters
        if filters.get('type') == 'anomalous':
            query = query.filter(Event.is_anomalous == True)
        elif filters.get('type') == 'normal':
            query = query.filter(Event.is_anomalous == False)

        if filters.get('ip'):
            ip_filter = sanitize_string(filters['ip'])
            query = query.filter(
                (Event.src_ip.contains(ip_filter)) |
                (Event.dst_ip.contains(ip_filter))
            )

        total = query.count()
        offset = (page - 1) * per_page
        events = query.order_by(Event.timestamp.desc()).offset(offset).limit(per_page).all()

        result = {
            'events': [event.to_dict() for event in events],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total
            }
        }

        close_db_session(session)
        return result

    except Exception as e:
        logger.error(f"Error getting paginated events: {str(e)}")
        return {'events': [], 'pagination': {'page': 1, 'per_page': per_page, 'total': 0}}


def get_paginated_responses(page, per_page, filters):
    """Helper function for WebSocket - get paginated responses"""
    try:
        session = get_db_session()
        query = session.query(Response)

        # Apply filters
        if filters.get('type') == 'type1':
            query = query.filter(Response.anomaly_type1.isnot(None))
        elif filters.get('type') == 'type2':
            query = query.filter(Response.anomaly_type2.isnot(None))

        if filters.get('status') == 'success':
            query = query.filter(Response.success == True)
        elif filters.get('status') == 'failed':
            query = query.filter(Response.success == False)

        total = query.count()
        offset = (page - 1) * per_page
        responses = query.order_by(Response.timestamp.desc()).offset(offset).limit(per_page).all()

        result = {
            'responses': [response.to_dict() for response in responses],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total
            }
        }

        close_db_session(session)
        return result

    except Exception as e:
        logger.error(f"Error getting paginated responses: {str(e)}")
        return {'responses': [], 'pagination': {'page': 1, 'per_page': per_page, 'total': 0}}