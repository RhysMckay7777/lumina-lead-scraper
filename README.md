# 🚀 Lumina Lead Scraper

Automated lead generation system for Solana token projects.

## ⚠️ IMPORTANT WARNINGS

### Telegram Rate Limits & Account Safety

**READ THIS BEFORE RUNNING:**

1. **Account Ban Risk**: Telegram has strict anti-spam policies. Automating joins and DMs can result in:
   - Temporary restrictions (FloodWait errors - hours to days)
   - Permanent account suspension
   - Phone number blacklisting

2. **Rate Limits Built In**:
   - Max 20 group joins per session
   - 30-second delay between joins
   - 60-second delay between DMs
   - **Still risky** - Telegram monitors patterns

3. **Recommendations**:
   - Use a **secondary phone number** for automation
   - Start with **small batches** (5-10 tokens max)
   - Monitor for FloodWait errors
   - Increase delays if you get rate limited
   - Consider manual outreach for high-value leads

4. **Legal/ToS Compliance**:
   - Violates Telegram Terms of Service
   - Use at your own risk
   - Consider this a proof-of-concept

## 🛠️ Setup

### 1. Environment Already Set Up
The virtual environment is already created at `~/lumina_lead_scraper/venv`.

### 2. Telegram Session Setup
On first run, you'll need to:
- Receive a code via SMS to +971588241651
- Enter the code when prompted
- Session file will be saved for future use

## 📋 Usage

### Option 1: Web UI (Recommended)

```bash
cd ~/lumina_lead_scraper
source venv/bin/activate
python app.py
```

Then open: http://localhost:5001

- View all leads in a dashboard
- Click "Start Scraping" to begin
- Monitor progress in real-time
- Automatically saves to `leads.csv`

### Option 2: Command Line

**Step 1: Scrape tokens from DEXScreener (no Telegram):**
```bash
cd ~/lumina_lead_scraper
source venv/bin/activate
python scraper.py
```
This creates/updates `leads.csv` with all matching tokens.

**Step 2: Test CSV reading (verify leads found):**
```bash
python test_csv_reading.py
```
Shows how many leads will be processed.

**Step 3: Run Telegram automation (CAREFUL!):**
```bash
python telegram_bot.py
```

⚠️ **On first run**, you'll need to authenticate:
- You'll receive an SMS code to +971588241651
- Enter the code when prompted
- Session file will be saved for future use

The script will:
- Read all leads from `leads.csv`
- Skip TEST entries and entries without Telegram links
- Skip already processed leads (dm_status = sent/failed)
- Process up to 20 groups per session
- Update CSV with admin usernames and dm_status

## 📊 How It Works

### 1. Token Discovery (DEXScreener)
- Searches for: trump, pepe, doge, ai, grok, meme, cat, dog, elon, bonk, wif
- Filters by:
  - Market cap: $50k - $5M
  - Liquidity: >$1k
  - Chain: Solana only
  - Must have Telegram link

### 2. Telegram Automation (Telethon)
- Joins Telegram groups (max 20 per session)
- Extracts admin usernames (skips bots)
- Sends personalized DM to first admin with username

### 3. DM Template
```
Hey! Saw you're building {token_name} - congrats on the launch.

We run Lumina, a crypto marketing agency that's helped projects like 
Stake.com and Polkadot scale user acquisition.

Open to a quick chat about growth? No pressure either way.
```

### 4. Results Tracking
All leads saved to `leads.csv`:
- symbol, name, market cap
- telegram, admin_username
- dm_status (dm_sent, dm_failed, no_admins_found)
- timestamp

## ⚙️ Configuration

Edit `config.py` to customize:
- Search terms
- Market cap range
- Liquidity threshold
- Join/DM delays
- Max joins per session
- DM template

## 🔧 Troubleshooting

### FloodWaitError
```
⚠️ FloodWait: Must wait XXs before joining/messaging again
```
**Solution**: Wait the specified time. Increase delays in config.py.

### UserPrivacyRestrictedError
```
⚠️ User has privacy settings that prevent DMs
```
**Solution**: Normal - user blocks DMs from non-contacts. Logged as 'dm_failed'.

### PeerFloodError
```
⚠️ FLOOD ERROR: Too many requests
```
**Solution**: Account is temporarily restricted. Stop automation for 24-48h.

### No admins found
- Group may not have public admin list
- All admins are bots
- Logged as 'no_admins_found'

## 📁 File Structure

```
~/lumina_lead_scraper/
├── venv/                    # Virtual environment (existing)
├── config.py                # Configuration settings
├── scraper.py               # DEXScreener scraper
├── telegram_bot.py          # Telegram automation
├── app.py                   # Flask web UI
├── leads.csv                # Output (generated)
├── lumina_session.session   # Telegram session (generated)
└── README.md                # This file
```

## 🚨 Safety Tips

1. **Start Small**: Test with 5-10 tokens first
2. **Monitor Logs**: Watch for rate limit warnings
3. **Use Burner Account**: Don't use your main Telegram
4. **Respect Privacy**: Stop if you get PeerFloodError
5. **Manual Follow-up**: Use automation for discovery, close manually

## 📞 Support

Built by Clawdbot for Lumina.

**Note**: This is a power tool. Use responsibly and at your own risk.
