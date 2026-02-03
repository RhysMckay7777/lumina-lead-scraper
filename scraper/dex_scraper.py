"""
Enhanced DEXScreener Scraper
- Accepts any DEXScreener URL (trending, new pairs, filtered)
- Scrapes multiple pages
- Filter by volume, liquidity, age, chain
- Integrates with database for deduplication
"""

import logging
import time
import re
import os
from typing import List, Dict, Optional, Callable
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class DEXScreenerScraper:
    """Enhanced DEXScreener scraper with multi-page and filter support"""
    
    SUPPORTED_CHAINS = ['solana', 'ethereum', 'base', 'arbitrum', 'polygon', 'bsc', 'avalanche']
    
    def __init__(self, headless: bool = True, page_timeout: int = 30):
        """
        Initialize the scraper
        
        Args:
            headless: Run browser in headless mode
            page_timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.page_timeout = page_timeout
        self.driver = None
    
    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Performance options
        options.add_argument('--disable-images')
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'disk-cache-size': 4096
        }
        options.add_experimental_option('prefs', prefs)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(self.page_timeout)
        logger.info("Chrome WebDriver initialized")
    
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _detect_chain_from_url(self, url: str) -> str:
        """Detect chain from DEXScreener URL"""
        for chain in self.SUPPORTED_CHAINS:
            if f'/{chain}' in url.lower() or f'chain={chain}' in url.lower():
                return chain
        return 'unknown'
    
    def _scroll_and_load(self, scroll_count: int = 10, pause: float = 2.0):
        """Scroll page to load more tokens (infinite scroll)"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        tokens_found = 0
        
        for i in range(scroll_count):
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            
            # Count current tokens
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/solana/'], a[href*='/ethereum/'], a[href*='/base/'], a[href*='/arbitrum/']")
            current_count = len(links)
            
            if current_count > tokens_found:
                tokens_found = current_count
                logger.debug(f"Scroll {i+1}: Found {tokens_found} token links")
            
            # Check if we've reached the end
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # Try one more scroll
                time.sleep(pause)
                final_height = self.driver.execute_script("return document.body.scrollHeight")
                if final_height == new_height:
                    logger.info(f"Reached end of page after {i+1} scrolls")
                    break
            
            last_height = new_height
        
        return tokens_found
    
    def _get_token_links(self, chain: str = None) -> List[str]:
        """Get all unique token page URLs from current page"""
        links = set()
        
        # Find all links to token pages
        selectors = [
            "a[href*='/solana/']",
            "a[href*='/ethereum/']",
            "a[href*='/base/']",
            "a[href*='/arbitrum/']",
            "a[href*='/polygon/']",
            "a[href*='/bsc/']",
        ]
        
        for selector in selectors:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                href = elem.get_attribute('href')
                if href and re.search(r'/[a-z]+/[A-Za-z0-9]{30,}', href):
                    # Ensure it's a full URL
                    if not href.startswith('http'):
                        href = 'https://dexscreener.com' + href
                    links.add(href)
        
        result = list(links)
        logger.info(f"Found {len(result)} unique token links")
        return result
    
    def _extract_token_data(self, token_url: str) -> Optional[Dict]:
        """Extract full token data from detail page"""
        try:
            self.driver.get(token_url)
            time.sleep(2)
            
            # Extract chain and address from URL
            url_match = re.search(r'/([a-z]+)/([A-Za-z0-9]{30,})', token_url)
            if not url_match:
                return None
            
            chain = url_match.group(1)
            contract_address = url_match.group(2)
            
            page_source = self.driver.page_source
            
            # Extract name and symbol
            name = "Unknown"
            symbol = "UNKNOWN"
            
            try:
                h1 = self.driver.find_element(By.TAG_NAME, "h1")
                header_text = h1.text.strip()
                # Format is usually "SYMBOL / Name" or just "SYMBOL"
                if '/' in header_text:
                    parts = header_text.split('/')
                    symbol = parts[0].strip()
                    name = parts[1].strip() if len(parts) > 1 else symbol
                else:
                    parts = header_text.split()
                    symbol = parts[0] if parts else contract_address[:6].upper()
                    name = ' '.join(parts[1:]) if len(parts) > 1 else symbol
            except:
                symbol = contract_address[:6].upper()
                name = f"Token_{contract_address[:8]}"
            
            # Extract socials
            telegram = self._extract_link('t.me', page_source)
            twitter = self._extract_link('twitter.com', page_source) or self._extract_link('x.com', page_source)
            website = self._extract_website(page_source)
            
            # Try to extract metrics from page
            volume_24h = self._extract_metric('volume', page_source)
            liquidity = self._extract_metric('liquidity', page_source)
            market_cap = self._extract_metric('fdv', page_source) or self._extract_metric('market cap', page_source)
            
            return {
                'address': contract_address,
                'contract_address': contract_address,
                'name': name,
                'symbol': symbol,
                'chain': chain,
                'telegram': telegram,
                'twitter': twitter,
                'website': website,
                'dexscreener_url': token_url,
                'volume_24h': volume_24h,
                'liquidity': liquidity,
                'market_cap': market_cap,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error extracting token data from {token_url}: {e}")
            return None
    
    def _extract_link(self, domain: str, page_source: str) -> Optional[str]:
        """Extract a social link from page source"""
        pattern = rf'href=["\']([^"\']*{re.escape(domain)}[^"\']*)["\']'
        match = re.search(pattern, page_source, re.IGNORECASE)
        if match:
            url = match.group(1)
            if url.startswith('//'):
                url = 'https:' + url
            return url if url.startswith('http') else None
        return None
    
    def _extract_website(self, page_source: str) -> Optional[str]:
        """Extract website (excluding social platforms)"""
        excluded = ['t.me', 'telegram', 'twitter.com', 'x.com', 'discord', 
                   'facebook', 'instagram', 'youtube', 'reddit', 'medium',
                   'dexscreener.com', 'etherscan', 'solscan', 'bscscan']
        
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', page_source)
        
        for href in hrefs:
            if not href.startswith('http'):
                continue
            
            is_excluded = any(ex in href.lower() for ex in excluded)
            if not is_excluded and '.' in href:
                # Basic validation
                try:
                    parsed = urlparse(href)
                    if parsed.netloc and len(parsed.netloc) > 3:
                        return href
                except:
                    continue
        
        return None
    
    def _extract_metric(self, metric_name: str, page_source: str) -> Optional[float]:
        """Try to extract a numeric metric from page"""
        try:
            # Look for patterns like "Volume: $1.2M" or "Liquidity: $500K"
            pattern = rf'{metric_name}[:\s]*\$?([\d,.]+)([KkMmBb])?'
            match = re.search(pattern, page_source, re.IGNORECASE)
            
            if match:
                value_str = match.group(1).replace(',', '')
                value = float(value_str)
                
                multiplier = match.group(2)
                if multiplier:
                    multipliers = {'k': 1e3, 'm': 1e6, 'b': 1e9}
                    value *= multipliers.get(multiplier.lower(), 1)
                
                return value
        except:
            pass
        
        return None
    
    def scrape_url(self, 
                   url: str, 
                   pages: int = 3,
                   max_tokens: int = 100,
                   filters: Dict = None,
                   progress_callback: Callable = None,
                   skip_addresses: set = None) -> List[Dict]:
        """
        Scrape tokens from a DEXScreener URL
        
        Args:
            url: DEXScreener URL (any filtered/trending/new pairs URL)
            pages: Number of pages to scrape (via scrolling)
            max_tokens: Maximum tokens to return
            filters: Dict with min_volume, min_liquidity, chains, etc.
            progress_callback: Function(current, total, token_data) for progress
            skip_addresses: Set of contract addresses to skip (already processed)
            
        Returns:
            List of token dictionaries
        """
        if skip_addresses is None:
            skip_addresses = set()
        
        if filters is None:
            filters = {}
        
        try:
            self._init_driver()
            
            chain = self._detect_chain_from_url(url)
            logger.info(f"Scraping URL: {url}")
            logger.info(f"Detected chain: {chain}")
            logger.info(f"Pages to scrape: {pages}, Max tokens: {max_tokens}")
            
            # Load the page
            self.driver.get(url)
            time.sleep(5)
            
            # Scroll to load more tokens (simulate pagination)
            scroll_count = pages * 5  # ~5 scrolls per "page"
            self._scroll_and_load(scroll_count=scroll_count)
            
            # Get all token links
            token_links = self._get_token_links(chain)
            
            # Filter out already-processed tokens
            original_count = len(token_links)
            token_links = [
                link for link in token_links 
                if not any(addr in link for addr in skip_addresses)
            ]
            logger.info(f"After dedup: {len(token_links)}/{original_count} tokens")
            
            # Limit tokens
            if len(token_links) > max_tokens:
                token_links = token_links[:max_tokens]
            
            # Extract data from each token
            tokens = []
            for i, link in enumerate(token_links, 1):
                logger.info(f"[{i}/{len(token_links)}] Extracting: {link}")
                
                token_data = self._extract_token_data(link)
                
                if token_data:
                    # Apply filters
                    if self._passes_filters(token_data, filters):
                        tokens.append(token_data)
                        
                        if progress_callback:
                            progress_callback(i, len(token_links), token_data)
                        
                        logger.info(f"  ✓ {token_data['name']} ({token_data['symbol']}) - TG: {bool(token_data['telegram'])}")
                    else:
                        logger.debug(f"  ✗ Filtered out: {token_data.get('name', 'Unknown')}")
                
                # Rate limiting
                time.sleep(0.5)
            
            # Summary
            with_tg = len([t for t in tokens if t.get('telegram')])
            with_web = len([t for t in tokens if t.get('website')])
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Scraping Complete")
            logger.info(f"  Total tokens: {len(tokens)}")
            logger.info(f"  With Telegram: {with_tg}")
            logger.info(f"  With Website: {with_web}")
            logger.info(f"{'='*60}")
            
            return tokens
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            self._close_driver()
    
    def _passes_filters(self, token: Dict, filters: Dict) -> bool:
        """Check if token passes all filters"""
        
        # Volume filter
        min_vol = filters.get('min_volume_24h')
        if min_vol and token.get('volume_24h'):
            if token['volume_24h'] < min_vol:
                return False
        
        max_vol = filters.get('max_volume_24h')
        if max_vol and token.get('volume_24h'):
            if token['volume_24h'] > max_vol:
                return False
        
        # Liquidity filter
        min_liq = filters.get('min_liquidity')
        if min_liq and token.get('liquidity'):
            if token['liquidity'] < min_liq:
                return False
        
        max_liq = filters.get('max_liquidity')
        if max_liq and token.get('liquidity'):
            if token['liquidity'] > max_liq:
                return False
        
        # Chain filter
        allowed_chains = filters.get('chains')
        if allowed_chains and token.get('chain'):
            if token['chain'] not in allowed_chains:
                return False
        
        # Require Telegram
        if filters.get('require_telegram', False):
            if not token.get('telegram'):
                return False
        
        return True
    
    def scrape_multiple_urls(self, 
                             urls: List[str], 
                             pages_per_url: int = 3,
                             max_tokens_per_url: int = 50,
                             filters: Dict = None,
                             skip_addresses: set = None) -> List[Dict]:
        """
        Scrape multiple DEXScreener URLs
        
        Args:
            urls: List of DEXScreener URLs
            pages_per_url: Pages to scrape per URL
            max_tokens_per_url: Max tokens per URL
            filters: Filter criteria
            skip_addresses: Addresses to skip
            
        Returns:
            Combined list of tokens (deduplicated)
        """
        all_tokens = []
        seen_addresses = set(skip_addresses or [])
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(urls)}] Scraping: {url}")
            logger.info(f"{'='*60}")
            
            tokens = self.scrape_url(
                url=url,
                pages=pages_per_url,
                max_tokens=max_tokens_per_url,
                filters=filters,
                skip_addresses=seen_addresses
            )
            
            # Add new tokens
            for token in tokens:
                addr = token.get('address')
                if addr and addr not in seen_addresses:
                    seen_addresses.add(addr)
                    all_tokens.append(token)
            
            logger.info(f"Total unique tokens so far: {len(all_tokens)}")
            
            # Pause between URLs
            if i < len(urls):
                time.sleep(5)
        
        return all_tokens


