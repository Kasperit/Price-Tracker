"""Scraping job runner and scheduler."""
import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
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

# Scraping logs directory
LOGS_DIR = Path(os.getenv('DATA_DIR', '.')) / 'logs'


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


def write_scraping_report(store_stats: list[dict], total_duration: float):
    """Write scraping statistics to a log file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = LOGS_DIR / f'scraping_report_{timestamp}.log'
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"SCRAPING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("STORE STATISTICS:\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Store':<25} {'Products':>10} {'Errors':>8} {'Duration':>12}\n")
        f.write("-" * 60 + "\n")
        
        total_products = 0
        total_errors = 0
        
        for stat in store_stats:
            f.write(f"{stat['store']:<25} {stat['products']:>10} {stat['errors']:>8} {format_duration(stat['duration']):>12}\n")
            total_products += stat['products']
            total_errors += stat['errors']
        
        f.write("-" * 60 + "\n")
        f.write(f"{'TOTAL':<25} {total_products:>10} {total_errors:>8} {format_duration(total_duration):>12}\n")
        f.write("=" * 60 + "\n\n")
        
        # Detailed breakdown
        f.write("DETAILED BREAKDOWN:\n")
        f.write("-" * 60 + "\n")
        for stat in store_stats:
            f.write(f"\n{stat['store']}:\n")
            f.write(f"  - Products scraped: {stat['products']}\n")
            f.write(f"  - Errors: {stat['errors']}\n")
            f.write(f"  - Duration: {format_duration(stat['duration'])} ({stat['duration']:.2f} seconds)\n")
            if stat['products'] > 0:
                avg_time = stat['duration'] / stat['products'] * 1000  # ms per product
                f.write(f"  - Avg time per product: {avg_time:.1f}ms\n")
        
        f.write("\n" + "=" * 60 + "\n")
    
    logger.info(f"Scraping report written to: {log_file}")
    return log_file

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


async def run_scraper_for_store(store_id: int, scraper_class: str, limit: int = None) -> dict:
    """Run scraper for a specific store and save results to database.
    
    Returns:
        dict with 'products', 'errors', and 'duration' keys
    """
    logger.info(f"Starting scraping for store ID {store_id} with {scraper_class}" + (f" (limit: {limit})" if limit else ""))
    
    start_time = time.time()
    
    scraper_cls = SCRAPER_REGISTRY.get(scraper_class)
    if not scraper_cls:
        logger.error(f"Unknown scraper class: {scraper_class}")
        return {'products': 0, 'errors': 0, 'duration': 0}
    
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
    
    duration = time.time() - start_time
    logger.info(f"Completed scraping for store ID {store_id}: {products_scraped} products, {errors} errors in {format_duration(duration)}")
    
    return {'products': products_scraped, 'errors': errors, 'duration': duration}


async def run_all_scrapers(limit: int = None):
    """Run scrapers for all active stores."""
    logger.info("=" * 50)
    logger.info(f"Starting bi-weekly scraping job at {datetime.now()}")
    logger.info("=" * 50)
    
    total_start_time = time.time()
    store_stats = []
    
    db = SessionLocal()
    try:
        store_repo = StoreRepository(db)
        stores = store_repo.get_all_active()
        
        for store in stores:
            logger.info(f"Processing store: {store.name}")
            stats = await run_scraper_for_store(store.id, store.scraper_class, limit=limit)
            stats['store'] = store.name
            store_stats.append(stats)
            
    finally:
        db.close()
    
    total_duration = time.time() - total_start_time
    
    # Write scraping report
    write_scraping_report(store_stats, total_duration)
    
    # Cleanup: remove products without price data
    db = SessionLocal()
    try:
        product_repo = ProductRepository(db)
        deleted_count = product_repo.delete_products_without_prices()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} products without price data")
    finally:
        db.close()
    
    logger.info("=" * 50)
    logger.info(f"Bi-weekly scraping job completed at {datetime.now()}")
    logger.info(f"Total duration: {format_duration(total_duration)}")
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
