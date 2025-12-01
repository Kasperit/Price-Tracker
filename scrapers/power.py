"""Power.fi API-based scraper implementation."""
import logging
from typing import Optional, AsyncGenerator

import httpx

from .base import BaseScraper, ScrapedProduct

logger = logging.getLogger(__name__)


class PowerAPIScraper(BaseScraper):
    """API-based scraper for Power.fi Finnish electronics store.
    
    Uses Power.fi's internal APIs:
    - Product list by category: https://www.power.fi/api/v2/productlists?cat={cat_id}&size={size}&from={offset}
    - Product details (bulk): https://www.power.fi/api/v2/products?ids={id1},{id2},...
    
    Power.fi doesn't have a public sitemap, so we enumerate products by category.
    """
    
    STORE_NAME = "Power"
    BASE_URL = "https://www.power.fi"
    
    # API endpoints
    API_PRODUCT_LIST = "https://www.power.fi/api/v2/productlists"
    API_PRODUCTS = "https://www.power.fi/api/v2/products"
    
    # Main categories with product_count as of Dec 2024
    # These are the top-level categories containing actual products
    MAIN_CATEGORIES = [
        3319,  # Puhelimet ja kamerat (Phones & Cameras)
        3313,  # Kellot ja kuntoilu (Watches & Fitness)
        3317,  # Tietotekniikka (Computers)
        3320,  # Pelaaminen (Gaming)
        3315,  # TV ja audio
        3283,  # Kodinkoneet (Appliances)
        3311,  # Keittiön pienkoneet (Kitchen appliances)
        5016,  # Smart Home
        3286,  # Koti ja piha (Home & Garden)
        3312,  # Kauneus ja terveys (Beauty & Health)
    ]
    
    # How many products to fetch per API request
    PAGE_SIZE = 100
    
    # Image CDN base URL
    IMAGE_CDN = "https://media.power-cdn.net"
    
    # HTTP headers to mimic browser requests
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'fi-FI,fi;q=0.9,en;q=0.8',
        'Referer': 'https://www.power.fi/',
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
        """Get product URLs by enumerating all categories.
        
        Power.fi doesn't have a public sitemap, so we use the product list API.
        """
        logger.info("Fetching product URLs from Power.fi categories")
        
        seen_ids = set()
        
        for category_id in self.MAIN_CATEGORIES:
            async for product_id in self._get_category_product_ids(category_id):
                if product_id not in seen_ids:
                    seen_ids.add(product_id)
                    yield f"{self.BASE_URL}/p-{product_id}/"
        
        logger.info(f"Found {len(seen_ids)} unique product URLs")
    
    async def _get_category_product_ids(self, category_id: int) -> AsyncGenerator[int, None]:
        """Get all product IDs from a category using pagination."""
        client = await self._get_client()
        offset = 0
        
        while True:
            try:
                params = {
                    'cat': category_id,
                    'size': self.PAGE_SIZE,
                    'from': offset,
                }
                
                response = await client.get(self.API_PRODUCT_LIST, params=params)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch category {category_id} page {offset}: {response.status_code}")
                    break
                
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                    break
                
                for product in products:
                    product_id = product.get('productId')
                    if product_id:
                        yield product_id
                
                # Check if we've reached the last page
                if data.get('isLastPage', True):
                    break
                
                offset += self.PAGE_SIZE
                
            except Exception as e:
                logger.error(f"Error fetching category {category_id} at offset {offset}: {e}")
                break
    
    async def _fetch_products_bulk(self, product_ids: list[int]) -> list[ScrapedProduct]:
        """Fetch multiple products in a single API call.
        
        Args:
            product_ids: List of product IDs to fetch
            
        Returns:
            List of ScrapedProduct objects
        """
        if not product_ids:
            return []
        
        try:
            client = await self._get_client()
            
            # Power.fi API accepts comma-separated IDs
            ids_param = ','.join(str(pid) for pid in product_ids)
            
            response = await client.get(f"{self.API_PRODUCTS}?ids={ids_param}")
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch products {product_ids[:3]}...: {response.status_code}")
                return []
            
            data = response.json()
            products = []
            
            # Response is a list of product objects
            product_list = data if isinstance(data, list) else [data]
            
            for product_data in product_list:
                product = self._parse_product(product_data)
                if product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products bulk: {e}")
            return []
    
    def _parse_product(self, data: dict) -> Optional[ScrapedProduct]:
        """Parse product data from API response.
        
        Args:
            data: Product data dict from API
            
        Returns:
            ScrapedProduct if valid, None otherwise
        """
        try:
            product_id = data.get('productId')
            if not product_id:
                return None
            
            name = data.get('title')
            if not name:
                logger.warning(f"No name found for product {product_id}")
                return None
            
            # Price
            price = data.get('price')
            if not price:
                logger.warning(f"No price found for product {product_id}")
                return None
            
            price = float(price)
            
            # Original price (if on sale)
            original_price = data.get('previousPrice')
            if original_price:
                original_price = float(original_price)
            
            # URL
            url = data.get('url', '')
            if url and not url.startswith('http'):
                url = f"{self.BASE_URL}{url}"
            elif not url:
                url = f"{self.BASE_URL}/p-{product_id}/"
            
            # Brand
            brand = data.get('manufacturerName')
            
            # Category
            category = data.get('categoryName')
            
            # Image URL - construct from productImage data
            image_url = None
            product_image = data.get('productImage')
            if product_image and isinstance(product_image, dict):
                base_path = product_image.get('basePath')
                variants = product_image.get('variants', [])
                
                if base_path and variants:
                    # Prefer 600x600 webp image, fall back to first available
                    preferred_variant = None
                    for variant in variants:
                        filename = variant.get('filename', '')
                        if '600x600' in filename and filename.endswith('.webp'):
                            preferred_variant = filename
                            break
                    
                    if not preferred_variant and variants:
                        preferred_variant = variants[0].get('filename')
                    
                    if preferred_variant:
                        image_url = f"{self.IMAGE_CDN}{base_path}/{preferred_variant}"
            
            # Availability - check stock count and web status
            stock_count = data.get('stockCount', 0)
            stores_stock = data.get('storesStockCount', 0)
            is_available = stock_count > 0 or stores_stock > 0
            
            return ScrapedProduct(
                external_id=str(product_id),
                name=name,
                url=url,
                price=price,
                original_price=original_price,
                brand=brand,
                category=category,
                image_url=image_url,
                is_available=is_available
            )
            
        except Exception as e:
            logger.error(f"Error parsing product data: {e}")
            return None
    
    async def scrape_all_products(self) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products from Power.fi using category enumeration.
        
        Since Power.fi's product list API already returns full product data,
        we can yield products directly without additional API calls.
        """
        logger.info("Starting API-based scrape of all Power.fi products")
        
        count = 0
        seen_ids = set()
        
        for category_id in self.MAIN_CATEGORIES:
            logger.info(f"Scraping category {category_id}...")
            
            async for product in self._scrape_category(category_id, seen_ids):
                count += 1
                yield product
                
                if count % 100 == 0:
                    logger.info(f"Scraped {count} products...")
        
        logger.info(f"Completed scraping Power.fi. Total products: {count}")
        
        await self.close()
    
    async def _scrape_category(self, category_id: int, seen_ids: set) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products from a single category.
        
        The product list API returns full product data, so we can parse directly.
        
        Args:
            category_id: Category ID to scrape
            seen_ids: Set of already seen product IDs to avoid duplicates
        """
        client = await self._get_client()
        offset = 0
        
        while True:
            try:
                params = {
                    'cat': category_id,
                    'size': self.PAGE_SIZE,
                    'from': offset,
                }
                
                response = await client.get(self.API_PRODUCT_LIST, params=params)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch category {category_id} page {offset}: {response.status_code}")
                    break
                
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                    break
                
                for product_data in products:
                    product_id = product_data.get('productId')
                    
                    if product_id and product_id not in seen_ids:
                        seen_ids.add(product_id)
                        product = self._parse_product(product_data)
                        if product:
                            yield product
                
                # Check if we've reached the last page
                if data.get('isLastPage', True):
                    break
                
                offset += self.PAGE_SIZE
                
            except Exception as e:
                logger.error(f"Error scraping category {category_id} at offset {offset}: {e}")
                break
    
    @staticmethod
    def extract_product_id(url: str) -> Optional[str]:
        """Extract product ID from Power.fi URL.
        
        URL format: /product-slug/p-{product_id}/
        Example: /tietotekniikka/tietokoneet/kannettavat-tietokoneet/lenovo-ideapad/p-4126595/
        """
        import re
        match = re.search(r'/p-(\d+)/', url)
        return match.group(1) if match else None


# Backwards compatibility alias
PowerScraper = PowerAPIScraper
