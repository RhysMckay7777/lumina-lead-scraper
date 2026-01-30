#!/bin/bash
# Lead Scraper v2 - Team Runner Script
# Makes it easy to run the scraper without remembering commands

echo "=========================================="
echo "  Lead Scraper v2 - Team Edition"
echo "=========================================="
echo ""

# Check if URL is provided
if [ -z "$1" ]; then
    echo "❌ Error: DEXScreener URL required"
    echo ""
    echo "Usage:"
    echo "  ./run_scraper.sh \"DEXSCREENER_URL\" [api-id] [api-hash] [phone]"
    echo ""
    echo "Example:"
    echo "  ./run_scraper.sh \"https://dexscreener.com/solana?rankBy=volume\" 12345678 abcdef123 \"+447123456789\""
    echo ""
    echo "Popular URLs:"
    echo "  Trending (5min): https://dexscreener.com/solana?rankBy=trendingScoreM5&order=desc"
    echo "  High volume:     https://dexscreener.com/solana?rankBy=volume&order=desc"
    echo "  New + liquid:    https://dexscreener.com/solana?minLiq=10000&maxAge=7"
    echo ""
    exit 1
fi

URL="$1"

# Check if credentials are provided or use environment variables
if [ ! -z "$2" ]; then
    API_ID="$2"
    API_HASH="$3"
    PHONE="$4"
else
    # Try to load from .env file
    if [ -f .env ]; then
        echo "📄 Loading credentials from .env file..."
        source .env
    else
        echo "❌ Error: Telegram credentials required"
        echo ""
        echo "Either:"
        echo "1. Provide them as arguments:"
        echo "   ./run_scraper.sh \"URL\" API_ID API_HASH PHONE"
        echo ""
        echo "2. Create .env file with:"
        echo "   TELEGRAM_API_ID=12345678"
        echo "   TELEGRAM_API_HASH=abcdef1234567890"
        echo "   TELEGRAM_PHONE=\"+447123456789\""
        echo ""
        exit 1
    fi
fi

# Verify credentials are set
if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$PHONE" ]; then
    echo "❌ Error: Missing credentials"
    echo "API_ID: ${API_ID:-NOT SET}"
    echo "API_HASH: ${API_HASH:-NOT SET}"
    echo "PHONE: ${PHONE:-NOT SET}"
    exit 1
fi

echo "✅ Configuration:"
echo "   URL: $URL"
echo "   API ID: $API_ID"
echo "   Phone: $PHONE"
echo ""
echo "Starting scraper..."
echo "This will take 3-4 hours. You can Ctrl+C to pause anytime."
echo ""
echo "=========================================="
echo ""

# Run the scraper
python3 scraper_v2.py "$URL" \
    --api-id "$API_ID" \
    --api-hash "$API_HASH" \
    --phone "$PHONE" \
    --output "leads_$(date +%Y%m%d_%H%M%S).csv"

echo ""
echo "=========================================="
echo "✅ Scraper finished!"
echo "Check leads_*.csv for results"
echo "=========================================="
