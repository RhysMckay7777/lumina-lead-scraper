"""Flask web UI for Lumina Lead Scraper"""

from flask import Flask, render_template, jsonify, request
import os
import csv
import asyncio
from datetime import datetime
import threading

import config
import scraper
import telegram_bot

app = Flask(__name__)

# Global state
scraping_in_progress = False
scraping_status = {
    'running': False,
    'message': 'Idle',
    'tokens_found': 0,
    'groups_joined': 0,
    'dms_sent': 0
}


def read_leads():
    """Read leads from CSV"""
    if not os.path.exists(config.CSV_FILE):
        return []
    
    leads = []
    with open(config.CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    
    return sorted(leads, key=lambda x: x.get('timestamp', ''), reverse=True)


@app.route('/')
def index():
    """Main dashboard"""
    leads = read_leads()
    
    stats = {
        'total_leads': len(leads),
        'dms_sent': len([l for l in leads if l.get('dm_status') == 'dm_sent']),
        'dms_failed': len([l for l in leads if l.get('dm_status') == 'dm_failed']),
        'no_admins': len([l for l in leads if l.get('dm_status') == 'no_admins_found']),
    }
    
    return render_template('index.html', leads=leads, stats=stats, status=scraping_status)


@app.route('/api/leads')
def api_leads():
    """API endpoint for leads"""
    leads = read_leads()
    return jsonify(leads)


@app.route('/api/status')
def api_status():
    """API endpoint for scraping status"""
    return jsonify(scraping_status)


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Trigger scraping"""
    global scraping_in_progress
    
    if scraping_in_progress:
        return jsonify({'error': 'Scraping already in progress'}), 400
    
    # Start scraping in background thread
    thread = threading.Thread(target=run_scraping_pipeline)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Scraping started'})


def run_scraping_pipeline():
    """Run the complete scraping pipeline"""
    global scraping_in_progress, scraping_status
    
    scraping_in_progress = True
    scraping_status['running'] = True
    scraping_status['message'] = 'Starting scrape...'
    
    try:
        # Step 1: Scrape tokens
        scraping_status['message'] = 'Scraping DEXScreener...'
        tokens = scraper.scrape_all_tokens()
        scraping_status['tokens_found'] = len(tokens)
        scraping_status['message'] = f'Found {len(tokens)} tokens. Processing Telegram...'
        
        if not tokens:
            scraping_status['message'] = 'No tokens found matching criteria'
            return
        
        # Step 2: Process via Telegram
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(telegram_bot.process_tokens(tokens))
        loop.close()
        
        scraping_status['message'] = 'Scraping complete!'
        
    except Exception as e:
        scraping_status['message'] = f'Error: {str(e)}'
    
    finally:
        scraping_in_progress = False
        scraping_status['running'] = False


# HTML template
@app.route('/template')
def template():
    """Serve the HTML template"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Lumina Lead Scraper</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0 0 10px 0;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }
        .btn:hover {
            background: #5568d3;
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 15px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
            font-family: monospace;
        }
        .status.running {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }
        table {
            width: 100%;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-collapse: collapse;
            overflow: hidden;
        }
        th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        a {
            color: #667eea;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Lumina Lead Scraper</h1>
        <p>Automated Solana token lead generation and outreach</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>Total Leads</h3>
            <div class="value" id="total-leads">{{ stats.total_leads }}</div>
        </div>
        <div class="stat-card">
            <h3>DMs Sent</h3>
            <div class="value" id="dms-sent">{{ stats.dms_sent }}</div>
        </div>
        <div class="stat-card">
            <h3>DMs Failed</h3>
            <div class="value" id="dms-failed">{{ stats.dms_failed }}</div>
        </div>
        <div class="stat-card">
            <h3>No Admins</h3>
            <div class="value" id="no-admins">{{ stats.no_admins }}</div>
        </div>
    </div>

    <div class="controls">
        <button class="btn" id="scrape-btn" onclick="startScrape()">
            🔍 Start Scraping
        </button>
        <div class="status" id="status">
            {{ status.message }}
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Token</th>
                <th>Symbol</th>
                <th>Market Cap</th>
                <th>Telegram</th>
                <th>Admin</th>
                <th>Status</th>
                <th>Timestamp</th>
            </tr>
        </thead>
        <tbody id="leads-table">
            {% for lead in leads %}
            <tr>
                <td><strong>{{ lead.name }}</strong></td>
                <td>{{ lead.symbol }}</td>
                <td>${{ "{:,}".format(lead.mcap|int) }}</td>
                <td><a href="{{ lead.telegram }}" target="_blank">Link</a></td>
                <td>{% if lead.admin_username %}@{{ lead.admin_username }}{% else %}-{% endif %}</td>
                <td>
                    {% if lead.dm_status == 'dm_sent' %}
                        <span class="badge badge-success">DM Sent</span>
                    {% elif lead.dm_status == 'dm_failed' %}
                        <span class="badge badge-danger">DM Failed</span>
                    {% elif lead.dm_status == 'no_admins_found' %}
                        <span class="badge badge-warning">No Admins</span>
                    {% else %}
                        <span class="badge">{{ lead.dm_status }}</span>
                    {% endif %}
                </td>
                <td>{{ lead.timestamp[:19] if lead.timestamp else '-' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        function startScrape() {
            const btn = document.getElementById('scrape-btn');
            btn.disabled = true;
            btn.textContent = '⏳ Scraping...';
            
            fetch('/api/scrape', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    startStatusPolling();
                })
                .catch(err => {
                    alert('Error: ' + err);
                    btn.disabled = false;
                    btn.textContent = '🔍 Start Scraping';
                });
        }

        function startStatusPolling() {
            const interval = setInterval(() => {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(status => {
                        const statusEl = document.getElementById('status');
                        statusEl.textContent = status.message;
                        statusEl.className = status.running ? 'status running' : 'status';
                        
                        if (!status.running) {
                            clearInterval(interval);
                            document.getElementById('scrape-btn').disabled = false;
                            document.getElementById('scrape-btn').textContent = '🔍 Start Scraping';
                            setTimeout(() => location.reload(), 2000);
                        }
                    });
            }, 2000);
        }
    </script>
</body>
</html>
"""


if __name__ == '__main__':
    # Create templates directory and save template
    os.makedirs('templates', exist_ok=True)
    
    # Save template
    template_html = """<!DOCTYPE html>
<html>
<head>
    <title>Lumina Lead Scraper</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0 0 10px 0;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }
        .btn:hover {
            background: #5568d3;
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 15px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
            font-family: monospace;
        }
        .status.running {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }
        table {
            width: 100%;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-collapse: collapse;
            overflow: hidden;
        }
        th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        a {
            color: #667eea;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Lumina Lead Scraper</h1>
        <p>Automated Solana token lead generation and outreach</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>Total Leads</h3>
            <div class="value" id="total-leads">{{ stats.total_leads }}</div>
        </div>
        <div class="stat-card">
            <h3>DMs Sent</h3>
            <div class="value" id="dms-sent">{{ stats.dms_sent }}</div>
        </div>
        <div class="stat-card">
            <h3>DMs Failed</h3>
            <div class="value" id="dms-failed">{{ stats.dms_failed }}</div>
        </div>
        <div class="stat-card">
            <h3>No Admins</h3>
            <div class="value" id="no-admins">{{ stats.no_admins }}</div>
        </div>
    </div>

    <div class="controls">
        <button class="btn" id="scrape-btn" onclick="startScrape()">
            🔍 Start Scraping
        </button>
        <div class="status" id="status">
            {{ status.message }}
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Token</th>
                <th>Symbol</th>
                <th>Market Cap</th>
                <th>Telegram</th>
                <th>Admin</th>
                <th>Status</th>
                <th>Timestamp</th>
            </tr>
        </thead>
        <tbody id="leads-table">
            {% for lead in leads %}
            <tr>
                <td><strong>{{ lead.name }}</strong></td>
                <td>{{ lead.symbol }}</td>
                <td>${{ "{:,}".format(lead.mcap|int) }}</td>
                <td><a href="{{ lead.telegram }}" target="_blank">Link</a></td>
                <td>{% if lead.admin_username %}@{{ lead.admin_username }}{% else %}-{% endif %}</td>
                <td>
                    {% if lead.dm_status == 'dm_sent' %}
                        <span class="badge badge-success">DM Sent</span>
                    {% elif lead.dm_status == 'dm_failed' %}
                        <span class="badge badge-danger">DM Failed</span>
                    {% elif lead.dm_status == 'no_admins_found' %}
                        <span class="badge badge-warning">No Admins</span>
                    {% else %}
                        <span class="badge">{{ lead.dm_status }}</span>
                    {% endif %}
                </td>
                <td>{{ lead.timestamp[:19] if lead.timestamp else '-' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        function startScrape() {
            const btn = document.getElementById('scrape-btn');
            btn.disabled = true;
            btn.textContent = '⏳ Scraping...';
            
            fetch('/api/scrape', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    startStatusPolling();
                })
                .catch(err => {
                    alert('Error: ' + err);
                    btn.disabled = false;
                    btn.textContent = '🔍 Start Scraping';
                });
        }

        function startStatusPolling() {
            const interval = setInterval(() => {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(status => {
                        const statusEl = document.getElementById('status');
                        statusEl.textContent = status.message;
                        statusEl.className = status.running ? 'status running' : 'status';
                        
                        if (!status.running) {
                            clearInterval(interval);
                            document.getElementById('scrape-btn').disabled = false;
                            document.getElementById('scrape-btn').textContent = '🔍 Start Scraping';
                            setTimeout(() => location.reload(), 2000);
                        }
                    });
            }, 2000);
        }
    </script>
</body>
</html>"""
    
    with open('templates/index.html', 'w') as f:
        f.write(template_html)
    
    app.run(host='0.0.0.0', port=config.WEB_PORT, debug=True)
