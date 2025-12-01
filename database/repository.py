"""Database repository for CRUD operations."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .models import Store, Product, PriceHistory, Category


class StoreRepository:
    """Repository for Store operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_active(self) -> list[Store]:
        """Get all active stores."""
        return self.db.query(Store).filter(Store.is_active == True).all()
    
    def get_by_name(self, name: str) -> Optional[Store]:
        """Get store by name."""
        return self.db.query(Store).filter(Store.name == name).first()
    
    def get_by_id(self, store_id: int) -> Optional[Store]:
        """Get store by ID."""
        return self.db.query(Store).filter(Store.id == store_id).first()
    
    def create(self, name: str, base_url: str, scraper_class: str, 
               sitemap_url: Optional[str] = None) -> Store:
        """Create a new store."""
        store = Store(
            name=name,
            base_url=base_url,
            scraper_class=scraper_class,
            sitemap_url=sitemap_url
        )
        self.db.add(store)
        self.db.commit()
        self.db.refresh(store)
        return store


class ProductRepository:
    """Repository for Product operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def get_by_external_id(self, store_id: int, external_id: str) -> Optional[Product]:
        """Get product by store and external ID."""
        return self.db.query(Product).filter(
            Product.store_id == store_id,
            Product.external_id == external_id
        ).first()
    
    def get_all(self, store_id: Optional[int] = None, 
                limit: int = 50, offset: int = 0) -> list[Product]:
        """Get all products with optional store filter."""
        q = self.db.query(Product)
        if store_id:
            q = q.filter(Product.store_id == store_id)
        return q.order_by(Product.name).offset(offset).limit(limit).all()
    
    def count_all(self, store_id: Optional[int] = None) -> int:
        """Count all products with optional store filter."""
        q = self.db.query(func.count(Product.id))
        if store_id:
            q = q.filter(Product.store_id == store_id)
        return q.scalar() or 0
    
    def search(self, query: str, store_id: Optional[int] = None, 
               limit: int = 50, offset: int = 0) -> list[Product]:
        """Search products by name."""
        q = self.db.query(Product).filter(
            Product.name.ilike(f"%{query}%")
        )
        if store_id:
            q = q.filter(Product.store_id == store_id)
        return q.order_by(Product.name).offset(offset).limit(limit).all()
    
    def count_search(self, query: str, store_id: Optional[int] = None) -> int:
        """Count search results."""
        q = self.db.query(func.count(Product.id)).filter(
            Product.name.ilike(f"%{query}%")
        )
        if store_id:
            q = q.filter(Product.store_id == store_id)
        return q.scalar() or 0
    
    def create_or_update(self, store_id: int, external_id: str, name: str, 
                         url: str, **kwargs) -> Product:
        """Create a new product or update existing one."""
        product = self.get_by_external_id(store_id, external_id)
        
        if product:
            # Update existing product
            product.name = name
            product.url = url
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            product.updated_at = datetime.utcnow()
        else:
            # Create new product
            product = Product(
                store_id=store_id,
                external_id=external_id,
                name=name,
                url=url,
                **kwargs
            )
            self.db.add(product)
        
        self.db.commit()
        self.db.refresh(product)
        return product


class PriceHistoryRepository:
    """Repository for PriceHistory operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_product(self, product_id: int, limit: Optional[int] = None) -> list[PriceHistory]:
        """Get price history for a product, ordered by date descending."""
        q = self.db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id
        ).order_by(PriceHistory.scraped_at.desc())
        
        if limit:
            q = q.limit(limit)
        return q.all()
    
    def get_latest(self, product_id: int) -> Optional[PriceHistory]:
        """Get the latest price for a product."""
        return self.db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id
        ).order_by(PriceHistory.scraped_at.desc()).first()
    
    def add_price(self, product_id: int, price: float, 
                  original_price: Optional[float] = None,
                  currency: str = "EUR") -> PriceHistory:
        """Add a new price entry for a product."""
        price_entry = PriceHistory(
            product_id=product_id,
            price=price,
            original_price=original_price,
            currency=currency
        )
        self.db.add(price_entry)
        self.db.commit()
        self.db.refresh(price_entry)
        return price_entry


class CategoryRepository:
    """Repository for Category operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_store(self, store_id: int) -> list[Category]:
        """Get all categories for a store."""
        return self.db.query(Category).filter(
            Category.store_id == store_id
        ).all()
    
    def get_or_create(self, store_id: int, name: str, 
                      slug: Optional[str] = None,
                      parent_id: Optional[int] = None) -> Category:
        """Get existing category or create new one."""
        category = self.db.query(Category).filter(
            Category.store_id == store_id,
            Category.name == name
        ).first()
        
        if not category:
            category = Category(
                store_id=store_id,
                name=name,
                slug=slug,
                parent_id=parent_id
            )
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
        
        return category
