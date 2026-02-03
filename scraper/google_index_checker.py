"""
Google Index Checker
Checks if a website is indexed on Google using site:domain.com search
"""

import requests
import logging
import time
import re
import random
from typing import Optional, Tuple
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GoogleIndexChecker:
    """Check if websites are indexed on Google"""
    
    # User agents to rotate
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(self, delay_seconds: float = 5.0):
        """
        Initialize the checker
        
        Args:
            delay_seconds: Delay between checks to avoid rate limiting
        """
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.last_check_time = 0
    
    def _get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        if not url:
            return None
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Remove www. prefix for consistency
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain if domain else None
        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return None
    
    def _wait_for_rate_limit(self):
        """Wait to respect rate limits"""
        elapsed = time.time() - self.last_check_time
        if elapsed < self.delay_seconds:
            sleep_time = self.delay_seconds - elapsed + random.uniform(0.5, 1.5)
            time.sleep(sleep_time)
    
    def check_indexed(self, website_url: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a website is indexed on Google
        
        Args:
            website_url: The website URL to check
            
        Returns:
            Tuple of (is_indexed: bool, result_count: int or None)
        """
        domain = self._get_domain(website_url)
        if not domain:
            logger.warning(f"Could not extract domain from: {website_url}")
            return False, None
        
        self._wait_for_rate_limit()
        
        try:
            # Use Google search with site: operator
            query = f"site:{domain}"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"
            
            headers = {
                "User-Agent": random.choice(self.USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            response = self.session.get(
                search_url,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            
            self.last_check_time = time.time()
            
            if response.status_code != 200:
                logger.warning(f"Google returned status {response.status_code} for {domain}")
                return None, None  # Unknown status
            
            html = response.text
            
            # Check for CAPTCHA
            if "unusual traffic" in html.lower() or "captcha" in html.lower():
                logger.error("Google CAPTCHA detected! Increase delay or use proxy.")
                return None, None
            
            # Parse results
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check for "No results found" indicators
            no_results_patterns = [
                "did not match any documents",
                "No results found",
                "Your search -",
            ]
            
            for pattern in no_results_patterns:
                if pattern.lower() in html.lower():
                    logger.info(f"✗ {domain} is NOT indexed (no results)")
                    return False, 0
            
            # Look for result stats (e.g., "About 1,234 results")
            result_stats = soup.find(id="result-stats")
            result_count = None
            
            if result_stats:
                stats_text = result_stats.get_text()
                # Extract number from "About 1,234 results"
                match = re.search(r'[\d,]+', stats_text)
                if match:
                    result_count = int(match.group().replace(',', ''))
            
            # Also check for actual search results
            search_results = soup.select("div.g") or soup.select("div[data-sokoban-container]")
            
            if result_count and result_count > 0:
                logger.info(f"✓ {domain} IS indexed ({result_count} results)")
                return True, result_count
            elif len(search_results) > 0:
                # Results exist but couldn't parse count
                logger.info(f"✓ {domain} IS indexed (found results)")
                return True, len(search_results)
            else:
                logger.info(f"✗ {domain} is NOT indexed")
                return False, 0
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout checking {domain}")
            return None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error checking {domain}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Error checking {domain}: {e}")
            return None, None
    
    def check_batch(self, urls: list) -> dict:
        """
        Check multiple URLs for indexing
        
        Args:
            urls: List of website URLs
            
        Returns:
            Dict mapping URL -> (is_indexed, result_count)
        """
        results = {}
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Checking: {url}")
            is_indexed, count = self.check_indexed(url)
            results[url] = {
                'is_indexed': is_indexed,
                'result_count': count
            }
        
        # Summary
        indexed = sum(1 for r in results.values() if r['is_indexed'])
        not_indexed = sum(1 for r in results.values() if r['is_indexed'] is False)
        unknown = sum(1 for r in results.values() if r['is_indexed'] is None)
        
        logger.info(f"\n📊 Index Check Summary:")
        logger.info(f"  ✓ Indexed: {indexed}")
        logger.info(f"  ✗ Not indexed: {not_indexed}")
        logger.info(f"  ? Unknown: {unknown}")
        
        return results


def check_google_index(url: str, delay: float = 5.0) -> Tuple[bool, Optional[int]]:
    """
    Convenience function to check if a single URL is indexed
    
    Args:
        url: Website URL to check
        delay: Delay before checking (rate limiting)
        
    Returns:
        Tuple of (is_indexed, result_count)
    """
    checker = GoogleIndexChecker(delay_seconds=delay)
    return checker.check_indexed(url)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python google_index_checker.py <url> [url2] [url3] ...")
        print("Example: python google_index_checker.py https://example.com")
        sys.exit(1)
    
    urls = sys.argv[1:]
    
    checker = GoogleIndexChecker(delay_seconds=3.0)
    
    for url in urls:
        is_indexed, count = checker.check_indexed(url)
        status = "✓ INDEXED" if is_indexed else "✗ NOT INDEXED" if is_indexed is False else "? UNKNOWN"
        print(f"{url}: {status} ({count} results)")