def scrape_dex(url: str, pages: int = 3, max_tokens: int = 100, 
               headless: bool = True, filters: Dict = None) -> List[Dict]:
    """
    Convenience function to scrape DEXScreener
    
    Args:
        url: DEXScreener URL
        pages: Number of pages
        max_tokens: Max tokens
        headless: Run headless
        filters: Filter criteria
        
    Returns:
        List of token dicts
    """
    scraper = DEXScreenerScraper(headless=headless)
    return scraper.scrape_url(url, pages=pages, max_tokens=max_tokens, filters=filters)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        # Default URL
        url = "https://dexscreener.com/solana?rankBy=trendingScoreH6&order=desc"
    else:
        url = sys.argv[1]
    
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print(f"\n🔍 Scraping: {url}")
    print(f"📄 Pages: {pages}")
    print()
    
    tokens = scrape_dex(url, pages=pages, max_tokens=50, headless=True)
    
    print(f"\n✅ Found {len(tokens)} tokens")
    print("\nSample tokens:")
    for t in tokens[:5]:
        print(f"  - {t['name']} ({t['symbol']})")
        print(f"    Chain: {t['chain']}")
        print(f"    Telegram: {t.get('telegram', 'N/A')}")
        print(f"    Website: {t.get('website', 'N/A')}")
        print()
