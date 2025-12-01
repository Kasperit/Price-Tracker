"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# Store schemas
class StoreBase(BaseModel):
    name: str
    base_url: str


class StoreResponse(StoreBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Price history schemas
class PriceHistoryBase(BaseModel):
    price: float
    original_price: Optional[float] = None
    currency: str = "EUR"


class PriceHistoryResponse(PriceHistoryBase):
    id: int
    scraped_at: datetime
    discount_percentage: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# Product schemas
class ProductBase(BaseModel):
    name: str
    url: str
    brand: Optional[str] = None


class ProductListResponse(ProductBase):
    id: int
    store_id: int
    external_id: str
    image_url: Optional[str] = None
    is_available: bool
    latest_price: Optional[float] = None
    store_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(ProductBase):
    id: int
    store_id: int
    external_id: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_available: bool
    created_at: datetime
    updated_at: datetime
    store: StoreResponse
    price_history: list[PriceHistoryResponse]
    
    model_config = ConfigDict(from_attributes=True)


# Search and pagination schemas
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class ProductSearchResponse(PaginatedResponse):
    items: list[ProductListResponse]


# Statistics schemas
class PriceStatistics(BaseModel):
    current_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    avg_price: Optional[float] = None
    price_change: Optional[float] = None  # Change from first to last
    price_change_percent: Optional[float] = None
