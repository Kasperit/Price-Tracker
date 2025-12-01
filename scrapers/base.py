"""Base scraper class for all store scrapers."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncGenerator

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    """Data class for a scraped product."""
    external_id: str
    name: str
    url: str
    price: float
    original_price: Optional[float] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_available: bool = True


class BaseScraper(ABC):
    """Abstract base class for all store scrapers.
    
    To add a new store:
    1. Create a new class that inherits from BaseScraper
    2. Implement all abstract methods
    3. Register the store in the database with the scraper class name
    """
    
    # Store information - override in subclasses
    STORE_NAME: str = ""
    BASE_URL: str = ""
    SITEMAP_URL: Optional[str] = None
    
    def __init__(self):
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close any resources. Override in subclasses if needed."""
        pass
    
    @abstractmethod
    async def get_product_urls(self) -> AsyncGenerator[str, None]:
        """Get all product URLs from the store.
        
        Should use sitemap if available, otherwise crawl category pages.
        Yields URLs one at a time to allow for memory-efficient processing.
        """
        pass
    
    @abstractmethod
    async def scrape_all_products(self) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products from the store.
        
        This is the main entry point for scraping.
        """
        pass
    
    @staticmethod
    def parse_price(price_text: str) -> Optional[float]:
        """Parse price from text, handling Finnish number format.
        
        Finnish format: 1 234,56 € or 1234,56€
        """
        if not price_text:
            return None
        
        # Remove currency symbols, spaces, and normalize
        cleaned = price_text.replace('€', '').replace('\xa0', '').strip()
        # Remove thousands separator (space or .)
        cleaned = cleaned.replace(' ', '').replace('.', '')
        # Replace comma with dot for decimal
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse price: {price_text}")
            return None
    
    @staticmethod
    def extract_product_id(url: str) -> Optional[str]:
        """Extract product ID from URL. Override in subclasses if needed."""
        # Default implementation: get last numeric segment
        import re
        matches = re.findall(r'/(\d+)(?:/|$|\?)', url)
        return matches[-1] if matches else None


class SitemapParser:
    """Helper class to parse XML sitemaps."""
    
    @staticmethod
    async def get_urls_from_sitemap(sitemap_url: str, 
                                     url_filter: Optional[str] = None) -> list[str]:
        """Fetch and parse a sitemap, returning product URLs.
        
        Args:
            sitemap_url: URL of the sitemap
            url_filter: Optional string that must be in the URL (e.g., '/product/')
            
        Returns:
            List of URLs from the sitemap
        """
        urls = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(sitemap_url, timeout=30.0)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml-xml')
                
                # Check if it's a sitemap index
                sitemap_tags = soup.find_all('sitemap')
                if sitemap_tags:
                    # It's a sitemap index, recursively get URLs from each sitemap
                    for sitemap in sitemap_tags:
                        loc = sitemap.find('loc')
                        if loc:
                            child_urls = await SitemapParser.get_urls_from_sitemap(
                                loc.text.strip(), url_filter
                            )
                            urls.extend(child_urls)
                else:
                    # It's a regular sitemap with URLs
                    for url_tag in soup.find_all('url'):
                        loc = url_tag.find('loc')
                        if loc:
                            url = loc.text.strip()
                            if not url_filter or url_filter in url:
                                urls.append(url)
                
                logger.info(f"Found {len(urls)} URLs from {sitemap_url}")
                
        except Exception as e:
            logger.error(f"Error fetching sitemap {sitemap_url}: {e}")
        
        return urls
