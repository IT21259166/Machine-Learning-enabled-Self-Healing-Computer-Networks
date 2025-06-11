#!/usr/bin/env python3
"""
ANBD System - Flask Backend with Database Integration
Handles start/stop from frontend, generates logs, saves to DB, sends WebSocket updates
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import json
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import uuid
import os
import pytz

# Sri Lanka timezone
SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'anbd-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///anbd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
CORS(app, origins=["http://localhost:*", "file://*", "http://127.0.0.1:*"])


# Add CORS headers for Electron
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Database Models
class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.String(36), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(SRI_LANKA_TZ), nullable=False)
    src_ip = db.Column(db.String(15), nullable=False)
    dst_ip = db.Column(db.String(15), nullable=False)
    src_port = db.Column(db.Integer, nullable=False)
    dst_port = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='normal', nullable=False)
    features = db.Column(db.Text, nullable=True)  # JSON string of features
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SRI_LANKA_TZ))

    def to_dict(self):
        return {
            'id': self.id,
            'log_id': self.log_id,
            'timestamp': self.timestamp.astimezone(SRI_LANKA_TZ).isoformat(),
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'status': self.status,
            'features': json.loads(self.features) if self.features else {},
            'created_at': self.created_at.astimezone(SRI_LANKA_TZ).isoformat()
        }


class Response(db.Model):
    __tablename__ = 'responses'

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.String(36), nullable=False)
    anomaly_id = db.Column(db.String(36), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(SRI_LANKA_TZ), nullable=False)
    src_ip = db.Column(db.String(15), nullable=False)
    dst_ip = db.Column(db.String(15), nullable=False)
    src_port = db.Column(db.Integer, nullable=False)
    dst_port = db.Column(db.Integer, nullable=False)
    anomaly_type1 = db.Column(db.String(50), nullable=True)
    anomaly_type2 = db.Column(db.String(50), nullable=True)
    res_type1 = db.Column(db.String(50), nullable=True)
    res_type2 = db.Column(db.String(50), nullable=True)
    features = db.Column(db.Text, nullable=True)  # JSON string of reFeatures
    confidence_score = db.Column(db.Float, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SRI_LANKA_TZ))

    def to_dict(self):
        return {
            'id': self.id,
            'log_id': self.log_id,
            'anomaly_id': self.anomaly_id,
            'timestamp': self.timestamp.astimezone(SRI_LANKA_TZ).isoformat(),
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'src_port': self.src_port,
            'dst_port': self.dst_port,
            'anomaly_type1': self.anomaly_type1,
            'anomaly_type2': self.anomaly_type2,
            'res_type1': self.res_type1,
            'res_type2': self.res_type2,
            'features': json.loads(self.features) if self.features else {},
            'confidence_score': self.confidence_score,
            'execution_time': self.execution_time,
            'status': self.status,
            'created_at': self.created_at.astimezone(SRI_LANKA_TZ).isoformat()
        }


# Log Generator Class
class ANBDLogGenerator:
    def __init__(self):
        self.is_running = False
        self.generation_thread = None
        self._start_time = None
        self._stop_time = None

        # Network topology from your GNS3 setup
        self.network_devices = {
            'routers': {
                'CORE-RO-1': ['192.168.60.2', '192.168.60.14', '192.168.60.17', '192.168.60.25', '192.168.60.29',
                              '192.168.61.1'],
                'CORE-RO-2': ['192.168.60.6', '192.168.60.10', '192.168.60.21', '192.168.60.26', '192.168.60.30'],
                'DT-RO-1': ['192.168.60.1', '192.168.60.5'],
                'DT-RO-2': ['192.168.60.9', '192.168.60.13'],
                'EDGE-FW': ['192.168.60.18', '192.168.60.22', '192.168.137.2']
            },
            'end_devices': {
                'VLAN10': ['192.168.10.1', '192.168.10.2'],
                'VLAN20': ['192.168.20.1', '192.168.20.2'],
                'VLAN30': ['192.168.30.1', '192.168.30.2'],
                'VLAN40': ['192.168.40.1', '192.168.40.2'],
                'Ubuntu': ['192.168.61.2']
            }
        }

        # Anomaly types
        self.anomaly_type1_list = [
            'bandwidth_saturation', 'throughput_anomaly', 'unusual_header_length',
            'unusual_packet_size', 'unusual_flow_duration'
        ]

        self.anomaly_type2_list = [
            'high_latency', 'high_error_rates', 'flapping_links',
            'connectivity_issues', 'high_packet_loss'
        ]

        # Response types
        self.response_types = {
            'type1': {
                'bandwidth_saturation': ['qos_adjustment', 'traffic_shaping', 'load_balancing'],
                'throughput_anomaly': ['interface_optimization', 'buffer_tuning', 'mtu_adjustment'],
                'unusual_header_length': ['header_compression', 'protocol_optimization'],
                'unusual_packet_size': ['fragmentation_fix', 'mss_clamping'],
                'unusual_flow_duration': ['timeout_adjustment', 'session_optimization']
            },
            'type2': {
                'high_latency': ['route_optimization', 'interface_reset', 'priority_queuing'],
                'high_error_rates': ['interface_diagnostics', 'cable_check', 'duplex_fix'],
                'flapping_links': ['interface_stabilization', 'dampening_config'],
                'connectivity_issues': ['routing_table_refresh', 'arp_clear', 'interface_bounce'],
                'high_packet_loss': ['buffer_increase', 'congestion_control', 'interface_optimization']
            }
        }

    def get_all_ips(self):
        """Get all IP addresses from topology"""
        all_ips = []
        for device_ips in self.network_devices['routers'].values():
            all_ips.extend(device_ips)
        for device_ips in self.network_devices['end_devices'].values():
            all_ips.extend(device_ips)
        return all_ips

    def generate_realistic_features(self):
        """Generate realistic network flow features"""
        return {
            'Flow Duration': round(random.uniform(0.1, 30.0), 3),
            'Total Fwd Packets': random.randint(1, 1000),
            'Total Backward Packets': random.randint(1, 500),
            'Total Length of Fwd Packets': random.randint(64, 65535),
            'Total Length of Bwd Packets': random.randint(64, 32768),
            'Fwd Packet Length Max': round(random.uniform(64, 1500), 2),
            'Fwd Packet Length Mean': round(random.uniform(200, 1000), 2),
            'Fwd Packet Length Std': round(random.uniform(50, 300), 2),
            'Bwd Packet Length Max': round(random.uniform(64, 1500), 2),
            'Bwd Packet Length Mean': round(random.uniform(200, 800), 2),
            'Bwd Packet Length Std': round(random.uniform(50, 250), 2),
            'Flow Bytes/s': round(random.uniform(100, 10000000), 2),
            'Flow Packets/s': round(random.uniform(1, 10000), 2),
            'Flow IAT Mean': round(random.uniform(0.001, 5.0), 4),
            'Flow IAT Std': round(random.uniform(0.001, 2.0), 4),
            'Flow IAT Max': round(random.uniform(0.1, 10.0), 3),
            'Flow IAT Min': round(random.uniform(0.0001, 0.1), 4),
            'Fwd IAT Total': round(random.uniform(0.1, 100.0), 3),
            'Fwd Header Length': round(random.uniform(20, 60), 2),
            'Bwd Header Length': round(random.uniform(20, 60), 2),
            'Min Packet Length': round(random.uniform(64, 200), 2),
            'Max Packet Length': round(random.uniform(1000, 1500), 2),
            'Packet Length Mean': round(random.uniform(300, 800), 2),
            'Packet Length Std': round(random.uniform(100, 400), 2),
            'Packet Length Variance': round(random.uniform(10000, 160000), 2),
            'ACK Flag Count': random.randint(0, 100),
            'Down/Up Ratio': round(random.uniform(0.1, 5.0), 3),
            'Average Packet Size': round(random.uniform(200, 1200), 2),
            'Avg Bwd Segment Size': round(random.uniform(200, 1000), 2),
            'Subflow Fwd Bytes': random.randint(64, 65535),
            'Init_Win_bytes_forward': random.randint(8192, 65536),
            'Init_Win_bytes_backward': random.randint(8192, 65536),
            'Idle Mean': round(random.uniform(0.1, 10.0), 3),
            'Idle Max': round(random.uniform(1.0, 50.0), 3),
            'Idle Min': round(random.uniform(0.01, 1.0), 4)
        }

    def generate_and_save_events(self):
        """Generate events and save to database"""
        with app.app_context():
            try:
                all_ips = self.get_all_ips()
                num_events = random.randint(3, 8)  # Generate 3-8 events per batch

                for _ in range(num_events):
                    # Generate network event
                    src_ip = random.choice(all_ips)
                    dst_ip = random.choice([ip for ip in all_ips if ip != src_ip])
                    src_port = random.randint(1024, 65535)
                    dst_port = random.choice([22, 23, 53, 80, 443, 993, 995, 3306, 5432, 8080])

                    # Determine if anomalous (25% chance)
                    status = random.choices(['normal', 'anomalous'], weights=[75, 25], k=1)[0]

                    features = self.generate_realistic_features()

                    # Create and save event
                    event = Event(
                        log_id=str(uuid.uuid4()),
                        src_ip=src_ip,
                        dst_ip=dst_ip,
                        src_port=src_port,
                        dst_port=dst_port,
                        status=status,
                        features=json.dumps(features)
                    )

                    db.session.add(event)
                    db.session.commit()

                    # Send event to frontend via WebSocket
                    socketio.emit('new_event', event.to_dict())

                    # If anomalous, generate response
                    if status == 'anomalous':
                        self.generate_and_save_response(event, features)

                    print(f"Generated event: {src_ip}:{src_port} -> {dst_ip}:{dst_port} ({status})")

            except Exception as e:
                print(f"Error generating events: {e}")
                db.session.rollback()

    def generate_and_save_response(self, event, features):
        """Generate response for anomalous event"""
        with app.app_context():
            try:
                # Select anomaly types
                anomaly_type1 = random.choice(self.anomaly_type1_list)
                anomaly_type2 = random.choice(self.anomaly_type2_list)

                # Select response types
                res_type1 = random.choice(self.response_types['type1'][anomaly_type1])
                res_type2 = random.choice(self.response_types['type2'][anomaly_type2])

                # Extract reFeatures (subset of features)
                re_features = {k: v for k, v in features.items() if k in [
                    'Flow Duration', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
                    'Flow Bytes/s', 'Flow Packets/s', 'Fwd Header Length', 'Bwd Header Length',
                    'Max Packet Length', 'Packet Length Mean'
                ]}

                # Create response
                response = Response(
                    log_id=event.log_id,
                    anomaly_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow() + timedelta(seconds=random.randint(1, 30)),
                    src_ip=event.src_ip,
                    dst_ip=event.dst_ip,
                    src_port=event.src_port,
                    dst_port=event.dst_port,
                    anomaly_type1=anomaly_type1,
                    anomaly_type2=anomaly_type2,
                    res_type1=res_type1,
                    res_type2=res_type2,
                    features=json.dumps(re_features),
                    confidence_score=round(random.uniform(0.7, 0.99), 3),
                    execution_time=round(random.uniform(0.5, 5.0), 2),
                    status=random.choice(['success', 'partial', 'failed'])
                )

                db.session.add(response)
                db.session.commit()

                # Send response to frontend via WebSocket
                socketio.emit('new_response', response.to_dict())

                print(f"Generated response: {anomaly_type1} + {anomaly_type2} -> {res_type1} + {res_type2}")

            except Exception as e:
                print(f"Error generating response: {e}")
                db.session.rollback()

    def start_generation(self):
        """Start log generation with detailed status messages"""
        if self.is_running:
            return False

        print("\n" + "=" * 60)
        print("🛡️  ANBD SYSTEM STARTUP SEQUENCE")
        print("=" * 60)

        # Step 1: Initialize system
        print("🚀 ANBD System starting...")
        time.sleep(0.5)

        # Step 2: Database initialization
        print("🗄️  Database initialized")
        time.sleep(0.3)

        # Step 3: Routes registration
        print("🔗 Routes registered")
        time.sleep(0.3)

        # Step 4: Preprocessing system
        print("⚙️  Preprocessing system started")
        time.sleep(0.5)

        # Step 5: RCA and Response engines
        print("🔧 RCA and Response engines started")
        time.sleep(0.5)

        # Step 6: Model loading
        print("🤖 Model loaded")
        time.sleep(0.5)

        self.is_running = True
        self._start_time = datetime.now(SRI_LANKA_TZ)

        print("✅ ANBD System started successfully!")
        print(f"📅 Start time: {self._start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("=" * 60 + "\n")

        # Send status update with start time
        socketio.emit('system_status', {
            'state': 'running',
            'message': 'System started',
            'start_time': self._start_time.isoformat(),
            'uptime': 0
        })

        # Start generation thread
        self.generation_thread = threading.Thread(target=self._generation_loop, daemon=True)
        self.generation_thread.start()

        return True

    def stop_generation(self):
        """Stop log generation with shutdown message"""
        if not self.is_running:
            return False

        print("\n" + "=" * 60)
        print("🛑 ANBD SYSTEM SHUTDOWN SEQUENCE")
        print("=" * 60)

        self.is_running = False
        self._stop_time = datetime.now(SRI_LANKA_TZ)

        print("🔄 Stopping system components...")
        time.sleep(0.5)

        print("💾 Saving final data...")
        time.sleep(0.3)

        print("🧹 Cleaning up resources...")
        time.sleep(0.3)

        uptime = self.get_uptime()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        print("🛑 ANBD System stopped")
        print(f"📅 Stop time: {self._stop_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"⏱️  Total uptime: {hours:02d}h {minutes:02d}m {seconds:02d}s")
        print("=" * 60 + "\n")

        # Send status update
        socketio.emit('system_status', {
            'state': 'stopped',
            'message': 'System stopped',
            'stop_time': self._stop_time.isoformat() if self._stop_time else None,
            'uptime': uptime
        })

        if self.generation_thread:
            self.generation_thread.join(timeout=5)

        return True

    def get_uptime(self):
        """Get system uptime in seconds"""
        if self.is_running and self._start_time:
            return (datetime.now(SRI_LANKA_TZ) - self._start_time).total_seconds()
        elif self._start_time and self._stop_time:
            return (self._stop_time - self._start_time).total_seconds()
        return 0

    def _generation_loop(self):
        """Main generation loop"""
        while self.is_running:
            try:
                self.generate_and_save_events()

                # Send statistics update with uptime
                stats = self.get_statistics()
                stats['uptime'] = self.get_uptime()
                socketio.emit('stats_update', stats)

                # Wait 10-30 seconds before next batch
                time.sleep(random.randint(10, 30))

            except Exception as e:
                print(f"Error in generation loop: {e}")
                break

    def get_statistics(self):
        """Get current system statistics"""
        with app.app_context():
            total_events = Event.query.count()
            total_responses = Response.query.count()

            # Today's stats
            today = datetime.now(SRI_LANKA_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            events_today = Event.query.filter(Event.created_at >= today).count()
            responses_today = Response.query.filter(Response.created_at >= today).count()

            # Anomaly stats
            anomalous_events = Event.query.filter_by(status='anomalous').count()

            return {
                'total_events': total_events,
                'total_responses': total_responses,
                'events_today': events_today,
                'responses_today': responses_today,
                'total_anomalies': anomalous_events,
                'anomaly_rate': round((anomalous_events / max(total_events, 1)) * 100, 2),
                'system_state': 'running' if self.is_running else 'stopped',
                'last_update': datetime.now(SRI_LANKA_TZ).isoformat(),
                'uptime': self.get_uptime(),
                'start_time': self._start_time.isoformat() if self._start_time else None
            }


# Initialize log generator
log_generator = ANBDLogGenerator()


# Authentication Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Simple authentication endpoint"""
    try:
        data = request.get_json()

        # For demo purposes, accept any username/password
        if data and data.get('username') and data.get('password'):
            return jsonify({
                'success': True,
                'access_token': 'demo-token-12345',
                'user': {
                    'username': data['username'],
                    'role': 'admin'
                }
            }), 200
        else:
            return jsonify({'error': 'Username and password required'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200


@app.route('/api/auth/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    return jsonify({
        'user': {
            'username': 'admin',
            'role': 'admin',
            'last_login': datetime.now().isoformat()
        }
    }), 200


# Dashboard Routes
@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary statistics"""
    try:
        stats = log_generator.get_statistics()

        # Add more detailed summary
        yesterday = datetime.now() - timedelta(days=1)
        recent_events = Event.query.filter(Event.created_at >= yesterday).count()
        recent_responses = Response.query.filter(Response.created_at >= yesterday).count()

        summary = {
            'total_events': stats['total_events'],
            'recent_events': recent_events,
            'total_responses': stats['total_responses'],
            'recent_responses': recent_responses,
            'total_anomalies': stats['total_anomalies'],
            'anomaly_rate': stats['anomaly_rate'],
            'system_state': stats['system_state'],
            'uptime': '0h 0m' if not log_generator.is_running else 'Running',
            'last_update': stats['last_update']
        }

        return jsonify(summary), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# API Routes
@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start the ANBD system"""
    try:
        if log_generator.start_generation():
            return jsonify({
                'message': 'System started successfully',
                'status': 'running'
            }), 200
        else:
            return jsonify({'error': 'System already running'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop the ANBD system"""
    try:
        if log_generator.stop_generation():
            return jsonify({
                'message': 'System stopped successfully',
                'status': 'stopped'
            }), 200
        else:
            return jsonify({'error': 'System not running'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get system status"""
    try:
        stats = log_generator.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/events', methods=['GET'])
def get_events():
    """Get events with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')

        query = Event.query
        if status:
            query = query.filter_by(status=status)

        events = query.order_by(Event.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'events': [event.to_dict() for event in events.items],
            'pagination': {
                'page': events.page,
                'pages': events.pages,
                'per_page': events.per_page,
                'total': events.total
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responses', methods=['GET'])
def get_responses():
    """Get responses with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        responses = Response.query.order_by(Response.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'responses': [response.to_dict() for response in responses.items],
            'pagination': {
                'page': responses.page,
                'pages': responses.pages,
                'per_page': responses.per_page,
                'total': responses.total
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/events', methods=['GET'])
def get_events_analytics():
    """Get events analytics for charts"""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.now(SRI_LANKA_TZ) - timedelta(days=days)

        # Events by status
        status_counts = db.session.query(
            Event.status, db.func.count(Event.id)
        ).filter(Event.created_at >= start_date).group_by(Event.status).all()

        # Create time series for last 24 hours
        time_series = []
        now = datetime.now(SRI_LANKA_TZ)

        for i in range(23, -1, -1):  # Last 24 hours
            hour_start = now - timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            hour_key = hour_start.strftime('%Y-%m-%d %H:00:00')

            # Count total events in this hour
            total_events = Event.query.filter(
                Event.created_at >= hour_start,
                Event.created_at < hour_end
            ).count()

            # Count anomalous events in this hour
            anomalous_events = Event.query.filter(
                Event.created_at >= hour_start,
                Event.created_at < hour_end,
                Event.status == 'anomalous'
            ).count()

            # Count normal events in this hour
            normal_events = Event.query.filter(
                Event.created_at >= hour_start,
                Event.created_at < hour_end,
                Event.status == 'normal'
            ).count()

            time_series.append({
                'time': hour_key,
                'total': total_events,
                'normal': normal_events,
                'anomalous': anomalous_events,
                'count': total_events  # For backward compatibility
            })

        return jsonify({
            'status_distribution': [{'status': status, 'count': count} for status, count in status_counts],
            'time_series': time_series
        }), 200
    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/responses', methods=['GET'])
def get_responses_analytics():
    """Get responses analytics for charts"""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Responses by anomaly type
        type1_counts = db.session.query(
            Response.anomaly_type1, db.func.count(Response.id)
        ).filter(
            Response.created_at >= start_date,
            Response.anomaly_type1.isnot(None)
        ).group_by(Response.anomaly_type1).all()

        type2_counts = db.session.query(
            Response.anomaly_type2, db.func.count(Response.id)
        ).filter(
            Response.created_at >= start_date,
            Response.anomaly_type2.isnot(None)
        ).group_by(Response.anomaly_type2).all()

        return jsonify({
            'anomaly_type1_distribution': [{'type': atype, 'count': count} for atype, count in type1_counts],
            'anomaly_type2_distribution': [{'type': atype, 'count': count} for atype, count in type2_counts]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send current status on connect
    stats = log_generator.get_statistics()
    emit('stats_update', stats)


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
        print("Database initialized")

    # Run the app
    print("Starting ANBD Flask Backend...")
    print("WebSocket enabled for real-time updates")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)