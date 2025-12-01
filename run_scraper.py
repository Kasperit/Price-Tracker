"""Manual scraping runner for testing or one-off runs."""
import asyncio
import argparse
import logging

from database.session import init_db
from scheduler import initialize_stores, run_all_scrapers, run_scraper_for_store
from database.session import SessionLocal
from database.repository import StoreRepository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_manual_scrape(store_name: str = None, limit: int = None):
    """Run scraping manually for testing or one-off runs.
    
    Args:
        store_name: Optional specific store to scrape. If None, scrapes all.
        limit: Optional limit on number of products to scrape (for testing)
    """
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize stores
    initialize_stores()
    
    if store_name:
        # Scrape specific store
        db = SessionLocal()
        try:
            store_repo = StoreRepository(db)
            store = store_repo.get_by_name(store_name)
            if store:
                logger.info(f"Running scraper for {store.name}")
                await run_scraper_for_store(store.id, store.scraper_class, limit=limit)
            else:
                logger.error(f"Store not found: {store_name}")
        finally:
            db.close()
    else:
        # Scrape all stores
        await run_all_scrapers(limit=limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually run price scraping")
    parser.add_argument(
        '--store', 
        type=str, 
        help='Specific store to scrape (e.g., "Verkkokauppa.com" or "Gigantti")'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of products to scrape (for testing)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_manual_scrape(args.store, args.limit))
