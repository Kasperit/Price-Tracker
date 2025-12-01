"""Database models for price tracking application."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, ForeignKey, DateTime, Text, Integer, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Store(Base):
    """Represents a web store (e.g., Verkkokauppa, Gigantti)."""
    
    __tablename__ = "stores"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    scraper_class: Mapped[str] = mapped_column(String(100), nullable=False)
    sitemap_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="store", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="store", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name='{self.name}')>"


class Category(Base):
    """Product category within a store."""
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="categories")
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side=[id], backref="children"
    )
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category"
    )
    
    __table_args__ = (
        Index("ix_categories_store_name", "store_id", "name"),
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Product(Base):
    """A product from a web store."""
    
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    store: Mapped["Store"] = relationship("Store", back_populates="products")
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="products"
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_products_store_external", "store_id", "external_id", unique=True),
        Index("ix_products_name", "name"),
    )
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name[:50]}...')>"
    
    @property
    def latest_price(self) -> Optional["PriceHistory"]:
        """Get the most recent price entry."""
        if self.price_history:
            return max(self.price_history, key=lambda p: p.scraped_at)
        return None


class PriceHistory(Base):
    """Historical price data for a product."""
    
    __tablename__ = "price_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="price_history")
    
    __table_args__ = (
        Index("ix_price_history_product_date", "product_id", "scraped_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PriceHistory(product_id={self.product_id}, price={self.price}, date={self.scraped_at})>"
    
    @property
    def discount_percentage(self) -> Optional[float]:
        """Calculate discount percentage if original price exists."""
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100, 1)
        return None
