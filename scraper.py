"""DEXScreener scraper for Solana tokens"""

import requests
import logging
import re
import csv
import os
from typing import List, Dict, Optional
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_telegram_link(socials: Optional[Dict]) -> Optional[str]:
    """Extract Telegram link from socials"""
    if not socials:
        return None
    
    for social in socials:
        if social.get('type') == 'telegram':
            return social.get('url')
    return None


def extract_twitter(socials: Optional[Dict]) -> Optional[str]:
    """Extract Twitter handle from socials"""
    if not socials:
        return None
    
    for social in socials:
        if social.get('type') == 'twitter':
            return social.get('url')
    return None


def extract_website(info: Optional[Dict]) -> Optional[str]:
    """Extract website from info"""
    if not info:
        return None
    
    websites = info.get('websites', [])
    if websites:
        return websites[0].get('url')
    return None


def search_tokens(search_term: str) -> List[Dict]:
    """Search for tokens on DEXScreener"""
    url = f"{config.DEXSCREENER_BASE_URL}/search?q={search_term}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pairs = data.get('pairs', [])
        logger.info(f"Found {len(pairs)} pairs for search term '{search_term}'")
        
        return pairs
    except Exception as e:
        logger.error(f"Error searching for '{search_term}': {e}")
        return []


def filter_tokens(pairs: List[Dict]) -> List[Dict]:
    """Filter tokens based on criteria"""
    filtered = []
    
    for pair in pairs:
        # Only Solana chain
        if pair.get('chainId') != 'solana':
            continue
        
        # Check market cap
        try:
            fdv = float(pair.get('fdv', 0) or 0)
            if not (config.MIN_MARKET_CAP <= fdv <= config.MAX_MARKET_CAP):
                continue
        except (ValueError, TypeError):
            continue
        
        # Check liquidity
        try:
            liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0) or 0)
            if liquidity_usd < config.MIN_LIQUIDITY:
                continue
        except (ValueError, TypeError):
            continue
        
        # Extract token info
        base_token = pair.get('baseToken', {})
        info = pair.get('info', {})
        
        token_data = {
            'symbol': base_token.get('symbol', ''),
            'name': base_token.get('name', ''),
            'address': base_token.get('address', ''),
            'mcap': fdv,
            'liquidity': liquidity_usd,
            'telegram': extract_telegram_link(info.get('socials')),
            'twitter': extract_twitter(info.get('socials')),
            'website': extract_website(info),
            'dex_url': f"https://dexscreener.com/{pair.get('chainId')}/{pair.get('pairAddress')}",
        }
        
        # Only include if has Telegram link
        if token_data['telegram']:
            filtered.append(token_data)
            logger.info(f"✓ Found: {token_data['name']} ({token_data['symbol']}) - ${int(fdv):,} mcap - TG: {token_data['telegram']}")
    
    return filtered


def scrape_all_tokens() -> List[Dict]:
    """Scrape tokens for all search terms with deduplication"""
    all_tokens = []
    seen_addresses = set()
    
    logger.info(f"Starting scrape with {len(config.SEARCH_TERMS)} search terms...")
    logger.info(f"Filters: ${config.MIN_MARKET_CAP:,} - ${config.MAX_MARKET_CAP:,} mcap, ${config.MIN_LIQUIDITY:,} liquidity")
    logger.info(f"{'='*60}")
    
    for i, term in enumerate(config.SEARCH_TERMS, 1):
        logger.info(f"[{i}/{len(config.SEARCH_TERMS)}] Searching for '{term}'...")
        pairs = search_tokens(term)
        filtered = filter_tokens(pairs)
        
        # Deduplicate by token address
        new_tokens = 0
        for token in filtered:
            if token['address'] not in seen_addresses:
                all_tokens.append(token)
                seen_addresses.add(token['address'])
                new_tokens += 1
        
        if new_tokens > 0:
            logger.info(f"  → Added {new_tokens} new tokens (total: {len(all_tokens)})")
    
    logger.info(f"{'='*60}")
    logger.info(f"✅ Scrape complete: {len(all_tokens)} unique tokens found")
    return all_tokens


def save_to_csv(tokens: List[Dict], filename: str = config.CSV_FILE):
    """Save tokens to CSV"""
    if not tokens:
        logger.warning("No tokens to save")
        return
    
    # Read existing leads to preserve dm_status if it exists
    existing_leads = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    address = row.get('address')
                    if address:
                        existing_leads[address] = {
                            'admin_username': row.get('admin_username', ''),
                            'dm_status': row.get('dm_status', ''),
                            'timestamp': row.get('timestamp', '')
                        }
        except Exception as e:
            logger.warning(f"Could not read existing CSV: {e}")
    
    # Write tokens with preserved status
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'symbol', 'name', 'mcap', 'liquidity', 'twitter', 'telegram', 
            'website', 'dex_url', 'address', 'admin_username', 'dm_status', 'timestamp'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for token in tokens:
            row = {
                'symbol': token['symbol'],
                'name': token['name'],
                'mcap': int(token['mcap']),
                'liquidity': int(token['liquidity']),
                'twitter': token.get('twitter', ''),
                'telegram': token.get('telegram', ''),
                'website': token.get('website', ''),
                'dex_url': token.get('dex_url', ''),
                'address': token['address'],
            }
            
            # Preserve existing status if token was previously processed
            if token['address'] in existing_leads:
                existing = existing_leads[token['address']]
                row['admin_username'] = existing['admin_username']
                row['dm_status'] = existing['dm_status']
                row['timestamp'] = existing['timestamp']
            else:
                row['admin_username'] = ''
                row['dm_status'] = ''
                row['timestamp'] = ''
            
            writer.writerow(row)
    
    logger.info(f"✅ Saved {len(tokens)} tokens to {filename}")


if __name__ == "__main__":
    tokens = scrape_all_tokens()
    save_to_csv(tokens)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SCRAPE SUMMARY")
    print(f"{'='*60}")
    print(f"Total unique tokens: {len(tokens)}")
    print(f"With Telegram links: {len([t for t in tokens if t['telegram']])}")
    print(f"Saved to: {config.CSV_FILE}")
    print(f"{'='*60}\n")
    
    # Show first 10
    print("First 10 tokens:")
    for i, token in enumerate(tokens[:10], 1):
        print(f"{i}. {token['name']} ({token['symbol']}) - ${int(token['mcap']):,} - {token['telegram']}")
