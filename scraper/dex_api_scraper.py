"""
DEXScreener API Scraper - Uses official API instead of web scraping
More reliable than web scraping (no Cloudflare issues)
"""

import requests
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DEXScreenerAPI:
    """Scrapes tokens using DEXScreener's public API"""
    
    BASE_URL = "https://api.dexscreener.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
    
    def get_trending_tokens(self, chain: str = None, limit: int = 100) -> List[Dict]:
        """Get top trending tokens (boosted)"""
        url = f"{self.BASE_URL}/token-boosts/top/v1"
        
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            tokens = resp.json()
            
            # Filter by chain if specified
            if chain:
                tokens = [t for t in tokens if t.get('chainId', '').lower() == chain.lower()]
            
            # Get full details for each token
            detailed_tokens = []
            for token in tokens[:limit]:
                details = self._get_token_details(token.get('tokenAddress'), token.get('chainId'))
                if details:
                    detailed_tokens.append(details)
                time.sleep(0.5)  # Rate limiting
            
            return detailed_tokens
            
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            return []
    
    def get_new_pairs(self, chain: str = "solana", limit: int = 100) -> List[Dict]:
        """Get recently created pairs"""
        url = f"{self.BASE_URL}/token-profiles/latest/v1"
        
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            profiles = resp.json()
            
            # Filter by chain
            if chain:
                profiles = [p for p in profiles if p.get('chainId', '').lower() == chain.lower()]
            
            # Get full details
            detailed = []
            for profile in profiles[:limit]:
                details = self._get_token_details(profile.get('tokenAddress'), profile.get('chainId'))
                if details:
                    detailed.append(details)
                time.sleep(0.5)
            
            return detailed
            
        except Exception as e:
            logger.error(f"Error fetching new pairs: {e}")
            return []
    
    def search_tokens(self, query: str, limit: int = 100) -> List[Dict]:
        """Search for tokens by name/symbol"""
        url = f"{self.BASE_URL}/latest/dex/search?q={query}"
        
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get('pairs', [])[:limit]
            
            return [self._format_pair(p) for p in pairs]
            
        except Exception as e:
            logger.error(f"Error searching tokens: {e}")
            return []
    
    def get_pairs_by_chain(self, chain: str, limit: int = 100) -> List[Dict]:
        """Get pairs for a specific chain"""
        # Use search with chain filter
        url = f"{self.BASE_URL}/latest/dex/pairs/{chain}"
        
        try:
            resp = self.session.get(url)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get('pairs', [])[:limit]
                return [self._format_pair(p) for p in pairs]
        except:
            pass
        
        # Fallback to search
        return self.search_tokens(chain, limit)
    
    def _get_token_details(self, token_address: str, chain: str) -> Optional[Dict]:
        """Get detailed info for a specific token"""
        url = f"{self.BASE_URL}/latest/dex/tokens/{token_address}"
        
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get('pairs', [])
            
            if not pairs:
                return None
            
            # Use the first pair as representative
            return self._format_pair(pairs[0])
            
        except Exception as e:
            logger.debug(f"Error fetching token details: {e}")
            return None
    
    def _format_pair(self, pair: Dict) -> Dict:
        """Format pair data into standardized token dict"""
        base_token = pair.get('baseToken', {})
        info = pair.get('info', {})
        socials = info.get('socials', [])
        
        # Extract socials
        telegram = None
        twitter = None
        website = None
        
        for social in socials:
            social_type = social.get('type', '').lower()
            social_url = social.get('url', '')
            
            if social_type == 'telegram':
                telegram = social_url
            elif social_type == 'twitter':
                twitter = social_url
        
        # Website from info
        websites = info.get('websites', [])
        if websites:
            website = websites[0].get('url')
        
        return {
            'name': base_token.get('name', 'Unknown'),
            'symbol': base_token.get('symbol', ''),
            'address': base_token.get('address', ''),
            'chain': pair.get('chainId', ''),
            'dex': pair.get('dexId', ''),
            'pair_address': pair.get('pairAddress', ''),
            'price_usd': pair.get('priceUsd'),
            'volume_24h': float(pair.get('volume', {}).get('h24', 0) or 0),
            'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0) or 0),
            'market_cap': float(pair.get('marketCap', 0) or 0),
            'created_at': pair.get('pairCreatedAt'),
            'telegram': telegram,
            'twitter': twitter,
            'website': website,
            'dexscreener_url': pair.get('url', f"https://dexscreener.com/{pair.get('chainId', 'solana')}/{pair.get('pairAddress', '')}"),
            'scraped_at': datetime.now().isoformat()
        }
    
    def scrape_with_filters(
        self,
        chain: str = "solana",
        min_volume: float = 10000,
        min_liquidity: float = 5000,
        max_age_hours: int = 168,
        limit: int = 100
    ) -> List[Dict]:
        """
        Scrape tokens with filters applied
        
        Args:
            chain: Blockchain to filter (solana, ethereum, base, etc)
            min_volume: Minimum 24h volume in USD
            min_liquidity: Minimum liquidity in USD
            max_age_hours: Maximum age of pair in hours
            limit: Maximum tokens to return
        """
        logger.info(f"Scraping {chain} tokens with filters...")
        logger.info(f"  Min volume: ${min_volume:,}")
        logger.info(f"  Min liquidity: ${min_liquidity:,}")
        logger.info(f"  Max age: {max_age_hours}h")
        
        # Get trending tokens first
        all_tokens = self.get_trending_tokens(chain, limit * 2)
        
        # Also get new pairs
        new_pairs = self.get_new_pairs(chain, limit)
        all_tokens.extend(new_pairs)
        
        # Remove duplicates
        seen = set()
        unique_tokens = []
        for token in all_tokens:
            addr = token.get('address', '')
            if addr and addr not in seen:
                seen.add(addr)
                unique_tokens.append(token)
        
        # Apply filters
        filtered = []
        now = datetime.now()
        
        for token in unique_tokens:
            # Volume filter
            if token.get('volume_24h', 0) < min_volume:
                continue
            
            # Liquidity filter
            if token.get('liquidity_usd', 0) < min_liquidity:
                continue
            
            # Age filter
            created_at = token.get('created_at')
            if created_at:
                try:
                    created = datetime.fromtimestamp(created_at / 1000)
                    age_hours = (now - created).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        continue
                except:
                    pass
            
            filtered.append(token)
            
            if len(filtered) >= limit:
                break
        
        logger.info(f"✅ Found {len(filtered)} tokens matching filters")
        logger.info(f"  With Telegram: {len([t for t in filtered if t.get('telegram')])}")
        logger.info(f"  With Website: {len([t for t in filtered if t.get('website')])}")
        
        return filtered


def test_scraper():
    """Test the scraper"""
    scraper = DEXScreenerAPI()
    
    print("🧪 Testing DEXScreener API Scraper\n")
    
    # Test trending
    print("1. Getting trending tokens...")
    trending = scraper.get_trending_tokens("solana", limit=5)
    print(f"   Found {len(trending)} trending tokens")
    for t in trending[:3]:
        print(f"   - {t['name']} ({t['symbol']}) | Vol: ${t['volume_24h']:,.0f} | TG: {t['telegram'] or 'None'}")
    
    # Test with filters
    print("\n2. Testing with filters...")
    filtered = scraper.scrape_with_filters(
        chain="solana",
        min_volume=10000,
        min_liquidity=5000,
        limit=10
    )
    print(f"   Found {len(filtered)} filtered tokens")
    for t in filtered[:3]:
        print(f"   - {t['name']} | Vol: ${t['volume_24h']:,.0f} | Liq: ${t['liquidity_usd']:,.0f}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_scraper()
