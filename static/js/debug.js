/**
 * ANBD Debug Dashboard JavaScript
 * Simple functions for debug interface
 */

// Auto-load data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSystemStatus();
    loadDatabaseStatus();
    loadModelStatus();
    loadLogs();
});

function loadSystemStatus() {
    fetch('/debug/system')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('system-status');
            if (data.error) {
                container.innerHTML = `<p class="status-error">Error: ${data.error}</p>`;
                return;
            }

            container.innerHTML = `
                <div class="metric">
                    <span>CPU Usage:</span>
                    <span class="${data.system.cpu_percent > 80 ? 'status-error' : 'status-good'}">${data.system.cpu_percent}%</span>
                </div>
                <div class="metric">
                    <span>Memory Usage:</span>
                    <span class="${data.system.memory_percent > 80 ? 'status-error' : 'status-good'}">${data.system.memory_percent}%</span>
                </div>
                <div class="metric">
                    <span>Disk Usage:</span>
                    <span class="${data.system.disk_percent > 90 ? 'status-error' : 'status-good'}">${data.system.disk_percent}%</span>
                </div>
                <div class="metric">
                    <span>Monitoring Status:</span>
                    <span class="${data.monitoring.status === 'running' ? 'status-good' : 'status-warning'}">${data.monitoring.status}</span>
                </div>
                <div class="metric">
                    <span>Uptime:</span>
                    <span class="status-good">${Math.round(data.monitoring.uptime_seconds)}s</span>
                </div>
            `;
        })
        .catch(error => {
            document.getElementById('system-status').innerHTML = `<p class="status-error">Failed to load: ${error}</p>`;
        });
}

function loadDatabaseStatus() {
    fetch('/debug/database')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('database-status');
            if (data.error) {
                container.innerHTML = `<p class="status-error">Error: ${data.error}</p>`;
                return;
            }

            const health = data.health.status === 'healthy' ? 'status-good' : 'status-error';

            container.innerHTML = `
                <div class="metric">
                    <span>Health:</span>
                    <span class="${health}">${data.health.status}</span>
                </div>
                <div class="metric">
                    <span>Events Count:</span>
                    <span class="status-good">${data.statistics.events_count || 0}</span>
                </div>
                <div class="metric">
                    <span>Responses Count:</span>
                    <span class="status-good">${data.statistics.responses_count || 0}</span>
                </div>
                <div class="metric">
                    <span>Pool Size:</span>
                    <span class="status-good">${data.statistics.pool_size || 'N/A'}</span>
                </div>
            `;
        })
        .catch(error => {
            document.getElementById('database-status').innerHTML = `<p class="status-error">Failed to load: ${error}</p>`;
        });
}

function loadModelStatus() {
    fetch('/debug/model')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('model-status');
            if (data.error) {
                container.innerHTML = `<p class="status-error">Error: ${data.error}</p>`;
                return;
            }

            const status = data.status === 'loaded' ? 'status-good' : 'status-error';

            container.innerHTML = `
                <div class="metric">
                    <span>Status:</span>
                    <span class="${status}">${data.status}</span>
                </div>
                <div class="metric">
                    <span>Input Shape:</span>
                    <span class="status-good">${data.input_shape ? JSON.stringify(data.input_shape) : 'N/A'}</span>
                </div>
                <div class="metric">
                    <span>Threshold:</span>
                    <span class="status-good">${data.threshold || 'N/A'}</span>
                </div>
            `;
        })
        .catch(error => {
            document.getElementById('model-status').innerHTML = `<p class="status-error">Failed to load: ${error}</p>`;
        });
}

function loadLogs() {
    fetch('/debug/logs?lines=20')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('logs-container');
            if (data.error) {
                container.innerHTML = `<p class="status-error">Error: ${data.error}</p>`;
                return;
            }

            if (data.logs && data.logs.length > 0) {
                container.innerHTML = data.logs.join('');
            } else {
                container.innerHTML = '<p class="status-warning">No logs available</p>';
            }
        })
        .catch(error => {
            document.getElementById('logs-container').innerHTML = `<p class="status-error">Failed to load: ${error}</p>`;
        });
}

function testPrediction() {
    const container = document.getElementById('test-results');
    container.innerHTML = '<p class="status-warning">Running prediction test...</p>';

    fetch('/debug/test/prediction')
        .then(response => response.json())
        .then(data => {
            if (data.test_successful) {
                container.innerHTML = `
                    <p class="status-good">✓ Prediction test successful</p>
                    <p>Anomalous: ${data.prediction_result.is_anomalous}</p>
                    <p>Error: ${data.prediction_result.reconstruction_error}</p>
                `;
            } else {
                container.innerHTML = `<p class="status-error">✗ Prediction test failed: ${data.error}</p>`;
            }
        })
        .catch(error => {
            container.innerHTML = `<p class="status-error">Test failed: ${error}</p>`;
        });
}

function testRCA1() {
    const container = document.getElementById('test-results');
    container.innerHTML = '<p class="status-warning">Running RCA Type 1 test...</p>';

    fetch('/debug/test/rca1')
        .then(response => response.json())
        .then(data => {
            if (data.test_successful) {
                container.innerHTML = `
                    <p class="status-good">✓ RCA Type 1 test successful</p>
                    <pre>${JSON.stringify(data.test_results, null, 2)}</pre>
                `;
            } else {
                container.innerHTML = `<p class="status-error">✗ RCA test failed: ${data.error}</p>`;
            }
        })
        .catch(error => {
            container.innerHTML = `<p class="status-error">Test failed: ${error}</p>`;
        });
}

function clearDatabase() {
    if (!confirm('Are you sure you want to clear the database? This cannot be undone.')) {
        return;
    }

    const container = document.getElementById('test-results');
    container.innerHTML = '<p class="status-warning">Clearing database...</p>';

    fetch('/debug/clear/database')
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                container.innerHTML = `<p class="status-good">✓ ${data.message}</p>`;
                // Refresh database status
                loadDatabaseStatus();
            } else {
                container.innerHTML = `<p class="status-error">✗ Clear failed: ${data.error}</p>`;
            }
        })
        .catch(error => {
            container.innerHTML = `<p class="status-error">Clear failed: ${error}</p>`;
        });
}

// Auto-refresh every 30 seconds
setInterval(function() {
    loadSystemStatus();
    loadDatabaseStatus();
}, 30000);