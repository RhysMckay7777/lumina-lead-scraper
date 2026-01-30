"""
DEXScreener URL Scraper - Extract tokens from filtered DEXScreener URLs
Handles pagination automatically until all results are scraped.
"""

import requests
import logging
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DEXScreenerScraper:
    """Scrapes tokens from DEXScreener filtered URLs with auto-pagination"""
    
    def __init__(self, headless: bool = True):
        """Initialize scraper with Selenium"""
        self.headless = headless
        self.driver = None
        self.tokens_scraped = []
        
    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("Chrome WebDriver initialized")
        
    def scrape_url(self, dexscreener_url: str) -> List[Dict]:
        """
        Scrape all tokens from a DEXScreener filtered URL
        
        Args:
            dexscreener_url: Full DEXScreener URL with filters applied
            
        Returns:
            List of token dictionaries with extracted data
        """
        try:
            self._init_driver()
            logger.info(f"Starting scrape of URL: {dexscreener_url}")
            
            self.driver.get(dexscreener_url)
            time.sleep(3)  # Wait for initial load
            
            page_num = 1
            all_tokens = []
            no_new_tokens_count = 0
            max_no_new_attempts = 3
            
            while True:
                logger.info(f"Scraping page {page_num}...")
                
                # Scroll aggressively to load all tokens on current view
                self._scroll_to_load()
                
                # Extract tokens from current page
                tokens = self._extract_tokens_from_page()
                
                if not tokens:
                    logger.info("No tokens found on current view.")
                    no_new_tokens_count += 1
                    if no_new_tokens_count >= max_no_new_attempts:
                        logger.info("No new tokens after multiple attempts. Scraping complete.")
                        break
                else:
                    no_new_tokens_count = 0  # Reset counter
                
                # Add new tokens (avoid duplicates)
                new_count = 0
                for token in tokens:
                    if not any(t['address'] == token['address'] for t in all_tokens):
                        all_tokens.append(token)
                        new_count += 1
                
                logger.info(f"Found {new_count} new tokens on page {page_num}. Total: {len(all_tokens)}")
                
                # If no new tokens found, try pagination
                if new_count == 0:
                    logger.info("No new tokens, attempting pagination...")
                    if not self._go_to_next_page():
                        logger.info("No more pages available.")
                        break
                    page_num += 1
                    time.sleep(2)
                else:
                    # Got new tokens, continue scrolling current page
                    time.sleep(1)
            
            # Summary
            logger.info("\n" + "="*80)
            logger.info("✅ SCRAPING COMPLETE")
            logger.info("="*80)
            logger.info(f"Total tokens scraped: {len(all_tokens)}")
            logger.info(f"Pages/views processed: {page_num}")
            
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
            return []
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")
    
    def _scroll_to_load(self):
        """Scroll page to trigger lazy loading - aggressive for large pages"""
        try:
            # Get current height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll down in chunks
            scroll_pause = 1.5
            for i in range(5):  # Multiple scrolls to load more
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                
                # Check if new content loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # No more content
                last_height = new_height
            
        except Exception as e:
            logger.warning(f"Error during scroll: {e}")
    
    def _extract_tokens_from_page(self) -> List[Dict]:
        """Extract token data from current page"""
        tokens = []
        
        try:
            # Wait for token rows to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr, .token-row, [data-testid='token-row'], a[href*='/']"))
            )
            
            # DEXScreener uses table rows - try most specific selector first
            selectors = [
                "table tbody tr",  # Most common
                "tbody tr",
                ".token-row",
                "[data-testid='token-row']",
                "div[class*='TokenRow']",
                "a[href*='/'][class*='row']"
            ]
            
            rows = []
            for selector in selectors:
                rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if rows and len(rows) > 2:  # Need at least a few rows
                    logger.debug(f"Using selector: {selector} ({len(rows)} rows)")
                    break
            
            if not rows:
                logger.warning("No token rows found with any selector")
                return []
            
            logger.info(f"Processing {len(rows)} potential token rows...")
            
            processed = 0
            for row in rows:
                try:
                    token_data = self._extract_token_from_row(row)
                    if token_data:
                        tokens.append(token_data)
                        processed += 1
                        if processed % 10 == 0:
                            logger.info(f"  Processed {processed} tokens...")
                except Exception as e:
                    logger.debug(f"Error extracting token from row: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(tokens)} valid tokens from this view")
            return tokens
            
        except TimeoutException:
            logger.warning("Timeout waiting for token rows")
            return []
        except Exception as e:
            logger.error(f"Error extracting tokens: {e}")
            return []
    
    def _extract_token_from_row(self, row) -> Optional[Dict]:
        """Extract token data from a single row element"""
        try:
            # Get the row's HTML and text
            html = row.get_attribute('innerHTML')
            text = row.text
            
            # Extract contract address from href (DEXScreener links to contract)
            contract_address = None
            try:
                # Try href first
                href = row.get_attribute('href')
                if href:
                    addr_match = re.search(r'([1-9A-HJ-NP-Za-km-z]{32,44})', href)
                    if addr_match:
                        contract_address = addr_match.group(1)
            except:
                pass
            
            # Fallback: search in HTML
            if not contract_address:
                addr_match = re.search(r'([1-9A-HJ-NP-Za-km-z]{32,44})', html)
                contract_address = addr_match.group(1) if addr_match else None
            
            if not contract_address:
                logger.debug("No contract address found in row")
                return None
            
            # Extract token name and symbol from text
            token_name = None
            token_symbol = None
            
            # Try to parse from text (usually format: "TokenName SYMBOL")
            text_lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if text_lines:
                # Look for token name/symbol pattern
                for line in text_lines[:5]:  # Check first 5 lines
                    # Pattern: "TokenName (SYMBOL)" or "TokenName SYMBOL"
                    name_symbol_match = re.search(r'([A-Za-z0-9\s]+?)[\s\(]+([A-Z0-9]{2,10})[\)\s]?', line)
                    if name_symbol_match:
                        token_name = name_symbol_match.group(1).strip()
                        token_symbol = name_symbol_match.group(2).strip()
                        break
            
            # Fallback: use first two non-empty lines
            if not token_name and len(text_lines) >= 2:
                token_name = text_lines[0]
                token_symbol = text_lines[1] if len(text_lines[1]) <= 10 else text_lines[0][:10]
            
            if not token_name:
                token_name = f"Token_{contract_address[:8]}"
                token_symbol = "UNKNOWN"
            
            # Try to extract socials from HTML without clicking (faster)
            telegram = self._extract_social_from_html(html, 't.me')
            twitter = self._extract_social_from_html(html, 'twitter.com', 'x.com')
            website = self._extract_website_from_html(html)
            
            token_data = {
                'name': token_name,
                'symbol': token_symbol,
                'address': contract_address,
                'telegram': telegram,
                'twitter': twitter,
                'website': website
            }
            
            logger.debug(f"Extracted: {token_name} ({token_symbol}) - {contract_address[:8]}...")
            return token_data
            
        except Exception as e:
            logger.debug(f"Error parsing token row: {e}")
            return None
    
    def _extract_social_from_html(self, html: str, *domains) -> Optional[str]:
        """Extract social link from HTML"""
        for domain in domains:
            match = re.search(rf'href=["\']([^"\']*{re.escape(domain)}[^"\']*)["\']', html)
            if match:
                return match.group(1)
        return None
    
    def _extract_website_from_html(self, html: str) -> Optional[str]:
        """Extract website from HTML (excluding social platforms)"""
        # Find all href links
        links = re.findall(r'href=["\']([^"\']+)["\']', html)
        for link in links:
            # Skip social platforms
            if any(platform in link.lower() for platform in ['t.me', 'twitter.com', 'x.com', 'discord', 'telegram', 'dexscreener.com']):
                continue
            # Must be http/https
            if link.startswith('http'):
                return link
        return None
    
    def _extract_telegram_from_detail(self) -> Optional[str]:
        """Extract Telegram link from detail view"""
        try:
            # Look for Telegram link in socials section
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='t.me'], a[href*='telegram']")
            for elem in elements:
                href = elem.get_attribute('href')
                if 't.me' in href or 'telegram' in href:
                    return href
        except Exception as e:
            logger.debug(f"Error extracting Telegram: {e}")
        return None
    
    def _extract_twitter_from_detail(self) -> Optional[str]:
        """Extract Twitter link from detail view"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='twitter.com'], a[href*='x.com']")
            for elem in elements:
                href = elem.get_attribute('href')
                if 'twitter.com' in href or 'x.com' in href:
                    return href
        except Exception as e:
            logger.debug(f"Error extracting Twitter: {e}")
        return None
    
    def _extract_website_from_detail(self) -> Optional[str]:
        """Extract website from detail view"""
        try:
            # Look for website link (usually has 'website' text or globe icon)
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a[rel='noopener noreferrer'][target='_blank']")
            for elem in elements:
                href = elem.get_attribute('href')
                text = elem.text.lower()
                # Skip known social platforms
                if any(platform in href for platform in ['t.me', 'twitter.com', 'x.com', 'discord', 'telegram']):
                    continue
                if 'website' in text or not text:
                    return href
        except Exception as e:
            logger.debug(f"Error extracting website: {e}")
        return None
    
    def _close_detail_view(self):
        """Close the token detail view"""
        try:
            # Try ESC key
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            # Try clicking close button
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close'], .close-button, [data-testid='close']")
                close_btn.click()
                time.sleep(0.5)
            except:
                pass
    
    def _go_to_next_page(self) -> bool:
        """Navigate to next page if available (handles infinite scroll)"""
        try:
            # DEXScreener likely uses infinite scroll
            # Keep scrolling until no more content loads
            
            logger.info("Attempting to load more tokens (infinite scroll)...")
            
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while scroll_attempts < max_scroll_attempts:
                # Get current height
                current_height = self.driver.execute_script("return document.body.scrollHeight")
                current_token_count = len(self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, tbody tr"))
                
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check if new content loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                new_token_count = len(self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, tbody tr"))
                
                if new_height > current_height or new_token_count > current_token_count:
                    logger.info(f"  Loaded more content (tokens: {current_token_count} → {new_token_count})")
                    return True  # More content loaded
                
                scroll_attempts += 1
                
                # If no change after 3 attempts, probably reached the end
                if scroll_attempts >= 3:
                    logger.info("  No new content after multiple scroll attempts")
                    break
            
            # Try traditional pagination buttons as fallback
            next_selectors = [
                "button[aria-label='Next page']",
                "a[aria-label='Next page']",
                "button:contains('Next')",
                ".pagination button:last-child",
                "[data-testid='next-page']"
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn.is_enabled():
                        next_btn.click()
                        time.sleep(2)
                        logger.info("  Clicked pagination button")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False


def scrape_dexscreener_url(url: str, headless: bool = True) -> List[Dict]:
    """
    Convenience function to scrape a DEXScreener URL
    
    Args:
        url: DEXScreener filtered URL
        headless: Run browser in headless mode
        
    Returns:
        List of token dictionaries
    """
    scraper = DEXScreenerScraper(headless=headless)
    return scraper.scrape_url(url)


if __name__ == "__main__":
    # Test scraper
    test_url = "https://dexscreener.com/solana?filters=..."  # Replace with actual URL
    tokens = scrape_dexscreener_url(test_url)
    
    print(f"\n✅ Scraped {len(tokens)} tokens")
    print("\nSample tokens:")
    for token in tokens[:5]:
        print(f"  - {token['name']} ({token['symbol']})")
        print(f"    Address: {token['address']}")
        print(f"    Telegram: {token['telegram']}")
        print(f"    Twitter: {token['twitter']}")
        print(f"    Website: {token['website']}")
        print()
