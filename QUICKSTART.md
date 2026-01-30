# Lead Scraper v2 - Team Quickstart ⚡

**Get leads from DEXScreener in 3 steps.**

---

## Step 1: Setup (One-time)

### Get Telegram Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your Telegram
3. Create app → Copy **API ID** and **API Hash**

### Configure Credentials

```bash
cd ~/lumina-lead-scraper-v2
cp .env.example .env
nano .env  # Or use any text editor
```

Edit the values:
```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_PHONE="+447123456789"
```

Save and close.

---

## Step 2: Pick a DEXScreener URL

Go to https://dexscreener.com/solana and apply filters, then copy the URL.

**Popular options:**

**Trending (5-min):**
```
https://dexscreener.com/solana?rankBy=trendingScoreM5&order=desc
```

**High volume:**
```
https://dexscreener.com/solana?rankBy=volume&order=desc
```

**New + liquid:**
```
https://dexscreener.com/solana?minLiq=10000&maxAge=7
```

---

## Step 3: Run It

```bash
cd ~/lumina-lead-scraper-v2
./run_scraper.sh "YOUR_DEXSCREENER_URL"
```

**Example:**
```bash
./run_scraper.sh "https://dexscreener.com/solana?rankBy=trendingScoreM5&order=desc"
```

**First time?** Telegram will text you a code. Enter it.

---

## That's It!

The scraper will:
1. Scrape 150 tokens (~8 min)
2. Join Telegram groups (~1-2 hours)
3. Find admins (~30 min)
4. Send DMs (~1-2 hours)

**Total:** 3-4 hours

**Output:** `leads_YYYYMMDD_HHMMSS.csv`

---

## View Results

```bash
cat leads_*.csv | head -20
```

Or open in Excel/Google Sheets.

---

## Customize DM Message

Edit `scraper_v2.py` around line 74:

```python
return """Hey {name}!

Your message here...

Rhys
Lumina Web3"""
```

---

## Need Help?

**Full docs:** `TEAM_DEPLOYMENT.md`  
**Technical:** `LEAD_SCRAPER_FIXED.md`  
**Questions:** Ask Clawd

---

**That's the entire process.** Now go get leads! 🚀

