"""
Simple HTTP Server for Factory Dashboard
使用Python标准库实现轻量级Web服务器
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
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
        elif path == '/api/address-details':
            # 新API：获取地址处理详情
            self.send_json_response({
                'address_details': factory_state.get('address_details', [])
            })
        elif path == '/api/graph-data':
            # 新API：获取图谱数据（树形结构）
            all_nodes = {}
            address_details = factory_state.get('address_details', [])

            # 合并所有地址的节点
            for addr_detail in address_details:
                if 'graph_result' in addr_detail and 'nodes' in addr_detail['graph_result']:
                    nodes_dict = addr_detail['graph_result']['nodes']
                    for node_id, node in nodes_dict.items():
                        if node_id not in all_nodes:
                            all_nodes[node_id] = node

            self.send_json_response({
                'nodes': all_nodes
            })
        elif path == '/api/line-details':
            # 新API：获取特定产线的详情
            query_params = parse_qs(parsed_path.query)
            line_id = query_params.get('line_id', [''])[0]
            self.send_json_response(self._get_line_details(line_id))
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
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_dashboard_html(self):
        """发送仪表板HTML"""
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        """隐藏日志消息"""
        pass

    def _get_line_details(self, line_id: str) -> dict:
        """获取特定产线的详情"""
        address_details = factory_state.get('address_details', [])

        if line_id == 'line_address_cleaning':
            return {
                'line_id': line_id,
                'line_name': '地址清洗产线',
                'addresses': [
                    {
                        'addr_id': d['addr_id'],
                        'raw': d['raw_address'],
                        'segment': d['cleaning_result'].get('segment_text', d['raw_address']),
                        'tokens': d['cleaning_result']['tokens_used'],
                        'status': d['status']
                    }
                    for d in address_details
                ]
            }
        elif line_id == 'line_address_to_graph':
            return {
                'line_id': line_id,
                'line_name': '地址-图谱产线',
                'addresses': [
                    {
                        'addr_id': d['addr_id'],
                        'raw': d['raw_address'],
                        'segment': d['graph_result'].get('segment_result', d['raw_address']),
                        'graph_nodes': d['graph_result'].get('nodes', {}),
                        'tokens': d['graph_result']['tokens_used'],
                        'status': d['status']
                    }
                    for d in address_details
                ]
            }
        return {}

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
        .production-line-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            border-color: #2a5298;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
            overflow: auto;
        }
        .modal.show { display: block; }
        .modal-content {
            background-color: #fefefe;
            margin: 5% auto;
            padding: 0;
            width: 90%;
            max-width: 1200px;
            border-radius: 10px;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .modal-header {
            padding: 20px 30px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 10px 10px 0 0;
        }
        .modal-header h2 { color: white; margin: 0; }
        .close-btn {
            color: white;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            border: none;
            background: none;
        }
        .close-btn:hover { color: #ccc; }
        .modal-body {
            padding: 30px;
        }
        .address-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .address-table thead th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #2a5298;
            font-weight: 600;
            color: #1e3c72;
        }
        .address-table tbody tr {
            border-bottom: 1px solid #e9ecef;
        }
        .address-table tbody tr:hover {
            background: #f8f9fa;
        }
        .address-table td {
            padding: 12px;
        }
        .graph-container {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            min-height: 400px;
            border: 2px solid #e9ecef;
        }
        .graph-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .graph-stat-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #2a5298;
            text-align: center;
        }
        .graph-stat-value {
            font-size: 2em;
            font-weight: 700;
            color: #1e3c72;
        }
        .graph-stat-label {
            font-size: 0.85em;
            color: #666;
            margin-top: 5px;
        }
        .graph-svg {
            width: 100%;
            height: 400px;
            background: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .graph-node {
            fill: #2a5298;
            stroke: #1e3c72;
            stroke-width: 2px;
        }
        .graph-node-text {
            fill: white;
            font-size: 12px;
            text-anchor: middle;
            dominant-baseline: central;
        }
        .graph-link {
            stroke: #999;
            stroke-width: 1px;
        }
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
            <div class="production-line-card" onclick="showLineDetails('line_address_cleaning')" style="cursor: pointer; transition: transform 0.2s; border: 2px solid transparent;">
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
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; color: #2a5298; font-weight: 600; text-align: center;">
                        👆 点击查看详情
                    </div>
                </div>
            </div>

            <div class="production-line-card" onclick="showLineDetails('line_address_to_graph')" style="cursor: pointer; transition: transform 0.2s; border: 2px solid transparent;">
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
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; color: #2a5298; font-weight: 600; text-align: center;">
                        👆 点击查看详情和动态图谱
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

    <!-- Line Details Modal -->
    <div id="lineDetailsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalLineTitle">产线详情</h2>
                <button class="close-btn" onclick="closeLineDetails()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="graph-stats">
                    <div class="graph-stat-item">
                        <div class="graph-stat-value" id="modalAddressCount">0</div>
                        <div class="graph-stat-label">已处理地址</div>
                    </div>
                    <div class="graph-stat-item">
                        <div class="graph-stat-value" id="modalTokenCount">0</div>
                        <div class="graph-stat-label">Token消耗</div>
                    </div>
                    <div class="graph-stat-item">
                        <div class="graph-stat-value" id="modalNodeCount">0</div>
                        <div class="graph-stat-label">图谱节点</div>
                    </div>
                    <div class="graph-stat-item">
                        <div class="graph-stat-value" id="modalRelCount">0</div>
                        <div class="graph-stat-label">图谱关系</div>
                    </div>
                </div>

                <h3 style="color: #1e3c72; margin-top: 30px;">📋 处理详情</h3>
                <table class="address-table">
                    <thead>
                        <tr>
                            <th>地址ID</th>
                            <th>原始地址</th>
                            <th>处理结果</th>
                            <th>Token消耗</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody id="addressTableBody">
                    </tbody>
                </table>

                <div id="graphContainer" class="graph-container" style="display: none;">
                    <h3 style="color: #1e3c72; margin-top: 0;">📊 动态知识图谱</h3>
                    <svg id="graphVisualization" class="graph-svg">
                        <text x="50%" y="50%" text-anchor="middle" fill="#999">加载中...</text>
                    </svg>
                </div>
            </div>
        </div>
    </div>

    <script>
        let workOrderChart, costChart;

        async function updateDashboard() {
            try {
                // Add cache-busting timestamp to ensure fresh data
                const timestamp = new Date().getTime();
                const response = await fetch(`/api/status?t=${timestamp}`);
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

        // 显示产线详情模态框
        async function showLineDetails(lineId) {
            const modal = document.getElementById('lineDetailsModal');
            const timestamp = new Date().getTime();

            try {
                // 获取产线详情
                const response = await fetch(`/api/line-details?line_id=${lineId}&t=${timestamp}`);
                const lineData = await response.json();

                // 获取图谱数据
                const graphResponse = await fetch(`/api/graph-data?t=${timestamp}`);
                const graphData = await graphResponse.json();

                // 更新模态框标题
                document.getElementById('modalLineTitle').textContent = lineData.line_name + ' - 详情';
                document.getElementById('modalAddressCount').textContent = lineData.addresses?.length || 0;

                // 更新地址表
                const tbody = document.getElementById('addressTableBody');
                tbody.innerHTML = '';

                let totalTokens = 0;
                let totalNodes = 0;
                let totalRels = 0;

                if (lineData.addresses) {
                    lineData.addresses.forEach((addr, idx) => {
                        totalTokens += addr.tokens || 0;

                        const row = document.createElement('tr');
                        let resultText = '';

                        if (lineId === 'line_address_cleaning') {
                            // 显示分词结果
                            resultText = addr.segment || addr.raw;
                        } else {
                            // 显示图谱统计
                            if (addr.graph_nodes && typeof addr.graph_nodes === 'object') {
                                const nodeCount = Object.keys(addr.graph_nodes).length;
                                totalNodes += nodeCount;
                                resultText = `${nodeCount} 节点`;
                            }
                        }

                        row.innerHTML = `
                            <td>#${addr.addr_id}</td>
                            <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis;" title="${addr.raw}">${addr.raw}</td>
                            <td style="color: #2a5298; font-weight: 600;">${resultText}</td>
                            <td>${(addr.tokens || 0).toFixed(2)}</td>
                            <td><span style="color: #28a745; font-weight: 600;">${addr.status}</span></td>
                        `;
                        tbody.appendChild(row);
                    });
                }

                document.getElementById('modalTokenCount').textContent = totalTokens.toFixed(2);

                // 如果是图谱产线，显示图谱可视化
                if (lineId === 'line_address_to_graph') {
                    document.getElementById('modalNodeCount').textContent = graphData.nodes ? Object.keys(graphData.nodes).length : 0;
                    document.getElementById('modalRelCount').textContent = '--';
                    document.getElementById('graphContainer').style.display = 'block';
                    visualizeGraph(graphData.nodes || {});
                } else {
                    document.getElementById('modalNodeCount').textContent = '0';
                    document.getElementById('modalRelCount').textContent = '--';
                    document.getElementById('graphContainer').style.display = 'none';
                }

                modal.classList.add('show');
            } catch (error) {
                console.error('Error loading line details:', error);
                alert('加载详情失败: ' + error.message);
            }
        }

        // 关闭模态框
        function closeLineDetails() {
            const modal = document.getElementById('lineDetailsModal');
            modal.classList.remove('show');
        }

        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('lineDetailsModal');
            if (event.target === modal) {
                modal.classList.remove('show');
            }
        }

        // 可视化图谱 - 交互式树形星图
        function visualizeGraph(nodesData) {
            const svg = document.getElementById('graphVisualization');
            svg.innerHTML = '';

            if (!nodesData || Object.keys(nodesData).length === 0) {
                svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#999" font-size="16">暂无图谱数据</text>';
                return;
            }

            const width = svg.clientWidth || 800;
            const height = svg.clientHeight || 400;
            const centerX = width / 2;
            const centerY = height / 2;

            // 为不同类型的节点使用不同的颜色
            const nodeColors = {
                'city': '#1e3c72',      // 深蓝 - 城市（中心）
                'district': '#2a5298',  // 蓝色 - 地区
                'street': '#6a82fb',    // 浅蓝 - 街道
                'building': '#ff6b6b',  // 红色 - 建筑
                'room': '#ffa726'       // 橙色 - 房间
            };

            // 找到中心节点
            let rootNode = null;
            for (let nodeId in nodesData) {
                if (nodesData[nodeId].type === 'city') {
                    rootNode = nodesData[nodeId];
                    break;
                }
            }

            if (!rootNode) {
                svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#999" font-size="16">未找到中心节点</text>';
                return;
            }

            // 计算可见节点（根据expanded状态和加载限制）
            const visibleNodes = {};
            const nodePositions = {};

            function getVisibleChildren(parent) {
                if (!parent.children || parent.children.length === 0) return [];

                // 最多显示10个子节点
                const visibleChildren = parent.children.slice(0, 10);
                return visibleChildren;
            }

            // 添加根节点
            visibleNodes[rootNode.id] = rootNode;
            nodePositions[rootNode.id] = { x: centerX, y: centerY };

            // 添加展开的第一层节点
            if (rootNode.expanded) {
                const visibleChildren = getVisibleChildren(rootNode);
                const childCount = visibleChildren.length + (rootNode.children.length > 10 ? 1 : 0);
                const radius = Math.min(width, height) / 3;

                visibleChildren.forEach((childId, idx) => {
                    if (nodesData[childId]) {
                        visibleNodes[childId] = nodesData[childId];
                        const angle = (idx / childCount) * 2 * Math.PI;
                        nodePositions[childId] = {
                            x: centerX + radius * Math.cos(angle),
                            y: centerY + radius * Math.sin(angle)
                        };
                    }
                });

                // 添加"更多"占位符
                if (rootNode.children.length > 10) {
                    const moreId = 'more_' + rootNode.id;
                    visibleNodes[moreId] = {
                        id: moreId,
                        label: `... (${rootNode.children.length - 10}更多)`,
                        type: 'more',
                        parent: rootNode.id,
                        isMore: true
                    };
                    const angle = ((childCount - 1) / childCount) * 2 * Math.PI;
                    const radius = Math.min(width, height) / 3;
                    nodePositions[moreId] = {
                        x: centerX + radius * Math.cos(angle),
                        y: centerY + radius * Math.sin(angle)
                    };
                }
            }

            // 定义箭头标记
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
            marker.setAttribute('id', 'arrowhead');
            marker.setAttribute('markerWidth', '10');
            marker.setAttribute('markerHeight', '10');
            marker.setAttribute('refX', '9');
            marker.setAttribute('refY', '3');
            marker.setAttribute('orient', 'auto');
            const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            polygon.setAttribute('points', '0 0, 10 3, 0 6');
            polygon.setAttribute('fill', '#999');
            marker.appendChild(polygon);
            defs.appendChild(marker);
            svg.appendChild(defs);

            // 绘制连接线
            for (let nodeId in visibleNodes) {
                const node = visibleNodes[nodeId];
                if (node.parent && nodePositions[node.parent] && nodePositions[nodeId]) {
                    const source = nodePositions[node.parent];
                    const target = nodePositions[nodeId];

                    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line.setAttribute('x1', source.x);
                    line.setAttribute('y1', source.y);
                    line.setAttribute('x2', target.x);
                    line.setAttribute('y2', target.y);
                    line.setAttribute('stroke', '#ccc');
                    line.setAttribute('stroke-width', '2');
                    svg.appendChild(line);
                }
            }

            // 绘制节点
            for (let nodeId in visibleNodes) {
                const node = visibleNodes[nodeId];
                const pos = nodePositions[nodeId];
                if (!pos) continue;

                const isCenter = node.type === 'city';
                const isMore = node.isMore;
                const radius = isCenter ? 40 : isMore ? 25 : 30;

                // 节点圆形
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', pos.x);
                circle.setAttribute('cy', pos.y);
                circle.setAttribute('r', radius);
                circle.setAttribute('fill', isMore ? '#f0f0f0' : (nodeColors[node.type] || '#2a5298'));
                circle.setAttribute('stroke', isCenter ? '#fff' : '#fff');
                circle.setAttribute('stroke-width', isCenter ? '3' : '2');
                circle.setAttribute('style', 'cursor: pointer;');

                // 点击事件
                circle.onclick = (e) => {
                    e.stopPropagation();
                    if (isMore) {
                        // 点击"更多"展开更多节点
                        console.log('展开更多子节点');
                    } else {
                        // 切换节点展开状态
                        node.expanded = !node.expanded;
                        visualizeGraph(nodesData);
                    }
                };

                svg.appendChild(circle);

                // 节点标签
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', pos.x);
                text.setAttribute('y', pos.y);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('dominant-baseline', 'central');
                text.setAttribute('fill', isMore ? '#999' : 'white');
                text.setAttribute('font-size', isCenter ? '14' : '12');
                text.setAttribute('font-weight', '700');
                text.setAttribute('style', 'cursor: pointer; pointer-events: none;');
                text.textContent = node.label;
                svg.appendChild(text);

                // 节点类型标签
                if (!isMore) {
                    const typeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    typeText.setAttribute('x', pos.x);
                    typeText.setAttribute('y', pos.y + radius + 18);
                    typeText.setAttribute('text-anchor', 'middle');
                    typeText.setAttribute('fill', '#666');
                    typeText.setAttribute('font-size', '10');
                    const typeLabel = {
                        'city': '城市',
                        'district': '地区',
                        'street': '街道',
                        'building': '建筑',
                        'room': '房间'
                    }[node.type] || node.type;
                    typeText.textContent = typeLabel;
                    svg.appendChild(typeText);

                    // 展开/收起指示符
                    if (node.children && node.children.length > 0) {
                        const indicator = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        indicator.setAttribute('x', pos.x + radius + 5);
                        indicator.setAttribute('y', pos.y - radius - 5);
                        indicator.setAttribute('fill', '#666');
                        indicator.setAttribute('font-size', '16');
                        indicator.setAttribute('style', 'cursor: pointer;');
                        indicator.textContent = node.expanded ? '▼' : '▶';
                        svg.appendChild(indicator);
                    }
                }
            }
        }
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
