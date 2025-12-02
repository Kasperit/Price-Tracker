"""Script to clean up products without price history."""
import logging
from database.session import SessionLocal, init_db
from database.repository import ProductRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup():
    """Remove products without any price history entries."""
    init_db()
    db = SessionLocal()
    
    try:
        product_repo = ProductRepository(db)
        deleted_count = product_repo.delete_products_without_prices()
        logger.info(f"Deleted {deleted_count} products without price data")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
