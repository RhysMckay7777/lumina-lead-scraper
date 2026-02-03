"""Configuration for Lumina Lead Scraper"""

# Telegram API credentials
TELEGRAM_API_ID = 33859061
TELEGRAM_API_HASH = "e82facfac85ca6b0e89a9368fadf0103"
TELEGRAM_PHONE = "+971588241651"
TELEGRAM_SESSION_FILE = "lumina_session.session"

# DEXScreener configuration
DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest/dex"
CHAIN = "solana"

# Search terms for token discovery
SEARCH_TERMS = [
    "trump", "pepe", "doge", "ai", "grok", "meme", "cat", "dog", "elon", "bonk", "wif",
    "pump", "moon", "shib", "floki", "wojak", "chad", "based", "ape", "monkey", "frog",
    "bull", "bear", "gold", "diamond", "gem", "100x", "launch", "new", "hot", "trending"
]

# Filter criteria
MIN_MARKET_CAP = 10000  # $10k
MAX_MARKET_CAP = 10000000  # $10M
MIN_LIQUIDITY = 500  # $500

# Telegram automation settings
JOIN_DELAY_SECONDS = 30  # Delay between joining groups
MAX_JOINS_PER_SESSION = 20  # Maximum groups to join per session
DM_DELAY_SECONDS = 60  # Delay between sending DMs

# DM template
DM_TEMPLATE = """Hey! Saw you're building {token_name} - congrats on the launch.

We run Lumina, a crypto marketing agency that's helped projects like Stake.com and Polkadot scale user acquisition.

Open to a quick chat about growth? No pressure either way."""

# CSV output
CSV_FILE = "leads.csv"

# Web UI settings
WEB_PORT = 5001
