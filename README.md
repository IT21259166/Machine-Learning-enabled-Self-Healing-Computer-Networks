# Machine Learning-Enabled Self-Healing Computer Networks

[![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-v2.10+-orange.svg)](https://tensorflow.org/)
[![Flask](https://img.shields.io/badge/Flask-v2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌟 Overview

An integrated autonomous network management system that combines advanced machine learning techniques with real-time network monitoring to achieve self-healing capabilities. The system automatically discovers network topology, detects faults and misconfigurations, identifies anomalous behavior, and performs automated remediation with minimal human intervention.

## 🎯 Project Objectives

- **90% fault detection accuracy** across various network scenarios
- **60% reduction in Mean Time to Repair (MTTR)** through automated remediation
- **Real-time anomaly detection** with sub-30 second response times
- **Autonomous network healing** with comprehensive audit trails
- **Zero-touch network operations** for common fault scenarios

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Dashboard (React)                       │
├─────────────────────────────────────────────────────────────────┤
│                    API Gateway (Flask)                         │
├─────────────────────────────────────────────────────────────────┤
│  Component 1     │  Component 2      │  Component 3            │
│  Network Mapping │  Fault Detection  │  Anomaly Detection      │
│  & Visualization │  & Response       │  & Response             │
├─────────────────────────────────────────────────────────────────┤
│              Database Layer (PostgreSQL/MongoDB)               │
├─────────────────────────────────────────────────────────────────┤
│                    Network Infrastructure                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🧩 Components

### Component 1: Network Mapping, Visualization & Prediction
**Developer:** D. M. R. O. Dissanayake (IT21289620)

- **Deep Q-Network (DQN)** for adaptive network discovery
- **Multi-protocol support** (SNMP, ICMP, LLDP, CDP)
- **Real-time topology visualization** with interactive dashboards
- **Predictive analytics** for network performance optimization

**Key Features:**
- Autonomous network scanning and discovery
- Dynamic topology mapping with change detection
- Performance prediction using reinforcement learning
- Grafana integration for real-time monitoring

### Component 2: Device Faults-Misconfiguration Detection & Response
**Developer:** R. V. G. M. M. Shakeer Udayar (IT21308116)

- **Tree-based differential analysis** for configuration drift detection
- **Graph-based Root Cause Analysis (RCA)** for fault isolation
- **Automated remediation** using Ansible playbooks
- **Configuration compliance** monitoring and enforcement

**Key Features:**
- Real-time configuration monitoring
- Intelligent fault correlation and analysis
- Automated rollback and recovery procedures
- Compliance reporting and audit trails

### Component 3: Anomalous Network Behavior Detection & Response
**Developer:** Z. H. Muhammadh (IT21259166)

- **LSTM-VAE architecture** for temporal anomaly detection
- **Hybrid classification system** combining ML and rule-based approaches
- **Unsupervised learning** for zero-day threat detection
- **Real-time behavioral analysis** with adaptive thresholds

**Key Features:**
- Time-series anomaly detection in network traffic
- Behavioral baseline establishment and monitoring
- Automated incident response and containment
- Integration with SIEM systems

## 📋 Prerequisites

### System Requirements
- **Operating System:** Ubuntu 20.04+ / Windows 10+ / macOS 10.15+
- **RAM:** 16GB minimum, 32GB recommended
- **Storage:** 100GB available space
- **Network:** Gigabit Ethernet for optimal performance

### Software Dependencies
- Python 3.8+
- Node.js 16+
- Docker & Docker Compose
- PostgreSQL 13+
- MongoDB 5.0+
- Redis 6.0+

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/ml-selfhealing-networks.git
cd ml-selfhealing-networks
```

### 2. Environment Setup
```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for frontend
cd frontend
npm install
cd ..
```

### 3. Database Setup
```bash
# Start database services
docker-compose up -d postgres mongodb redis

# Run database migrations
python manage.py db upgrade

# Load initial data
python scripts/load_sample_data.py
```

### 4. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration file
nano .env
```

**Required Environment Variables:**
```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/selfhealing
MONGODB_URI=mongodb://localhost:27017/selfhealing
REDIS_URL=redis://localhost:6379

# Security Settings
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Network Configuration
SNMP_COMMUNITY=public
NETWORK_DISCOVERY_INTERVAL=300

# ML Model Settings
MODEL_UPDATE_INTERVAL=3600
ANOMALY_THRESHOLD=0.8
```

## 🏃‍♂️ Running the Application

### Development Mode
```bash
# Start backend services
python app.py

# Start frontend development server (new terminal)
cd frontend
npm start

# Start ML training pipeline (new terminal)
python ml_pipeline/train_models.py
```

### Production Mode
```bash
# Build and start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

### Access Points
- **Web Dashboard:** http://localhost:3000
- **API Documentation:** http://localhost:5000/api/docs
- **Grafana Dashboards:** http://localhost:3001
- **Kibana Logs:** http://localhost:5601

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/ --cov-report=html

# Run specific component tests
python -m pytest tests/component1/
python -m pytest tests/component2/
python -m pytest tests/component3/
```

### Integration Tests
```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
python -m pytest tests/integration/

# Network simulation tests
python tests/network_simulation/test_gns3_scenarios.py
```

### Performance Tests
```bash
# Load testing
python tests/performance/load_test.py

# Benchmark ML models
python tests/performance/model_benchmarks.py
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# System health endpoint
curl http://localhost:5000/health

# Component status
curl http://localhost:5000/api/v1/status
```

### Metrics & Dashboards
- **Grafana Dashboards:** Pre-configured dashboards for network topology, fault detection, and anomaly monitoring
- **Prometheus Metrics:** Custom metrics for system performance and ML model accuracy
- **ELK Stack Integration:** Centralized logging and log analysis

### Key Performance Indicators
- Network discovery coverage: >95%
- Fault detection accuracy: >90%
- Mean Time to Repair (MTTR): <5 minutes
- False positive rate: <5%
- System availability: >99.9%

## 🔒 Security

### Authentication & Authorization
- **JWT-based authentication** with role-based access control (RBAC)
- **Multi-factor authentication** for administrative access
- **API rate limiting** and request throttling

### Data Protection
- **AES-256 encryption** for sensitive configuration data
- **TLS 1.3** for all API communications
- **Database encryption** at rest and in transit

### Security Compliance
- **OWASP Top 10** mitigation strategies implemented
- **ISO/IEC 27001** security controls compliance
- **NIST Cybersecurity Framework** alignment
- **Regular security audits** and penetration testing

## 📚 API Documentation

### Core Endpoints

#### Network Discovery
```http
GET /api/v1/network/topology
POST /api/v1/network/scan
PUT /api/v1/network/devices/{device_id}
```

#### Fault Detection
```http
GET /api/v1/faults/events
POST /api/v1/faults/remediate/{fault_id}
GET /api/v1/faults/history
```

#### Anomaly Detection
```http
GET /api/v1/anomalies/detection
POST /api/v1/anomalies/threshold
GET /api/v1/anomalies/patterns
```

### WebSocket Events
```javascript
// Real-time network updates
socket.on('network:topology_changed', callback);
socket.on('faults:new_event', callback);
socket.on('anomalies:detected', callback);
```

## 🔧 Configuration

### Network Discovery Settings
```yaml
network_discovery:
  protocols: [snmp, icmp, lldp, cdp]
  scan_interval: 300  # seconds
  timeout: 30
  max_concurrent: 50
```

### ML Model Configuration
```yaml
lstm_vae:
  sequence_length: 100
  latent_dim: 32
  learning_rate: 0.001
  batch_size: 64
  epochs: 100

dqn:
  state_size: 256
  action_size: 10
  memory_size: 10000
  epsilon_decay: 0.995
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
docker-compose ps postgres mongodb

# Reset database
docker-compose down
docker volume rm ml-selfhealing-networks_postgres_data
docker-compose up -d postgres
```

#### ML Model Training Failures
```bash
# Check GPU availability
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

# Monitor training logs
tail -f logs/ml_training.log

# Restart training pipeline
python ml_pipeline/retrain_models.py
```

#### Network Discovery Issues
```bash
# Test SNMP connectivity
snmpwalk -v2c -c public target_device 1.3.6.1.2.1.1.1.0

# Check firewall rules
sudo ufw status

# Verify network permissions
sudo tcpdump -i any port 161
```

### Performance Optimization
- **Database indexing:** Ensure proper indexes on frequently queried fields
- **Memory management:** Monitor memory usage during ML training
- **Network bandwidth:** Consider rate limiting for large-scale discovery
- **Caching:** Enable Redis caching for frequently accessed data

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- **PEP 8** compliance for Python code
- **ESLint** configuration for JavaScript/React
- **Black** formatter for Python
- **Prettier** formatter for frontend code

### Testing Requirements
- Minimum 80% code coverage
- All tests must pass before merging
- Integration tests for new features
- Performance benchmarks for ML components

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

### Development Team
- **D. M. R. O. Dissanayake** (IT21289620) - Network Mapping & Visualization
- **R. V. G. M. M. Shakeer Udayar** (IT21308116) - Fault Detection & Response  
- **Z. H. Muhammadh** (IT21259166) - Anomaly Detection & Response

### Supervision
- **Dr. Harinda Fernando** - Project Supervisor

### Institution
**Sri Lanka Institute of Information Technology (SLIIT)**  
Faculty of Computing  
Final Year Project 24-25J-078

## 📞 Support

### Getting Help
- **Documentation:** [Wiki Pages](https://github.com/your-repo/ml-selfhealing-networks/wiki)
- **Issues:** [GitHub Issues](https://github.com/your-repo/ml-selfhealing-networks/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-repo/ml-selfhealing-networks/discussions)

### Contact Information
- **Project Email:** selfhealing-networks@sliit.lk
- **Supervisor:** harinda.f@sliit.lk

## 📈 Roadmap

### Version 1.0 (Current)
- ✅ Core network discovery and mapping
- ✅ Basic fault detection and remediation
- ✅ LSTM-VAE anomaly detection
- ✅ Web-based dashboard

### Version 1.1 (Q3 2025)
- 🔄 Enhanced ML model accuracy
- 🔄 Mobile application support
- 🔄 Advanced reporting capabilities
- 🔄 Cloud deployment options

### Version 2.0 (Q1 2026)
- 📋 Multi-vendor device support
- 📋 Advanced AI-driven predictions
- 📋 Enterprise integration features
- 📋 Distributed deployment architecture

## 🙏 Acknowledgments

- **SLIIT Faculty of Computing** for providing research facilities
- **Open source community** for various libraries and frameworks
- **Network administrators** who provided real-world insights
- **Beta testers** who helped identify issues and improvements

---

**Made with ❤️ by the SLIIT - Faculty of Computing**
