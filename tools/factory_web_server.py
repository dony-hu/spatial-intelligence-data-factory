"""
Factory Web Server - Real-time dashboard server using Flask
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from typing import Dict, Any

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# Global state - shared with demo script
factory_state = {
    'factory_name': 'Shanghai Data Factory',
    'status': 'running',
    'start_time': None,
    'production_lines': {},
    'work_orders': {
        'total': 0,
        'completed': 0,
        'in_progress': 0,
        'pending': 0
    },
    'metrics': {
        'total_tokens': 0.0,
        'quality_rate': 0.0,
        'processed_count': 0
    }
}

def update_state(new_state: Dict[str, Any]):
    """Update factory state from demo script"""
    global factory_state
    factory_state.update(new_state)

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get current factory status"""
    return jsonify(factory_state)

@app.route('/api/production-lines')
def get_production_lines():
    """Get all production lines status"""
    return jsonify(factory_state.get('production_lines', {}))

@app.route('/api/work-orders')
def get_work_orders():
    """Get work orders statistics"""
    return jsonify(factory_state.get('work_orders', {}))

@app.route('/api/metrics')
def get_metrics():
    """Get KPI metrics"""
    return jsonify(factory_state.get('metrics', {}))

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
