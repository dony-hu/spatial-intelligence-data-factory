"""
Simple HTTP Server for Factory Dashboard
使用Python标准库实现轻量级Web服务器
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# Global factory state
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

class FactoryDashboardHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 处理API请求
        if path == '/api/status':
            self.send_json_response(factory_state)
        elif path == '/api/production-lines':
            self.send_json_response(factory_state.get('production_lines', {}))
        elif path == '/api/work-orders':
            self.send_json_response(factory_state.get('work_orders', {}))
        elif path == '/api/metrics':
            self.send_json_response(factory_state.get('metrics', {}))
        elif path == '/':
            # 服务主页面
            self.send_dashboard_html()
        else:
            self.send_error(404)

    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_dashboard_html(self):
        """发送仪表板HTML"""
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        """隐藏日志消息"""
        pass

    @staticmethod
    def get_dashboard_html():
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据工厂实时看板 - 两条产线</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container-fluid { max-width: 1600px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .header h1 { color: #1e3c72; margin-bottom: 10px; display: flex; align-items: center; gap: 15px; }
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            background: #28a745;
            color: white;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 4px solid #2a5298;
        }
        .metric-label { color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .metric-value { font-size: 2.5em; font-weight: 700; color: #1e3c72; margin-bottom: 5px; }
        .metric-subtitle { font-size: 0.85em; color: #999; }
        .production-lines-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .production-line-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .line-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #2a5298; }
        .line-name { font-size: 1.3em; font-weight: 700; color: #1e3c72; display: flex; align-items: center; gap: 10px; }
        .line-number { background: #2a5298; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.9em; }
        .line-status { padding: 6px 12px; background: #28a745; color: white; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
        .line-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-item { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 3px solid #2a5298; }
        .stat-label { font-size: 0.85em; color: #666; margin-bottom: 5px; }
        .stat-value { font-size: 1.8em; font-weight: 700; color: #1e3c72; }
        .progress-bar-custom { height: 8px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin-top: 10px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #2a5298, #6a82fb); border-radius: 10px; transition: width 0.3s ease; }
        .charts-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .chart-container { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; height: 350px; }
        .chart-title { color: #1e3c72; font-size: 1.1em; font-weight: 700; margin-bottom: 15px; }
        .footer { background: white; padding: 20px; border-radius: 10px; text-align: center; color: #666; font-size: 0.9em; }
        .update-indicator { display: inline-block; width: 10px; height: 10px; background: #28a745; border-radius: 50%; margin-left: 10px; animation: blink 1s infinite; }
        @keyframes blink { 0%, 50%, 100% { opacity: 1; } 25%, 75% { opacity: 0.3; } }
        h2 { color: white; margin-bottom: 20px; margin-top: 40px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="header">
            <h1>
                🏭 数据工厂实时看板
                <span class="status-badge" id="status-badge">运营中</span>
                <span class="update-indicator"></span>
            </h1>
            <p style="margin: 0; color: #666;">
                两条产线流水线系统 • 实时处理 • 每秒1条地址
            </p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">处理进度</div>
                <div class="metric-value" id="processed-count">0</div>
                <div class="metric-subtitle">已处理地址</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">完成任务</div>
                <div class="metric-value" id="completed-orders">0</div>
                <div class="metric-subtitle">总计</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">质检合格率</div>
                <div class="metric-value" id="quality-rate">0%</div>
                <div class="metric-subtitle">质检检查结果</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Token消耗</div>
                <div class="metric-value" id="total-tokens">0</div>
                <div class="metric-subtitle">累计成本</div>
            </div>
        </div>

        <h2>【两条产线运行状态】</h2>
        <div class="production-lines-section">
            <div class="production-line-card">
                <div class="line-header">
                    <div class="line-name">
                        <span class="line-number">1</span>
                        地址清洗产线
                    </div>
                    <div class="line-status" id="line1-status">运行中</div>
                </div>
                <div class="line-stats">
                    <div class="stat-item">
                        <div class="stat-label">完成任务</div>
                        <div class="stat-value" id="line1-completed">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">工人数</div>
                        <div class="stat-value" id="line1-workers">2</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">工序步数</div>
                        <div class="stat-value">3</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">成本 (tokens)</div>
                        <div class="stat-value" id="line1-tokens">0</div>
                    </div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-size: 0.9em; color: #666; margin-bottom: 8px;">
                        工序进度: <span style="color: #1e3c72; font-weight: 600;" id="line1-step">解析</span>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill" id="line1-progress" style="width: 0%;"></div>
                    </div>
                </div>
                <div style="font-size: 0.85em; color: #666; background: #f8f9fa; padding: 12px; border-radius: 8px;">
                    <div>📥 输入: 原始地址</div>
                    <div>📤 输出: 标准化地址</div>
                    <div style="margin-top: 8px; color: #2a5298; font-weight: 600;">
                        解析 → 标准化 → 验证
                    </div>
                </div>
            </div>

            <div class="production-line-card">
                <div class="line-header">
                    <div class="line-name">
                        <span class="line-number">2</span>
                        地址-图谱产线
                    </div>
                    <div class="line-status" id="line2-status">等待中</div>
                </div>
                <div class="line-stats">
                    <div class="stat-item">
                        <div class="stat-label">完成任务</div>
                        <div class="stat-value" id="line2-completed">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">工人数</div>
                        <div class="stat-value" id="line2-workers">2</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">工序步数</div>
                        <div class="stat-value">3</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">成本 (tokens)</div>
                        <div class="stat-value" id="line2-tokens">0</div>
                    </div>
                </div>
                <div style="margin-bottom: 15px;">
                    <div style="font-size: 0.9em; color: #666; margin-bottom: 8px;">
                        工序进度: <span style="color: #1e3c72; font-weight: 600;" id="line2-step">特征提取</span>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill" id="line2-progress" style="width: 0%;"></div>
                    </div>
                </div>
                <div style="font-size: 0.85em; color: #666; background: #f8f9fa; padding: 12px; border-radius: 8px;">
                    <div>📥 输入: 标准化地址</div>
                    <div>📤 输出: 图谱节点&关系</div>
                    <div style="margin-top: 8px; color: #2a5298; font-weight: 600;">
                        特征提取 → 融合 → 验证
                    </div>
                </div>
            </div>
        </div>

        <h2>【数据分析】</h2>
        <div class="charts-section">
            <div class="chart-container">
                <div class="chart-title">任务完成状态</div>
                <canvas id="workOrderChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">产线成本分布</div>
                <canvas id="costChart"></canvas>
            </div>
        </div>

        <div class="footer">
            自动刷新中... 最后更新: <span id="last-update">--:--:--</span>
        </div>
    </div>

    <script>
        let workOrderChart, costChart;

        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                const now = new Date();
                document.getElementById('last-update').textContent = 
                    now.toLocaleTimeString('zh-CN');

                document.getElementById('processed-count').textContent = 
                    data.metrics?.processed_count || 0;
                document.getElementById('completed-orders').textContent = 
                    data.work_orders?.completed || 0;
                document.getElementById('quality-rate').textContent = 
                    ((data.metrics?.quality_rate || 0) * 100).toFixed(1) + '%';
                document.getElementById('total-tokens').textContent = 
                    (data.metrics?.total_tokens || 0).toFixed(2);

                const lines = data.production_lines || {};
                
                if (lines['line_address_cleaning']) {
                    const line1 = lines['line_address_cleaning'];
                    document.getElementById('line1-completed').textContent = 
                        line1.completed_tasks || 0;
                    document.getElementById('line1-tokens').textContent = 
                        (line1.total_tokens_consumed || 0).toFixed(2);
                    document.getElementById('line1-progress').style.width = 
                        Math.min((line1.completed_tasks || 0) * 100 / 100, 100) + '%';
                }

                if (lines['line_address_to_graph']) {
                    const line2 = lines['line_address_to_graph'];
                    document.getElementById('line2-completed').textContent = 
                        line2.completed_tasks || 0;
                    document.getElementById('line2-tokens').textContent = 
                        (line2.total_tokens_consumed || 0).toFixed(2);
                    document.getElementById('line2-progress').style.width = 
                        Math.min((line2.completed_tasks || 0) * 100 / 100, 100) + '%';
                }

                updateCharts(data);
            } catch (error) {
                console.log('连接服务器中...');
            }
        }

        function updateCharts(data) {
            const workOrders = data.work_orders || {};
            
            if (workOrderChart) {
                workOrderChart.data.datasets[0].data = [
                    workOrders.completed || 0,
                    workOrders.in_progress || 0,
                    workOrders.pending || 0
                ];
                workOrderChart.update('none');
            }

            const lines = data.production_lines || {};
            if (costChart) {
                const labels = [];
                const costs = [];
                
                if (lines['line_address_cleaning']) {
                    labels.push('清洗产线');
                    costs.push(lines['line_address_cleaning'].total_tokens_consumed || 0);
                }
                if (lines['line_address_to_graph']) {
                    labels.push('图谱产线');
                    costs.push(lines['line_address_to_graph'].total_tokens_consumed || 0);
                }
                
                costChart.data.labels = labels;
                costChart.data.datasets[0].data = costs;
                costChart.update('none');
            }
        }

        function initCharts() {
            const workOrderCtx = document.getElementById('workOrderChart').getContext('2d');
            workOrderChart = new Chart(workOrderCtx, {
                type: 'doughnut',
                data: {
                    labels: ['已完成', '进行中', '等待中'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                        borderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });

            const costCtx = document.getElementById('costChart').getContext('2d');
            costChart = new Chart(costCtx, {
                type: 'bar',
                data: {
                    labels: ['清洗产线', '图谱产线'],
                    datasets: [{
                        label: 'Token消耗',
                        data: [0, 0],
                        backgroundColor: ['#2a5298', '#6a82fb'],
                        borderColor: ['#1e3c72', '#2a5298'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        window.addEventListener('DOMContentLoaded', () => {
            initCharts();
            updateDashboard();
            setInterval(updateDashboard, 1000);
        });
    </script>
</body>
</html>'''

def start_server(port=5000):
    """启动Web服务器"""
    server = HTTPServer(('127.0.0.1', port), FactoryDashboardHandler)
    print(f"🌐 Web服务器启动: http://127.0.0.1:{port}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, factory_state

def update_factory_state(new_state):
    """更新工厂状态"""
    global factory_state
    factory_state.update(new_state)
