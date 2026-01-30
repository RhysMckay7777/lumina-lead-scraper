#!/bin/bash
# Test the scraper only (no Telegram automation)

cd ~/lumina_lead_scraper
source venv/bin/activate

echo "🔍 Testing DEXScreener scraper (no Telegram automation)..."
echo ""

python scraper.py
