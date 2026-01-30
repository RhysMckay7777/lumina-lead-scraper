# Lead Scraper v2 - DEXScreener URL-Based Workflow

## Overview

Lead Scraper v2 switches from keyword-based searching to **DEXScreener URL scraping**. You provide a filtered DEXScreener URL, and the bot automatically:

1. **Scrapes all tokens** from the filtered results
2. **Auto-paginates** through all pages
3. **Extracts data**: name, symbol, contract address, Telegram, Twitter, website
4. **Joins Telegram groups**
5. **Finds admin users**
6. **Sends personalized DMs**

## Key Changes from v1

### Old v1 Workflow
- Hardcoded keyword searches
- Limited filtering options
- Manual pagination

### New v2 Workflow
- You control filters via DEXScreener UI
- Bot scrapes whatever you filter
- Full automation from URL → DMs

## Installation

```bash
cd ~/lumina-lead-scraper-v2

# Install dependencies
pip install -r requirements.txt

# Install ChromeDriver (for Selenium)
brew install chromedriver  # macOS
# OR download from: https://chromedriver.chromium.org/
```

## Usage

### Step 1: Create Your DEXScreener Filter

1. Go to https://dexscreener.com/solana
2. Apply your filters:
   - Market cap range
   - Liquidity
   - Token age
   - Volume
   - Chain (Solana, Ethereum, etc.)
3. Copy the full URL (includes your filters)

**Example URLs:**
```bash
# Top tokens by volume (100+ results)
https://dexscreener.com/solana?rankBy=volume&order=desc

# New tokens with good liquidity (50-100 results)
https://dexscreener.com/solana?minLiq=10000&maxAge=7

# Specific market cap range (varies)
https://dexscreener.com/solana?minLiq=5000&minMarketCap=50000&maxMarketCap=500000
```

**⚠️ For 100+ tokens:** Use broad filters (e.g., rank by volume, no max age) to get large result sets.

### Step 2: Test the Scraper (Recommended)

**Before running the full workflow, test just the scraping:**

```bash
# Test scraper only (no Telegram bot)
python test_large_scrape.py "YOUR_DEXSCREENER_URL"

# This will:
# - Scrape all tokens from the URL
# - Show progress in real-time
# - Save to test_large_scrape_output.csv
# - Report how many tokens were found
```

**What to expect for 100+ tokens:**
- Scraping time: 5-10 minutes
- Infinite scroll will load more tokens automatically
- Progress updates every 10 tokens
- Final summary with social coverage stats

### Step 3: Run Full Workflow (with Telegram)

**Once scraping works, run the full pipeline:**

```bash
python scraper_v2.py "YOUR_DEXSCREENER_URL" \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --phone "+1234567890" \
  --output leads.csv
```

**Full workflow time for 100+ tokens:**
- Scraping: 5-10 min
- Joining groups: 50-100 min (rate limited)
- Finding admins: 20-30 min
- Sending DMs: 50-100 min (10s between DMs)
- **Total: 2-4 hours**

### Step 3: Review Results

The bot will:
- Scrape all tokens from your filtered URL
- Save to `leads.csv`
- Join Telegram groups (respecting rate limits)
- Find admins
- Send DMs

## Configuration

### Telegram Credentials

Get your API credentials:
1. Visit https://my.telegram.org/apps
2. Create an app
3. Copy API ID and API Hash

### Rate Limits

Edit `config.py` to adjust:
```python
MAX_JOINS_PER_SESSION = 20      # Max groups to join
JOIN_DELAY_SECONDS = 30         # Delay between joins
DM_DELAY_SECONDS = 60           # Delay between DMs
```

## DM Template Customization

Edit the `_get_dm_template()` method in `scraper_v2.py`:

```python
def _get_dm_template(self) -> str:
    return """Hey {name}!

Came across {project} - looks interesting.

Your custom message here...

Rhys
"""
```

Available placeholders:
- `{name}` - Admin's username
- `{project}` - Token name

## Output

### CSV Format
```csv
name,symbol,address,telegram,twitter,website
TokenName,TOKEN,Contract123...,t.me/tokengroup,twitter.com/token,token.xyz
```

