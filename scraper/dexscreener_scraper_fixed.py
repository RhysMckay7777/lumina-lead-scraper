"""
DEXScreener URL Scraper - FIXED VERSION
Properly extracts socials by clicking into each token's detail page
"""

import requests
import logging
import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DEXScreenerScraperFixed:
    """Scrapes tokens from DEXScreener with proper social extraction"""
    
    def __init__(self, headless: bool = True):
        """Initialize scraper with Selenium"""
        self.headless = headless
        self.driver = None
        
    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("Chrome WebDriver initialized")
        
    def scrape_url(self, dexscreener_url: str, max_tokens: int = 150) -> List[Dict]:
        """
        Scrape tokens from a DEXScreener filtered URL
        
        Args:
            dexscreener_url: Full DEXScreener URL with filters applied
            max_tokens: Maximum number of tokens to scrape (default: 150)
            
        Returns:
            List of token dictionaries with extracted data
        """
        try:
            self._init_driver()
            logger.info(f"Starting scrape of URL: {dexscreener_url}")
            logger.info(f"Max tokens to scrape: {max_tokens}")
            
            self.driver.get(dexscreener_url)
            time.sleep(5)  # Wait for initial load
            
            # Scroll to load tokens
            logger.info("Loading all tokens via infinite scroll...")
            self._scroll_to_load_all()
            
            # Get all token links
            token_links = self._get_all_token_links()
            logger.info(f"Found {len(token_links)} token links")
            
            # Limit to max_tokens
            if len(token_links) > max_tokens:
                logger.info(f"Limiting to first {max_tokens} tokens")
                token_links = token_links[:max_tokens]
            
            # Extract data from each token
            all_tokens = []
            for i, link in enumerate(token_links, 1):
                logger.info(f"[{i}/{len(token_links)}] Extracting token data...")
                
                token_data = self._extract_token_details(link)
                if token_data:
                    all_tokens.append(token_data)
                    logger.info(f"  ✅ {token_data['name']} ({token_data['symbol']}) - Telegram: {token_data['telegram'] is not None}")
                
                # Progress update
                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{len(token_links)} tokens processed")
                
                # Rate limiting
                time.sleep(1)
            
            # Summary
            logger.info("\n" + "="*80)
            logger.info("✅ SCRAPING COMPLETE")
            logger.info("="*80)
            logger.info(f"Total tokens scraped: {len(all_tokens)}")
            
            # Count tokens with socials
            with_telegram = len([t for t in all_tokens if t.get('telegram')])
            with_twitter = len([t for t in all_tokens if t.get('twitter')])
            with_website = len([t for t in all_tokens if t.get('website')])
            
            logger.info(f"Tokens with Telegram: {with_telegram} ({with_telegram/len(all_tokens)*100:.1f}%)")
            logger.info(f"Tokens with Twitter: {with_twitter} ({with_twitter/len(all_tokens)*100:.1f}%)")
            logger.info(f"Tokens with Website: {with_website} ({with_website/len(all_tokens)*100:.1f}%)")
            logger.info("="*80)
            
            return all_tokens
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")
    
    def _scroll_to_load_all(self):
        """Scroll to load all tokens (infinite scroll)"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        scroll_attempts = 0
        max_attempts = 20
        
        while scroll_attempts < max_attempts:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Check for new content
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # No new content, try a few more times
                scroll_attempts += 1
                if scroll_attempts >= 3:
                    logger.info("  Reached end of infinite scroll")
                    break
            else:
                # New content loaded
                scroll_attempts = 0
                last_height = new_height
                logger.info(f"  Loaded more tokens... (height: {new_height})")
    
    def _get_all_token_links(self) -> List[str]:
        """Get all token detail page URLs"""
        try:
            # DEXScreener uses links in table rows
            # URLs look like: /solana/ADDRESS
            links = []
            
            # Wait for table
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/solana/'], a[href*='/ethereum/'], a[href*='/']"))
            )
            
            # Get all links that look like token pages
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            
            for elem in elements:
                href = elem.get_attribute('href')
                if href and ('dexscreener.com' in href or href.startswith('/')):
                    # Check if it's a token page (has contract address pattern)
                    if re.search(r'/[a-z]+/[A-Za-z0-9]{30,}', href):
                        if href not in links:
                            links.append(href)
            
            return links
            
        except Exception as e:
            logger.error(f"Error getting token links: {e}")
            return []
    
    def _extract_token_details(self, url: str) -> Optional[Dict]:
        """Extract full token details from detail page"""
        try:
            # Navigate to token page
            self.driver.get(url)
            time.sleep(2)
            
            # Extract contract address from URL
            addr_match = re.search(r'/([A-Za-z0-9]{30,})', url)
            contract_address = addr_match.group(1) if addr_match else None
            
            if not contract_address:
                return None
            
            # Extract token name and symbol from page
            token_name = "Unknown"
            token_symbol = "UNKNOWN"
            
            try:
                # Try to find token name/symbol in header
                header_text = self.driver.find_element(By.TAG_NAME, "h1").text
                parts = header_text.split()
                if len(parts) >= 2:
                    token_symbol = parts[0]
                    token_name = " ".join(parts[1:]).strip('/')
                elif len(parts) == 1:
                    token_symbol = parts[0]
                    token_name = parts[0]
            except:
                # Fallback: use contract address
                token_name = f"Token_{contract_address[:8]}"
                token_symbol = contract_address[:6].upper()
            
            # Extract socials
            page_source = self.driver.page_source
            
            telegram = self._extract_social_from_page('t.me', page_source)
            twitter = self._extract_social_from_page('twitter.com', page_source) or \
                     self._extract_social_from_page('x.com', page_source)
            website = self._extract_website_from_page(page_source)
            
            return {
                'name': token_name,
                'symbol': token_symbol,
                'address': contract_address,
                'telegram': telegram,
                'twitter': twitter,
                'website': website
            }
            
        except Exception as e:
            logger.debug(f"Error extracting token details: {e}")
            return None
    
    def _extract_social_from_page(self, domain: str, page_source: str) -> Optional[str]:
        """Extract social link from page source"""
        # Look for href with domain
        pattern = rf'href=["\']([^"\']*{re.escape(domain)}[^"\']*)["\']'
        match = re.search(pattern, page_source)
        if match:
            url = match.group(1)
            # Clean up URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                return None  # Relative URL, skip
            return url
        return None
    
    def _extract_website_from_page(self, page_source: str) -> Optional[str]:
        """Extract website from page source (excluding social platforms)"""
        # Find all hrefs
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', page_source)
        
        for href in hrefs:
            # Skip social platforms and DEXScreener
            if any(platform in href.lower() for platform in [
                't.me', 'twitter.com', 'x.com', 'discord', 'telegram', 
                'dexscreener.com', 'facebook', 'instagram', 'youtube',
                'reddit', 'medium'
            ]):
                continue
            
            # Must be http/https
            if href.startswith('http') and '.' in href:
                return href
        
        return None


def scrape_dexscreener_url(url: str, headless: bool = True, max_tokens: int = 150) -> List[Dict]:
    """
    Convenience function to scrape a DEXScreener URL
    
    Args:
        url: DEXScreener filtered URL
        headless: Run browser in headless mode
        max_tokens: Maximum number of tokens to scrape
        
    Returns:
        List of token dictionaries
    """
    scraper = DEXScreenerScraperFixed(headless=headless)
    return scraper.scrape_url(url, max_tokens=max_tokens)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dexscreener_scraper_fixed.py <url> [max_tokens]")
        sys.exit(1)
    
    url = sys.argv[1]
    max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    
    tokens = scrape_dexscreener_url(url, headless=True, max_tokens=max_tokens)
    
    print(f"\n✅ Scraped {len(tokens)} tokens")
    print("\nSample tokens:")
    for token in tokens[:5]:
        print(f"  - {token['name']} ({token['symbol']})")
        print(f"    Address: {token['address'][:20]}...")
        print(f"    Telegram: {token['telegram']}")
        print(f"    Twitter: {token['twitter']}")
        print(f"    Website: {token['website']}")
        print()
