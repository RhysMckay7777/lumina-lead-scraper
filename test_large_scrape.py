"""
Test script for large DEXScreener URL scraping (100+ tokens)
"""

import sys
from dexscreener_url_scraper import scrape_dexscreener_url

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_large_scrape.py <dexscreener_url>")
        print("\nExample URLs to try:")
        print("  https://dexscreener.com/solana?rankBy=volume&order=desc")
        print("  https://dexscreener.com/solana?minLiq=10000&maxAge=7")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("="*80)
    print("DEXScreener Large URL Test")
    print("="*80)
    print(f"URL: {url}")
    print("Target: 100+ tokens")
    print("\nStarting scrape...\n")
    
    # Run scraper (headless=False to see browser)
    tokens = scrape_dexscreener_url(url, headless=True)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Total tokens scraped: {len(tokens)}")
    
    if len(tokens) >= 100:
        print("✅ SUCCESS: Scraped 100+ tokens!")
    else:
        print(f"⚠️  Only scraped {len(tokens)} tokens (target: 100+)")
        print("   Try a URL with more results or check for errors above")
    
    # Show sample
    print("\nSample tokens:")
    for token in tokens[:5]:
        print(f"  - {token['name']} ({token['symbol']})")
        print(f"    Contract: {token['address'][:20]}...")
        print(f"    Telegram: {token['telegram'] or 'N/A'}")
        print(f"    Twitter: {token['twitter'] or 'N/A'}")
        print()
    
    # Save to CSV
    import csv
    with open('test_large_scrape_output.csv', 'w', newline='', encoding='utf-8') as f:
        if tokens:
            fieldnames = ['name', 'symbol', 'address', 'telegram', 'twitter', 'website']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tokens)
    
    print(f"✅ Saved to: test_large_scrape_output.csv")

if __name__ == "__main__":
    main()
