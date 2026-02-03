# Lumina Lead Scraper v2 - Autonomous Edition

A 24/7 autonomous lead generation system for crypto projects. Scrapes DEXScreener for new tokens, checks Google indexing, joins Telegram groups, and sends personalized outreach to admins.

## 🚀 Features

### Core Features
- **DEXScreener Scraping**: Scrape any DEXScreener URL (trending, new pairs, filtered)
- **Multi-page Support**: Scrape multiple pages via infinite scroll
- **Filter System**: Filter by volume, liquidity, age, chain
- **Google Index Check**: Identify projects with unindexed websites (easy SEO wins!)
- **Telegram Automation**: Auto-join groups, find admins, send personalized DMs
- **Rate Limiting**: Built-in protection against Telegram flood errors
- **SQLite Tracking**: Never re-message the same project twice

### Autonomous Monitoring
- **24/7 Daemon**: Runs continuously as a background service
- **Active Hours**: Configurable operating hours
- **Auto-Recovery**: Automatic restart on crashes
- **Error Handling**: Pauses on repeated errors, resumes automatically

### Reporting
- **Daily Reports**: Summary of activity sent to Telegram
- **Weekly Reports**: Aggregated weekly statistics
- **Funnel Analysis**: Track discovery → contact → response rates

## 📦 Installation

```bash
cd ~/lumina-lead-scraper-v2/scraper

# Install dependencies
./scraper_ctl.sh install

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# URLs to monitor
dexscreener:
  urls_to_monitor:
    - "https://dexscreener.com/solana?rankBy=trendingScoreH6"
    - "https://dexscreener.com/solana/new-pairs"

# Filters
  filters:
    min_volume_24h: 10000
    min_liquidity: 5000
    chains: [solana, ethereum, base]

# Telegram settings
telegram:
  rate_limits:
    max_joins_per_hour: 10
    max_dms_per_hour: 5

# Message template
  message_template: |
    Hey! Saw you're building {project_name}...
```

## 🎮 Usage

### Control Script

```bash
# Start the daemon
./scraper_ctl.sh start

# Stop the daemon  
./scraper_ctl.sh stop

# Check status
./scraper_ctl.sh status

# Follow live logs
./scraper_ctl.sh logs

# Run single cycle (test mode)
./scraper_ctl.sh test

# Generate reports
./scraper_ctl.sh report

# View database stats
./scraper_ctl.sh db
```

### Manual Operation

```bash
# Scrape DEXScreener URL
python dex_scraper.py "https://dexscreener.com/solana?rankBy=trendingScoreH6"

# Check Google index
python google_index_checker.py https://example.com

# Generate report
python daily_report.py --type daily
python daily_report.py --type weekly
python daily_report.py --type overall
```

## 📊 Components

| File | Description |
|------|-------------|
| `autonomous_scraper.py` | 24/7 daemon that orchestrates everything |
| `dex_scraper.py` | Enhanced DEXScreener scraper |
| `google_index_checker.py` | Checks if websites are indexed on Google |
| `telegram_automator.py` | Telegram group joining and DM automation |
| `database.py` | SQLite database for tracking all activity |
| `daily_report.py` | Report generation |
| `config.yaml` | All configuration in one place |
| `scraper_ctl.sh` | Control script for daemon management |

## 🔒 Rate Limits

The system respects Telegram's limits to avoid bans:

- **Group joins**: 10 per hour, 50 per day
- **DMs**: 5 per hour, 30 per day
- **Delays**: 30s between joins, 60s between DMs
- **Cooldowns**: 15 min after DM, 5 min after join

## 📝 Database Schema

The SQLite database tracks:

- **projects**: All discovered tokens and their metadata
- **telegram_groups**: Join attempts and results
- **admins**: Discovered group admins
- **messages**: All sent messages and responses
- **daily_metrics**: Daily statistics
- **error_log**: Errors for debugging

## 🚦 Workflow

1. **Scrape**: Monitor DEXScreener URLs for new tokens
2. **Filter**: Apply volume/liquidity/chain filters
3. **Dedupe**: Skip tokens already in database
4. **Index Check**: Check if website is on Google
5. **Join**: Join Telegram groups (unindexed sites first)
6. **Find Admins**: Identify group administrators
7. **DM**: Send personalized outreach message
8. **Track**: Record everything in database
9. **Report**: Daily summaries delivered to Telegram

## 🐛 Troubleshooting

### Telegram FloodWait
If you see FloodWait errors, the system will automatically pause. You can:
1. Reduce `max_joins_per_hour` and `max_dms_per_hour` in config
2. Increase delay times
3. Wait for the specified time

### Chrome Driver Issues
```bash
# Install Chrome and ChromeDriver
brew install --cask google-chrome
brew install chromedriver
```

### Logs Location
- Daemon logs: `~/clawd/scraper-logs/daemon.stdout.log`
- Scraper logs: `~/clawd/scraper-logs/scraper_YYYY-MM-DD.log`

## 📄 License

MIT License
