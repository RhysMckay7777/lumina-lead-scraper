#!/bin/bash
# Lumina Lead Scraper - Quick Start

cd ~/lumina_lead_scraper
source venv/bin/activate

echo "🚀 Starting Lumina Lead Scraper Web UI..."
echo ""
echo "⚠️  IMPORTANT WARNINGS:"
echo "   - Telegram automation can get your account banned"
echo "   - Max 20 group joins per session (built-in limit)"
echo "   - Use a secondary phone number recommended"
echo "   - See README.md for full safety guidelines"
echo ""
echo "📊 Opening web interface on http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
