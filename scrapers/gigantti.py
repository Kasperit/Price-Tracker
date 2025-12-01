"""Gigantti.fi API-based scraper implementation."""
import logging
import re
from typing import Optional, AsyncGenerator

import httpx

from .base import BaseScraper, ScrapedProduct, SitemapParser

logger = logging.getLogger(__name__)


class GiganttiAPIScraper(BaseScraper):
    """API-based scraper for Gigantti.fi Finnish electronics store.
    
    Uses Gigantti's internal APIs:
    - Product card: https://www.gigantti.fi/api/product/{id}/card
    - Price data: https://www.gigantti.fi/api/price/{id}
    """
    
    STORE_NAME = "Gigantti"
    BASE_URL = "https://www.gigantti.fi"
    SITEMAP_URL = "https://www.gigantti.fi/sitemaps/OCFIGIG.pdp.index.sitemap.xml"
    
    # API endpoints
    API_PRODUCT_CARD = "https://www.gigantti.fi/api/product/{product_id}/card"
    API_PRICE = "https://www.gigantti.fi/api/price/{product_id}"
    
    # HTTP headers to mimic browser requests
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'fi-FI,fi;q=0.9,en;q=0.8',
        'Referer': 'https://www.gigantti.fi/',
    }
    
    def __init__(self):
        """Initialize the API scraper with HTTP client."""
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.HEADERS,
                timeout=30.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_product_urls(self) -> AsyncGenerator[str, None]:
        """Get product URLs from Gigantti sitemap."""
        logger.info(f"Fetching product URLs from {self.SITEMAP_URL}")
        
        urls = await SitemapParser.get_urls_from_sitemap(
            self.SITEMAP_URL,
            url_filter='/product/'
        )
        
        logger.info(f"Found {len(urls)} product URLs from sitemap")
        
        for url in urls:
            yield url
    
    async def _fetch_product_by_id(self, product_id: str) -> Optional[ScrapedProduct]:
        """Fetch product data using Gigantti API endpoints.
        
        Args:
            product_id: The product ID to fetch
            
        Returns:
            ScrapedProduct if successful, None otherwise
        """
        try:
            client = await self._get_client()
            
            # Fetch product card data
            card_url = self.API_PRODUCT_CARD.format(product_id=product_id)
            card_response = await client.get(card_url)
            
            if card_response.status_code != 200:
                logger.warning(f"Failed to fetch product card for {product_id}: {card_response.status_code}")
                return None
            
            card_data = card_response.json()
            
            # The API response wraps data in a 'data' key
            product_data = card_data.get('data', card_data)
            
            # Fetch price data
            price_url = self.API_PRICE.format(product_id=product_id)
            price_response = await client.get(price_url)
            
            price_data = None
            if price_response.status_code == 200:
                price_data = price_response.json()
            
            # Extract product information from card data
            name = product_data.get('name') or product_data.get('title')
            if not name:
                logger.warning(f"No name found for product {product_id}")
                return None
            
            # Get price from product data - price.current is an array [priceWithVAT, priceWithoutVAT]
            price = None
            original_price = None
            
            product_price = product_data.get('price')
            if isinstance(product_price, dict):
                current = product_price.get('current')
                original = product_price.get('original')
                
                # current is an array [priceWithVAT, priceWithoutVAT]
                if isinstance(current, list) and len(current) > 0:
                    price = float(current[0])  # First element is price with VAT
                elif isinstance(current, (int, float)):
                    price = float(current)
                
                if isinstance(original, list) and len(original) > 0:
                    original_price = float(original[0])
                elif isinstance(original, (int, float)):
                    original_price = float(original)
            
            # Fallback to price API data if needed
            if not price and price_data:
                price_info = price_data.get('data', price_data).get('price', price_data.get('data', price_data))
                if isinstance(price_info, dict):
                    current = price_info.get('current')
                    if isinstance(current, list) and len(current) > 0:
                        price = float(current[0])
                    elif isinstance(current, (int, float)):
                        price = float(current)
            
            if not price:
                logger.warning(f"No price found for product {product_id}")
                return None
            
            # Ensure price is float
            if isinstance(price, str):
                price = self.parse_price(price)
            else:
                price = float(price)
            
            if original_price:
                if isinstance(original_price, str):
                    original_price = self.parse_price(original_price)
                else:
                    original_price = float(original_price)
            
            # Get brand
            brand = product_data.get('brand') or product_data.get('manufacturer')
            if isinstance(brand, dict):
                brand = brand.get('name')
            
            # Get category - from taxonomy array
            category = None
            taxonomy = product_data.get('taxonomy')
            if taxonomy and isinstance(taxonomy, list) and len(taxonomy) > 0:
                category = taxonomy[0]  # First category from taxonomy
            
            # Get image URL
            image_url = product_data.get('imageUrl')
            if not image_url:
                images = product_data.get('images') or product_data.get('image')
                if images:
                    if isinstance(images, list) and len(images) > 0:
                        first_img = images[0]
                        image_url = first_img.get('url') if isinstance(first_img, dict) else str(first_img)
                    elif isinstance(images, dict):
                        image_url = images.get('url') or images.get('src')
                    elif isinstance(images, str):
                        image_url = images
            
            # Build product URL
            url = product_data.get('href') or product_data.get('url') or product_data.get('productUrl')
            if not url:
                url = f"{self.BASE_URL}/product/{product_id}"
            elif not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"
            
            # Check availability from sellability object
            is_available = True
            sellability = product_data.get('sellability')
            if sellability and isinstance(sellability, dict):
                is_available = sellability.get('isBuyableOnline', False) or sellability.get('isBuyableInStore', False)
            
            return ScrapedProduct(
                external_id=product_id,
                name=name,
                url=url,
                price=price,
                original_price=original_price,
                brand=brand,
                category=category,
                image_url=image_url,
                is_available=is_available
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching product {product_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    async def scrape_all_products(self) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products from the sitemap using API."""
        logger.info("Starting API-based scrape of all Gigantti products")
        
        count = 0
        errors = 0
        
        async for url in self.get_product_urls():
            product_id = self.extract_product_id(url)
            if not product_id:
                continue
            
            product = await self._fetch_product_by_id(product_id)
            if product:
                count += 1
                yield product
                
                if count % 100 == 0:
                    logger.info(f"Scraped {count} products...")
            else:
                errors += 1
        
        logger.info(f"Completed scraping. Success: {count}, Errors: {errors}")
        
        await self.close()
    
    @staticmethod
    def extract_product_id(url: str) -> Optional[str]:
        """Extract product ID from Gigantti URL.
        
        URL format: /product/{category-path}/{product-slug}/{product_id}
        Example: /product/puhelimet-tabletit-ja-alykellot/puhelimet/samsung-galaxy/820912
        """
        match = re.search(r'/(\d+)(?:\?|$)', url)
        return match.group(1) if match else None


# Backwards compatibility alias
GiganttiScraper = GiganttiAPIScraper
