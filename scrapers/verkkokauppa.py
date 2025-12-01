"""API-based scraper for Verkkokauppa.com Finnish electronics store."""
import logging
import re
from typing import Optional, AsyncGenerator

import httpx

from .base import BaseScraper, ScrapedProduct, SitemapParser
from config import config

logger = logging.getLogger(__name__)


class VerkkokauppaScraper(BaseScraper):
    """API-based scraper for Verkkokauppa.com Finnish electronics store.
    
    Uses the public web API for efficient data fetching.
    API endpoint: https://web-api.service.verkkokauppa.com/products/{id}
    """
    
    STORE_NAME = "Verkkokauppa.com"
    BASE_URL = "https://www.verkkokauppa.com"
    SITEMAP_URL = "https://cdn-a.verkkokauppa.com/gsitemaps1/sitemap.xml"  # CDN URL to avoid redirect
    API_URL = "https://web-api.service.verkkokauppa.com/products"
    
    def __init__(self):
        super().__init__()
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Initialize HTTP client."""
        self.http_client = httpx.AsyncClient(
            headers={
                "User-Agent": config.USER_AGENTS[0],
                "Accept": "application/json",
            },
            timeout=30.0
        )
        logger.info(f"HTTP client started for {self.STORE_NAME}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
        logger.info(f"HTTP client closed for {self.STORE_NAME}")
    
    async def get_product_urls(self) -> AsyncGenerator[str, None]:
        """Get product URLs from Verkkokauppa sitemap."""
        logger.info(f"Fetching product URLs from {self.SITEMAP_URL}")
        
        urls = await SitemapParser.get_urls_from_sitemap(
            self.SITEMAP_URL,
            url_filter='/fi/product/'
        )
        
        logger.info(f"Found {len(urls)} product URLs from sitemap")
        
        for url in urls:
            yield url
    
    async def get_product_ids_from_sitemap(self) -> AsyncGenerator[str, None]:
        """Extract product IDs from sitemap URLs."""
        async for url in self.get_product_urls():
            product_id = self.extract_product_id(url)
            if product_id:
                yield product_id
    
    async def fetch_products_batch(self, product_ids: list[str]) -> list[ScrapedProduct]:
        """Fetch multiple products in a single API call (more efficient)."""
        if not product_ids:
            return []
        
        try:
            # API supports comma-separated IDs
            ids_str = ",".join(product_ids)
            url = f"{self.API_URL}/{ids_str}"
            response = await self.http_client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"Batch API returned {response.status_code}")
                return []
            
            data = response.json()
            products = []
            
            if isinstance(data, list):
                for product_data in data:
                    pid = str(product_data.get('pid', ''))
                    if pid:
                        product = self._parse_api_response(product_data, pid)
                        if product:
                            products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            return []
    
    def _parse_api_response(self, data: dict, product_id: str) -> Optional[ScrapedProduct]:
        """Parse API response into ScrapedProduct."""
        try:
            # Get name (prefer Finnish)
            name_data = data.get('name', {})
            name = name_data.get('fi') or name_data.get('en') or str(name_data)
            
            if not name:
                return None
            
            # Get price
            price_data = data.get('price', {})
            current_price = price_data.get('current')
            original_price = price_data.get('original')
            
            if not current_price:
                return None
            
            # Get URL
            href_data = data.get('href', {})
            product_url = href_data.get('fi', '')
            if product_url and not product_url.startswith('http'):
                product_url = f"{self.BASE_URL}{product_url}"
            
            # Get brand
            brand_data = data.get('brand', {})
            brand = brand_data.get('name') if isinstance(brand_data, dict) else None
            
            # Get category
            category = None
            sales_cat = data.get('sales_category', {})
            if sales_cat:
                path = sales_cat.get('path', [])
                if path:
                    category = path[0].get('name') if path else None
            
            # Get image
            images = data.get('images', [])
            image_url = None
            if images and len(images) > 0:
                image_url = images[0].get('300') or images[0].get('500')
            
            # Check availability
            is_available = data.get('active', True) and data.get('visible', 1) == 1
            
            return ScrapedProduct(
                external_id=product_id,
                name=name,
                url=product_url or f"{self.BASE_URL}/fi/product/{product_id}",
                price=float(current_price),
                original_price=float(original_price) if original_price and original_price != current_price else None,
                brand=brand,
                category=category,
                image_url=image_url,
                is_available=is_available
            )
            
        except Exception as e:
            logger.error(f"Error parsing product {product_id}: {e}")
            return None
    
    async def scrape_all_products(self) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products using the API (batch mode for efficiency)."""
        batch_size = 50  # API supports multiple IDs
        batch = []
        
        async for product_id in self.get_product_ids_from_sitemap():
            batch.append(product_id)
            
            if len(batch) >= batch_size:
                products = await self.fetch_products_batch(batch)
                for product in products:
                    yield product
                    logger.info(f"Scraped: {product.name[:50]}... - {product.price}€")
                
                batch = []
        
        # Process remaining batch
        if batch:
            products = await self.fetch_products_batch(batch)
            for product in products:
                yield product
                logger.info(f"Scraped: {product.name[:50]}... - {product.price}€")
    
    @staticmethod
    def extract_product_id(url: str) -> Optional[str]:
        """Extract product ID from Verkkokauppa URL.
        
        URL format: /fi/product/{product_id}/{product-slug}
        Example: /fi/product/987838/MSI-MAG-A850GL-PCIE5-II-ATX-virtalahde-850-W
        """
        match = re.search(r'/fi/product/(\d+)/', url)
        return match.group(1) if match else None