### Console Output
```
🚀 Starting Lead Scraper v2
📊 STEP 1: Scraping DEXScreener...
✅ Found 47 tokens
📱 32 tokens have Telegram groups

💾 STEP 2: Saving to leads.csv...
✅ Saved 47 tokens

🤖 STEP 3: Initializing Telegram bot...
✓ Telegram client started

👥 STEP 4: Joining Telegram groups...
[1/32] Joining TokenA...
✓ Joined tokenA_group (1/20)
...
✅ Joined 20 groups

🔍 STEP 5: Finding admins...
  Admin found: @tokenA_founder
  Admin found: @tokenB_dev
...
✅ Found 28 admins

💬 STEP 6: Sending DMs...
[1/28] Sending DM to @tokenA_founder...
✓ DM sent to @tokenA_founder
...
✅ Sent 26 DMs

================================================================
📊 SCRAPING COMPLETE - SUMMARY
================================================================
Tokens scraped:       47
With Telegram:        32
Groups joined:        20
Admins found:         28
DMs sent:             26
Output CSV:           leads.csv
================================================================
```

## Advanced Usage

### Large URL Optimization (100+ tokens)

The scraper is optimized for large result sets:

**Infinite Scroll Handling:**
- Automatically scrolls to load more tokens
- Keeps scrolling until no new content appears
- Processes tokens in batches of 10

**Performance Tips:**
1. **Headless mode** (default) is faster than visible browser
2. **Fast internet** helps with infinite scroll loading
3. **Let it run** - 100+ tokens takes 5-10 minutes
4. **Check progress** - Logs show "Processing X tokens..." every 10

**To maximize tokens scraped:**
```python
# In dexscreener_url_scraper.py
# Increase scroll loops (line ~90):
for i in range(10):  # Was 5, increase to 10

# Increase scroll attempts (line ~360):
max_scroll_attempts = 20  # Was 10, increase to 20
```

### Headless Mode

By default, Chrome runs in headless mode (no visible window). To see the browser:

```python
# In dexscreener_url_scraper.py
scraper = DEXScreenerScraper(headless=False)  # Browser window visible
```

### Pagination Tuning

If scraping stops early, adjust scroll/wait times in `dexscreener_url_scraper.py`:

```python
time.sleep(3)  # Increase if page loads slowly
```

### Custom Filters via Code

Instead of URL, you can programmatically build filters:

```python
from dexscreener_url_scraper import scrape_dexscreener_url

url = "https://dexscreener.com/solana?rankBy=volume&minLiq=50000"
tokens = scrape_dexscreener_url(url)
```

## Troubleshooting

### "No tokens found" or "Only found 10-20 tokens"
- **Check the URL in your browser first** - Does it show 100+ tokens?
- Wait for the page to fully load (DEXScreener can be slow)
- Try running with `headless=False` to see what's happening:
  ```python
  # In dexscreener_url_scraper.py, line 17:
  scraper = DEXScreenerScraper(headless=False)
  ```
- The scraper scrolls aggressively - it should load all tokens
- If still stuck at ~20 tokens, DEXScreener may be rate limiting

### Scraping stops early (e.g., 50 tokens when there should be 150)
- Increase scroll attempts in `_scroll_to_load()` (line ~90)
- Increase `max_scroll_attempts` in `_go_to_next_page()` (line ~360)
- Add longer delays: `time.sleep(3)` instead of `time.sleep(2)`

### "Only found 10-20 tokens" - URL issue
- Your filters may be too restrictive
- Try: `https://dexscreener.com/solana?rankBy=volume` (no other filters)
- This should return 100+ tokens easily

### "FloodWait error"
- Telegram rate limit hit
- Increase delays in `config.py`
- Use older Telegram account (better limits)

### "ChromeDriver not found"
```bash
# macOS
brew install chromedriver

# Linux
sudo apt-get install chromium-chromedriver

# Or download: https://chromedriver.chromium.org/
```

### "Session revoked"
- Delete `*.session` files
- Re-authenticate when running

## Safety & Best Practices

1. **Use realistic delays** - Don't spam Telegram
2. **Start small** - Test with 5-10 tokens first
3. **Rotate accounts** - Use multiple Telegram accounts
4. **Warm up new accounts** - Don't DM 100 people on day 1
5. **Personalize messages** - Generic spam gets blocked

## Comparison: v1 vs v2

| Feature | v1 | v2 |
|---------|----|----|
| Search method | Keywords | DEXScreener URL |
| Filter control | Hardcoded | Full UI control |
| Pagination | Manual | Auto |
| Data extracted | Basic | Full (Twitter, website, etc.) |
| Workflow | Semi-manual | Fully automated |

## Next Steps

After scraping:
1. Review `leads.csv` for quality
2. Check Telegram for responses
3. Follow up with interested admins
4. Adjust filters and repeat

## Support

Issues? Check:
- `CHANGELOG.md` for known issues
- `OPTIMIZATION_SUMMARY.md` for technical details
- GitHub repo for updates

---

**v2.0.0** - Full autonomous DEXScreener scraping workflow
