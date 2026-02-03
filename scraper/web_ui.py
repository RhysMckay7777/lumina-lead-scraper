#!/usr/bin/env python3
"""
Lumina Lead Scraper - Web Interface
Simple UI for configuring and running the scraper without editing code
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import subprocess
import threading
import os
import json

app = Flask(__name__)

CONFIG_FILE = "config.json"
LOG_FILE = "scraper.log"

# Default config
DEFAULT_CONFIG = {
    "min_mcap": 100000,
    "max_mcap": 1200000,
    "min_liquidity": 1000,
    "max_age_days": 7,
    "chain": "solana",
    "telegram_api_id": "",
    "telegram_api_hash": "",
    "telegram_phone": "",
    "delay_between_joins": 30,
    "max_joins_per_session": 30,
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Lumina Lead Scraper</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        body { background: #0a0a0a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00ff88; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 30px; }
        .card { background: #1a1a1a; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
        .card h2 { margin-top: 0; color: #00ff88; font-size: 18px; }
        .form-row { display: flex; gap: 20px; margin-bottom: 15px; }
        .form-group { flex: 1; }
        label { display: block; color: #888; font-size: 12px; margin-bottom: 5px; text-transform: uppercase; }
        input { width: 100%; background: #0a0a0a; border: 1px solid #333; color: #fff; padding: 12px; border-radius: 8px; font-size: 14px; }
        input:focus { outline: none; border-color: #00ff88; }
        .btn { background: #00ff88; color: #000; border: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #00cc6a; }
        .btn:disabled { background: #333; color: #666; cursor: not-allowed; }
        .btn-secondary { background: #333; color: #fff; }
        .btn-secondary:hover { background: #444; }
        .status { padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .status.success { background: rgba(0,255,136,0.1); border: 1px solid #00ff88; }
        .status.error { background: rgba(255,0,0,0.1); border: 1px solid #ff4444; }
        .status.running { background: rgba(255,200,0,0.1); border: 1px solid #ffcc00; }
        .log-output { background: #0a0a0a; border: 1px solid #333; border-radius: 8px; padding: 15px; font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto; white-space: pre-wrap; }
        .help-text { color: #666; font-size: 12px; margin-top: 5px; }
        .section-divider { border-top: 1px solid #333; margin: 20px 0; padding-top: 20px; }
        .actions { display: flex; gap: 10px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Lumina Lead Scraper</h1>
        <p class="subtitle">Automated crypto token lead generation</p>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="card">
            <h2>📊 DEXScreener Filters</h2>
            <div class="form-row">
                <div class="form-group">
                    <label>Min Market Cap ($)</label>
                    <input type="number" id="min_mcap" value="{{ config.min_mcap }}">
                </div>
                <div class="form-group">
                    <label>Max Market Cap ($)</label>
                    <input type="number" id="max_mcap" value="{{ config.max_mcap }}">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Min Liquidity ($)</label>
                    <input type="number" id="min_liquidity" value="{{ config.min_liquidity }}">
                </div>
                <div class="form-group">
                    <label>Max Age (Days)</label>
                    <input type="number" id="max_age_days" value="{{ config.max_age_days }}">
                </div>
            </div>
            <div class="form-group">
                <label>Blockchain</label>
                <input type="text" id="chain" value="{{ config.chain }}">
                <p class="help-text">solana, ethereum, base, arbitrum, etc.</p>
            </div>
        </div>
        
        <div class="card">
            <h2>📱 Telegram Credentials</h2>
            <p class="help-text" style="margin-bottom: 15px;">Get these from <a href="https://my.telegram.org/apps" target="_blank" style="color: #00ff88;">my.telegram.org/apps</a> (use a burner account!)</p>
            <div class="form-row">
                <div class="form-group">
                    <label>API ID</label>
                    <input type="text" id="telegram_api_id" value="{{ config.telegram_api_id }}" placeholder="12345678">
                </div>
                <div class="form-group">
                    <label>API Hash</label>
                    <input type="text" id="telegram_api_hash" value="{{ config.telegram_api_hash }}" placeholder="abcdef1234567890">
                </div>
            </div>
            <div class="form-group">
                <label>Phone Number</label>
                <input type="text" id="telegram_phone" value="{{ config.telegram_phone }}" placeholder="+44123456789">
            </div>
            
            <div class="section-divider">
                <h3 style="color: #888; font-size: 14px; margin-bottom: 15px;">Rate Limiting</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label>Delay Between Joins (seconds)</label>
                        <input type="number" id="delay_between_joins" value="{{ config.delay_between_joins }}">
                    </div>
                    <div class="form-group">
                        <label>Max Joins Per Session</label>
                        <input type="number" id="max_joins_per_session" value="{{ config.max_joins_per_session }}">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="actions">
            <button class="btn" onclick="saveAndRun()">▶️ Save & Run Scraper</button>
            <button class="btn btn-secondary" onclick="saveConfig()">💾 Save Config</button>
            <button class="btn btn-secondary" onclick="downloadCSV()">📥 Download CSV</button>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>📋 Live Output</h2>
            <div id="log" class="log-output">Click "Save & Run Scraper" to start...</div>
        </div>
    </div>
    
    <script>
        function getConfig() {
            return {
                min_mcap: parseInt(document.getElementById('min_mcap').value),
                max_mcap: parseInt(document.getElementById('max_mcap').value),
                min_liquidity: parseInt(document.getElementById('min_liquidity').value),
                max_age_days: parseInt(document.getElementById('max_age_days').value),
                chain: document.getElementById('chain').value,
                telegram_api_id: document.getElementById('telegram_api_id').value,
                telegram_api_hash: document.getElementById('telegram_api_hash').value,
                telegram_phone: document.getElementById('telegram_phone').value,
                delay_between_joins: parseInt(document.getElementById('delay_between_joins').value),
                max_joins_per_session: parseInt(document.getElementById('max_joins_per_session').value),
            };
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        async function saveConfig() {
            const config = getConfig();
            const response = await fetch('/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            const result = await response.json();
            showStatus(result.message, result.status);
        }
        
        async function saveAndRun() {
            await saveConfig();
            showStatus('🔄 Scraper is running...', 'running');
            
            const response = await fetch('/run', {method: 'POST'});
            const result = await response.json();
            
            if (result.status === 'running') {
                pollLogs();
            }
        }
        
        async function pollLogs() {
            const logDiv = document.getElementById('log');
            
            const poll = async () => {
                const response = await fetch('/logs');
                const data = await response.json();
                logDiv.textContent = data.logs;
                logDiv.scrollTop = logDiv.scrollHeight;
                
                if (data.running) {
                    setTimeout(poll, 1000);
                } else {
                    showStatus('✅ Scraper finished!', 'success');
                }
            };
            
            poll();
        }
        
        function downloadCSV() {
            window.location.href = '/download';
        }
    </script>
</body>
</html>
'''

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

scraper_process = None
scraper_running = False

@app.route('/')
def index():
    config = load_config()
    return render_template_string(HTML_TEMPLATE, config=config)

@app.route('/save', methods=['POST'])
def save():
    config = request.json
    save_config(config)
    
    # Also update scraper.py with new config
    update_scraper_config(config)
    
    return jsonify({'status': 'success', 'message': '✅ Configuration saved!'})

@app.route('/run', methods=['POST'])
def run():
    global scraper_process, scraper_running
    
    if scraper_running:
        return jsonify({'status': 'error', 'message': 'Scraper already running'})
    
    # Clear log file
    with open(LOG_FILE, 'w') as f:
        f.write('')
    
    # Run scraper in background
    def run_scraper():
        global scraper_process, scraper_running
        scraper_running = True
        
        with open(LOG_FILE, 'w') as log:
            scraper_process = subprocess.Popen(
                ['python3', 'scraper.py'],
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            scraper_process.wait()
        
        scraper_running = False
    
    thread = threading.Thread(target=run_scraper)
    thread.start()
    
    return jsonify({'status': 'running', 'message': 'Scraper started'})

@app.route('/logs')
def logs():
    global scraper_running
    
    log_content = ''
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            log_content = f.read()
    
    return jsonify({'logs': log_content, 'running': scraper_running})

@app.route('/download')
def download():
    if os.path.exists('leads.csv'):
        return send_file('leads.csv', as_attachment=True)
    return 'No CSV file found', 404

def update_scraper_config(config):
    """Update the scraper.py file with new config values"""
    scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scraper.py')
    
    if not os.path.exists(scraper_path):
        return
    
    with open(scraper_path, 'r') as f:
        content = f.read()
    
    # Update config values
    replacements = [
        ('MIN_MCAP = \\d+', f"MIN_MCAP = {config['min_mcap']}"),
        ('MAX_MCAP = \\d+', f"MAX_MCAP = {config['max_mcap']}"),
        ('MIN_LIQUIDITY = \\d+', f"MIN_LIQUIDITY = {config['min_liquidity']}"),
        ('MAX_AGE_DAYS = \\d+', f"MAX_AGE_DAYS = {config['max_age_days']}"),
        ('CHAIN = "[^"]*"', f'CHAIN = "{config["chain"]}"'),
        ('DELAY_BETWEEN_JOINS = \\d+', f"DELAY_BETWEEN_JOINS = {config['delay_between_joins']}"),
        ('MAX_JOINS_PER_SESSION = \\d+', f"MAX_JOINS_PER_SESSION = {config['max_joins_per_session']}"),
    ]
    
    # Handle Telegram credentials
    api_id = config.get('telegram_api_id', '')
    api_hash = config.get('telegram_api_hash', '')
    phone = config.get('telegram_phone', '')
    
    if api_id:
        replacements.append(('API_ID = None', f'API_ID = {api_id}'))
        replacements.append((f'API_ID = \\d+', f'API_ID = {api_id}'))
    if api_hash:
        replacements.append(('API_HASH = None', f'API_HASH = "{api_hash}"'))
        replacements.append((f'API_HASH = "[^"]*"', f'API_HASH = "{api_hash}"'))
    if phone:
        replacements.append(('PHONE_NUMBER = None', f'PHONE_NUMBER = "{phone}"'))
        replacements.append((f'PHONE_NUMBER = "[^"]*"', f'PHONE_NUMBER = "{phone}"'))
    
    import re
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    with open(scraper_path, 'w') as f:
        f.write(content)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Lumina Lead Scraper - Web Interface")
    print("="*50)
    print("\nOpen in browser: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
