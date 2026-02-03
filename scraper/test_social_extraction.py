"""
Quick test: Extract 10 tokens with social links to verify it works
"""

import sys
from dexscreener_scraper_fixed import scrape_dexscreener_url

def main():
    url = "https://dexscreener.com/solana?rankBy=volume&order=desc"
    
    print("="*80)
    print("QUICK SOCIAL EXTRACTION TEST (10 tokens)")
    print("="*80)
    print(f"URL: {url}")
    print("\nTesting social link extraction...\n")
    
    # Scrape only 10 tokens
    tokens = scrape_dexscreener_url(url, headless=True, max_tokens=10)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    if not tokens:
        print("❌ No tokens scraped")
        return
    
    print(f"Total tokens: {len(tokens)}\n")
    
    # Show all tokens
    for i, token in enumerate(tokens, 1):
        print(f"{i}. {token['name']} ({token['symbol']})")
        print(f"   Contract: {token['address'][:30]}...")
        print(f"   Telegram: {'✅ ' + token['telegram'] if token['telegram'] else '❌ Not found'}")
        print(f"   Twitter:  {'✅ ' + token['twitter'] if token['twitter'] else '❌ Not found'}")
        print(f"   Website:  {'✅ ' + token['website'] if token['website'] else '❌ Not found'}")
        print()
    
    # Stats
    with_tg = len([t for t in tokens if t['telegram']])
    with_tw = len([t for t in tokens if t['twitter']])
    with_ws = len([t for t in tokens if t['website']])
    
    print("="*80)
    print("COVERAGE")
    print("="*80)
    print(f"Telegram: {with_tg}/{len(tokens)} ({with_tg/len(tokens)*100:.1f}%)")
    print(f"Twitter:  {with_tw}/{len(tokens)} ({with_tw/len(tokens)*100:.1f}%)")
    print(f"Website:  {with_ws}/{len(tokens)} ({with_ws/len(tokens)*100:.1f}%)")
    
    if with_tg > 0 or with_tw > 0:
        print("\n✅ SUCCESS: Social extraction is working!")
    else:
        print("\n⚠️  WARNING: No socials found. Check DEXScreener page structure.")

if __name__ == "__main__":
    main()
