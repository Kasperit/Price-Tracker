"""Scraping job runner and scheduler."""
import asyncio
import logging
from datetime import datetime
from typing import Type

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.session import SessionLocal, init_db
from database.repository import StoreRepository, ProductRepository, PriceHistoryRepository
from scrapers.base import BaseScraper
from scrapers.verkkokauppa import VerkkokauppaScraper
from scrapers.gigantti import GiganttiAPIScraper
from scrapers.power import PowerAPIScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Registry of available scrapers
SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    'VerkkokauppaScraper': VerkkokauppaScraper,
    'GiganttiScraper': GiganttiAPIScraper,
    'GiganttiAPIScraper': GiganttiAPIScraper,
    'PowerScraper': PowerAPIScraper,
    'PowerAPIScraper': PowerAPIScraper,
}


def initialize_stores():
    """Initialize stores in the database if they don't exist."""
    db = SessionLocal()
    try:
        store_repo = StoreRepository(db)
        
        # Add Verkkokauppa
        if not store_repo.get_by_name("Verkkokauppa.com"):
            store_repo.create(
                name="Verkkokauppa.com",
                base_url="https://www.verkkokauppa.com",
                scraper_class="VerkkokauppaScraper",
                sitemap_url="https://www.verkkokauppa.com/gsitemaps1/sitemap.xml"
            )
            logger.info("Added Verkkokauppa.com store")
        
        # Add Gigantti
        if not store_repo.get_by_name("Gigantti"):
            store_repo.create(
                name="Gigantti",
                base_url="https://www.gigantti.fi",
                scraper_class="GiganttiScraper",
                sitemap_url="https://www.gigantti.fi/sitemaps/OCFIGIG.pdp.index.sitemap.xml"
            )
            logger.info("Added Gigantti store")
        
        # Add Power
        if not store_repo.get_by_name("Power"):
            store_repo.create(
                name="Power",
                base_url="https://www.power.fi",
                scraper_class="PowerScraper",
                sitemap_url=None  # Power doesn't have a public sitemap
            )
            logger.info("Added Power store")
            
    finally:
        db.close()


async def run_scraper_for_store(store_id: int, scraper_class: str, limit: int = None):
    """Run scraper for a specific store and save results to database."""
    logger.info(f"Starting scraping for store ID {store_id} with {scraper_class}" + (f" (limit: {limit})" if limit else ""))
    
    scraper_cls = SCRAPER_REGISTRY.get(scraper_class)
    if not scraper_cls:
        logger.error(f"Unknown scraper class: {scraper_class}")
        return
    
    db = SessionLocal()
    product_repo = ProductRepository(db)
    price_repo = PriceHistoryRepository(db)
    
    products_scraped = 0
    errors = 0
    
    try:
        async with scraper_cls() as scraper:
            async for product_data in scraper.scrape_all_products():
                # Check limit
                if limit and products_scraped >= limit:
                    logger.info(f"Reached limit of {limit} products")
                    break
                try:
                    # Create or update product
                    product = product_repo.create_or_update(
                        store_id=store_id,
                        external_id=product_data.external_id,
                        name=product_data.name,
                        url=product_data.url,
                        brand=product_data.brand,
                        image_url=product_data.image_url,
                        is_available=product_data.is_available
                    )
                    
                    # Add price history entry
                    price_repo.add_price(
                        product_id=product.id,
                        price=product_data.price,
                        original_price=product_data.original_price
                    )
                    
                    products_scraped += 1
                    
                    if products_scraped % 100 == 0:
                        logger.info(f"Scraped {products_scraped} products so far...")
                        
                except Exception as e:
                    logger.error(f"Error saving product {product_data.name}: {e}")
                    errors += 1
                    continue
                    
    except Exception as e:
        logger.error(f"Scraper error: {e}")
    finally:
        db.close()
    
    logger.info(f"Completed scraping for store ID {store_id}: {products_scraped} products, {errors} errors")


async def run_all_scrapers(limit: int = None):
    """Run scrapers for all active stores."""
    logger.info("=" * 50)
    logger.info(f"Starting monthly scraping job at {datetime.now()}")
    logger.info("=" * 50)
    
    db = SessionLocal()
    try:
        store_repo = StoreRepository(db)
        stores = store_repo.get_all_active()
        
        for store in stores:
            logger.info(f"Processing store: {store.name}")
            await run_scraper_for_store(store.id, store.scraper_class, limit=limit)
            
    finally:
        db.close()
    
    logger.info("=" * 50)
    logger.info(f"Monthly scraping job completed at {datetime.now()}")
    logger.info("=" * 50)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the scheduler."""
    scheduler = AsyncIOScheduler()
    
    # Run every 2 weeks (1st and 15th of each month) at 3:00 AM
    scheduler.add_job(
        run_all_scrapers,
        CronTrigger(day='1,15', hour=3, minute=0),
        id='biweekly_scrape',
        name='Bi-weekly Price Scraping',
        replace_existing=True
    )
    
    logger.info("Scheduler configured: Bi-weekly scraping on days 1 and 15 at 03:00")
    return scheduler


async def main():
    """Main entry point for the scheduler."""
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize stores
    initialize_stores()
    
    # Create and start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        # Keep the scheduler running
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
