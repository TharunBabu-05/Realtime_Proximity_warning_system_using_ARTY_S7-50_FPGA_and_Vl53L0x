import serial
import time
import threading
import json
import csv
import os
from datetime import datetime
from collections import deque
from flask import Flask, Response, render_template_string, request, jsonify

# Check for required libraries
try:
    import serial
    print(f"[INFO] Required libraries found - pyserial: {serial.__version__}")
except ImportError as e:
    print(f"[ERROR] Missing required library: {e}")
    print("[INFO] Please install: pip install pyserial flask")
    exit(1)

# --- Serial Configuration ---
SERIAL_PORT = 'COM7'
SERIAL_BAUDRATE = 9600

# --- Global Variables ---
latest_data = "No data yet"
data_history = deque(maxlen=1000)
connection_status = "Disconnected"
total_bytes = 0
message_count = 0
start_time = datetime.now()
data_logging = False
log_filename = ""

# --- Flask Setup ---
app = Flask(__name__)

# Disable Flask logging for cleaner output
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# Enhanced HTML Template
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Enhanced Serial Data Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(45deg, #2c3e50, #3498db);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .status-bar {
            display: flex;
            justify-content: space-around;
            background: #34495e;
            color: white;
            padding: 15px;
            flex-wrap: wrap;
        }
        
        .status-item {
            text-align: center;
            margin: 5px;
        }
        
        .status-value {
            font-size: 1.2rem;
            font-weight: bold;
            display: block;
        }
        
        .status-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .content-area {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
            padding: 20px;
        }
        
        @media (max-width: 1024px) {
            .content-area { grid-template-columns: 1fr; }
        }
        
        .main-display {
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .display-header {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            font-weight: 500;
        }
        
        .data-display {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #00ff00;
            line-height: 1.6;
        }
        
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .panel {
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .panel-header {
            background: #34495e;
            color: white;
            padding: 15px;
            font-weight: 500;
        }
        
        .panel-content {
            padding: 20px;
        }
        
        .input-group {
            margin-bottom: 15px;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #2c3e50;
        }
        
        .form-control {
            width: 100%;
            padding: 10px;
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            font-size: 0.9rem;
            transition: border-color 0.3s ease;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #3498db;
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .statistics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c3e50;
            display: block;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #7f8c8d;
        }
        
        .connection-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .connected {
            background: #27ae60;
            box-shadow: 0 0 10px #27ae60;
        }
        
        .disconnected {
            background: #e74c3c;
            box-shadow: 0 0 10px #e74c3c;
        }
        
        .data-line {
            margin-bottom: 8px;
            padding: 5px;
            border-left: 3px solid #3498db;
            padding-left: 10px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .timestamp {
            color: #7f8c8d;
            font-size: 0.8rem;
        }
        
        .success-message {
            color: #27ae60;
            background: rgba(39, 174, 96, 0.1);
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Serial Data Monitor</h1>
            <p>Real-time serial communication dashboard</p>
        </div>
        
        <div class="status-bar">
            <div class="status-item">
                <span class="status-value" id="connection-status">
                    <span class="connection-indicator disconnected"></span>Disconnected
                </span>
                <span class="status-label">Connection Status</span>
            </div>
            <div class="status-item">
                <span class="status-value" id="port-info">{{port}}</span>
                <span class="status-label">Port</span>
            </div>
            <div class="status-item">
                <span class="status-value" id="baudrate-info">{{baudrate}}</span>
                <span class="status-label">Baud Rate</span>
            </div>
            <div class="status-item">
                <span class="status-value" id="message-count">0</span>
                <span class="status-label">Messages</span>
            </div>
            <div class="status-item">
                <span class="status-value" id="bytes-count">0 B</span>
                <span class="status-label">Total Bytes</span>
            </div>
            <div class="status-item">
                <span class="status-value" id="uptime">00:00:00</span>
                <span class="status-label">Uptime</span>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" onclick="clearDisplay()">🗑️ Clear Display</button>
            <button class="btn btn-success" onclick="downloadData()">💾 Download Data</button>
            <button class="btn btn-warning" onclick="toggleLogging()" id="log-btn">📝 Start Logging</button>
            <label class="checkbox-group">
                <input type="checkbox" id="auto-scroll" checked onchange="toggleAutoScroll()">
                <span>Auto Scroll</span>
            </label>
            <label class="checkbox-group">
                <input type="checkbox" id="timestamps" checked onchange="toggleTimestamps()">
                <span>Show Timestamps</span>
            </label>
        </div>
        
        <div class="content-area">
            <div class="main-display">
                <div class="display-header">
                    📡 Live Serial Data Stream
                </div>
                <div class="data-display" id="data-display">
                    <div class="data-line">Waiting for data...</div>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="panel">
                    <div class="panel-header">📊 Statistics</div>
                    <div class="panel-content">
                        <div class="statistics">
                            <div class="stat-item">
                                <span class="stat-value" id="avg-msg-size">0 B</span>
                                <span class="stat-label">Avg Message Size</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="msg-rate">0/s</span>
                                <span class="stat-label">Messages/sec</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="data-rate">0 B/s</span>
                                <span class="stat-label">Data Rate</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value" id="last-message">Never</span>
                                <span class="stat-label">Last Message</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="panel">
                    <div class="panel-header">🔍 Data Filter</div>
                    <div class="panel-content">
                        <div class="input-group">
                            <label>Filter Text</label>
                            <input type="text" class="form-control" id="filter-text" 
                                   placeholder="Enter text to filter..." 
                                   onkeyup="applyFilter()">
                        </div>
                        <button class="btn btn-danger" onclick="clearFilter()" style="width: 100%;">
                            🚫 Clear Filter
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let showTimestamps = true;
        let autoScrollEnabled = true;
        let filterText = '';
        let allData = [];
        let startTime = new Date();
        
        // Server-Sent Events connection
        console.log("Starting EventSource connection...");
        const evtSource = new EventSource("/stream");
        
        evtSource.onopen = function(event) {
            console.log("EventSource connection opened");
        };
        
        evtSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                updateDisplay(data);
                updateStatistics(data);
            } catch (e) {
                console.log("Error parsing JSON, treating as plain text");
                const data = {
                    message: event.data,
                    timestamp: new Date().toISOString(),
                    status: 'Connected'
                };
                updateDisplay(data);
            }
        };
        
        evtSource.onerror = function(event) {
            console.error("EventSource error:", event);
            updateConnectionStatus("Connection Error");
        };
        
        function updateDisplay(data) {
            const display = document.getElementById('data-display');
            const timestamp = new Date(data.timestamp).toLocaleTimeString();
            
            // Store all data
            allData.push(data);
            if (allData.length > 1000) {
                allData.shift();
            }
            
            // Apply filter
            if (shouldShowMessage(data.message)) {
                const dataLine = document.createElement('div');
                dataLine.className = 'data-line';
                
                let content = '';
                if (showTimestamps) {
                    content += `<span class="timestamp">[${timestamp}] </span>`;
                }
                content += data.message;
                
                dataLine.innerHTML = content;
                display.appendChild(dataLine);
                
                // Keep only last 200 visible messages for performance
                while (display.children.length > 200) {
                    display.removeChild(display.firstChild);
                }
                
                // Auto scroll
                if (autoScrollEnabled) {
                    display.scrollTop = display.scrollHeight;
                }
            }
            
            // Update connection status
            if (data.status) {
                updateConnectionStatus(data.status);
            }
        }
        
        function updateConnectionStatus(status) {
            const statusElement = document.getElementById('connection-status');
            const indicator = statusElement.querySelector('.connection-indicator');
            
            if (status === 'Connected') {
                statusElement.innerHTML = '<span class="connection-indicator connected"></span>Connected';
            } else {
                statusElement.innerHTML = `<span class="connection-indicator disconnected"></span>${status}`;
            }
        }
        
        function updateStatistics(data) {
            if (data.stats) {
                document.getElementById('message-count').textContent = data.stats.message_count || 0;
                document.getElementById('bytes-count').textContent = formatBytes(data.stats.total_bytes || 0);
                document.getElementById('avg-msg-size').textContent = formatBytes(data.stats.avg_message_size || 0);
                document.getElementById('msg-rate').textContent = (data.stats.message_rate || 0).toFixed(1) + '/s';
                document.getElementById('data-rate').textContent = formatBytes(data.stats.data_rate || 0) + '/s';
                document.getElementById('last-message').textContent = 
                    new Date(data.timestamp).toLocaleTimeString();
            }
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function shouldShowMessage(message) {
            if (!filterText) return true;
            return message.toLowerCase().includes(filterText.toLowerCase());
        }
        
        function clearDisplay() {
            document.getElementById('data-display').innerHTML = 
                '<div class="data-line">Display cleared...</div>';
        }
        
        function toggleAutoScroll() {
            autoScrollEnabled = document.getElementById('auto-scroll').checked;
        }
        
        function toggleTimestamps() {
            showTimestamps = document.getElementById('timestamps').checked;
        }
        
        function applyFilter() {
            filterText = document.getElementById('filter-text').value;
        }
        
        function clearFilter() {
            document.getElementById('filter-text').value = '';
            filterText = '';
        }
        
        function downloadData() {
            const data = allData.map(item => 
                `"${item.timestamp}","${item.message.replace(/"/g, '""')}"`
            ).join('\\n');
            
            const blob = new Blob(['Timestamp,Message\\n' + data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `serial_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }
        
        function toggleLogging() {
            fetch('/toggle_logging', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    const btn = document.getElementById('log-btn');
                    if (data.logging) {
                        btn.textContent = '⏹️ Stop Logging';
                        btn.className = 'btn btn-danger';
                    } else {
                        btn.textContent = '📝 Start Logging';
                        btn.className = 'btn btn-warning';
                    }
                })
                .catch(error => console.log('Logging toggle error:', error));
        }
        
        // Update uptime every second
        setInterval(() => {
            const uptime = Math.floor((new Date() - startTime) / 1000);
            const hours = Math.floor(uptime / 3600).toString().padStart(2, '0');
            const minutes = Math.floor((uptime % 3600) / 60).toString().padStart(2, '0');
            const seconds = (uptime % 60).toString().padStart(2, '0');
            document.getElementById('uptime').textContent = `${hours}:${minutes}:${seconds}`;
        }, 1000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    try:
        return render_template_string(HTML_PAGE, port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE)
    except Exception as e:
        print(f"[ERROR] Template error: {e}")
        return f"<h1>Error</h1><p>{e}</p>", 500

@app.route("/stream")
def stream():
    print("[DEBUG] Stream route accessed")
    
    def event_stream():
        print("[DEBUG] Event stream generator started")
        global message_count, total_bytes, start_time
        last_time = time.time()
        last_message_count = 0
        last_bytes = 0
        
        while True:
            try:
                current_time = time.time()
                time_diff = current_time - last_time
                
                # Calculate rates every second
                message_rate = 0
                data_rate = 0
                if time_diff >= 1.0:
                    message_rate = (message_count - last_message_count) / time_diff
                    data_rate = (total_bytes - last_bytes) / time_diff
                    last_message_count = message_count
                    last_bytes = total_bytes
                    last_time = current_time
                
                # Calculate average message size
                avg_msg_size = total_bytes / max(message_count, 1)
                
                data = {
                    "message": latest_data,
                    "timestamp": datetime.now().isoformat(),
                    "status": connection_status,
                    "stats": {
                        "message_count": message_count,
                        "total_bytes": total_bytes,
                        "avg_message_size": avg_msg_size,
                        "message_rate": message_rate,
                        "data_rate": data_rate
                    }
                }
                
                json_str = json.dumps(data)
                yield f"data: {json_str}\n\n"
                time.sleep(0.2)  # Send updates every 200ms
                
            except Exception as e:
                print(f"[ERROR] Stream error: {e}")
                error_data = json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()})
                yield f"data: {error_data}\n\n"
                time.sleep(1)
    
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route("/toggle_logging", methods=["POST"])
def toggle_logging():
    global data_logging, log_filename
    
    try:
        data_logging = not data_logging
        
        if data_logging:
            log_filename = f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(log_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Data'])
            print(f"[INFO] Started logging to {log_filename}")
        else:
            print(f"[INFO] Stopped logging")
        
        return jsonify({"logging": data_logging, "filename": log_filename})
    
    except Exception as e:
        print(f"[ERROR] Logging toggle failed: {e}")
        return jsonify({"error": str(e)})

# --- Serial Reader Thread ---
def serial_reader():
    global latest_data, connection_status, total_bytes, message_count, data_history
    
    while True:
        try:
            print(f"[INFO] Attempting to connect to {SERIAL_PORT}...")
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=0.1)
            ser.dtr = False
            ser.rts = False
            connection_status = "Connected"
            print(f"[INFO] Connected to {SERIAL_PORT} at {SERIAL_BAUDRATE} baud")
            
            while True:
                if ser.in_waiting > 0:
                    data_bytes = ser.read(ser.in_waiting)
                    try:
                        data_str = data_bytes.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        data_str = f"<BIN:{data_bytes.hex()}>"
                    
                    if data_str:
                        latest_data = data_str
                        total_bytes += len(data_bytes)
                        message_count += 1
                        
                        # Store in history
                        timestamp = datetime.now()
                        data_history.append({
                            'timestamp': timestamp,
                            'data': data_str,
                            'bytes': len(data_bytes)
                        })
                        
                        # Log to file if enabled
                        if data_logging and log_filename:
                            try:
                                with open(log_filename, 'a', newline='') as f:
                                    writer = csv.writer(f)
                                    writer.writerow([timestamp.isoformat(), data_str])
                            except Exception as e:
                                print(f"[ERROR] Logging failed: {e}")
                        
                        print(f"[SERIAL] {data_str}")
                
                time.sleep(0.05)
                
        except serial.SerialException as e:
            print(f"[ERROR] Serial connection failed: {e}")
            connection_status = f"Serial Error: {str(e)}"
            latest_data = "Serial connection error"
            time.sleep(3)
            
        except Exception as e:
            print(f"[ERROR] Unexpected serial error: {e}")
            connection_status = f"Error: {str(e)}"
            time.sleep(3)

if __name__ == "__main__":
    try:
        print(f"[INFO] Enhanced Serial Monitor Starting...")
        print(f"[INFO] Configuration: {SERIAL_PORT} @ {SERIAL_BAUDRATE} baud")
        
        # Start the serial reader thread
        print(f"[INFO] Starting serial reader thread...")
        threading.Thread(target=serial_reader, daemon=True).start()
        time.sleep(1)  # Give serial thread time to start
        
        print(f"[INFO] Starting Flask web server...")
        print(f"[INFO] 🌐 Access dashboard at: http://localhost:5000")
        print(f"[INFO] 🌐 Or from network: http://10.157.212.51:5000")  # Using your IP from earlier
        print(f"[INFO] Press Ctrl+C to stop")
        
        # Run Flask
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)
        
    except KeyboardInterrupt:
        print(f"\\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Application failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[INFO] Application ended")