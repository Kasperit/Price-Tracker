"""API routes for products and stores."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_db
from database.models import Product, Store, PriceHistory
from database.repository import ProductRepository, StoreRepository, PriceHistoryRepository
from .schemas import (
    ProductListResponse, 
    ProductDetailResponse, 
    ProductSearchResponse,
    StoreResponse,
    PriceHistoryResponse,
    PriceStatistics
)

router = APIRouter()


# Dependency to get repositories
def get_product_repo(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_store_repo(db: Session = Depends(get_db)) -> StoreRepository:
    return StoreRepository(db)


def get_price_repo(db: Session = Depends(get_db)) -> PriceHistoryRepository:
    return PriceHistoryRepository(db)


# Store endpoints
@router.get("/stores", response_model=list[StoreResponse], tags=["stores"])
async def list_stores(db: Session = Depends(get_db)):
    """Get all active stores."""
    repo = StoreRepository(db)
    stores = repo.get_all_active()
    return stores


@router.get("/stores/{store_id}", response_model=StoreResponse, tags=["stores"])
async def get_store(store_id: int, db: Session = Depends(get_db)):
    """Get a specific store by ID."""
    repo = StoreRepository(db)
    store = repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


# Product endpoints
@router.get("/products", response_model=ProductSearchResponse, tags=["products"])
async def list_products(
    store_id: Optional[int] = Query(None, description="Filter by store ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """List all products with optional store filter."""
    repo = ProductRepository(db)
    offset = (page - 1) * page_size
    
    products = repo.get_all(store_id=store_id, limit=page_size, offset=offset)
    total = repo.count_all(store_id=store_id)
    
    # Add latest price and store name to each product
    items = []
    for product in products:
        price_repo = PriceHistoryRepository(db)
        latest = price_repo.get_latest(product.id)
        
        items.append(ProductListResponse(
            id=product.id,
            name=product.name,
            url=product.url,
            brand=product.brand,
            store_id=product.store_id,
            external_id=product.external_id,
            image_url=product.image_url,
            is_available=product.is_available,
            latest_price=latest.price if latest else None,
            store_name=product.store.name if product.store else None
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return ProductSearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/products/search", response_model=ProductSearchResponse, tags=["products"])
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    store_id: Optional[int] = Query(None, description="Filter by store ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Search products by name."""
    repo = ProductRepository(db)
    offset = (page - 1) * page_size
    
    products = repo.search(q, store_id=store_id, limit=page_size, offset=offset)
    total = repo.count_search(q, store_id=store_id)
    
    # Add latest price and store name to each product
    items = []
    for product in products:
        price_repo = PriceHistoryRepository(db)
        latest = price_repo.get_latest(product.id)
        
        items.append(ProductListResponse(
            id=product.id,
            name=product.name,
            url=product.url,
            brand=product.brand,
            store_id=product.store_id,
            external_id=product.external_id,
            image_url=product.image_url,
            is_available=product.is_available,
            latest_price=latest.price if latest else None,
            store_name=product.store.name if product.store else None
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return ProductSearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse, tags=["products"])
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product details with full price history."""
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get price history with discount percentages
    price_history = []
    for ph in product.price_history:
        price_history.append(PriceHistoryResponse(
            id=ph.id,
            price=ph.price,
            original_price=ph.original_price,
            currency=ph.currency,
            scraped_at=ph.scraped_at,
            discount_percentage=ph.discount_percentage
        ))
    
    # Sort by date descending
    price_history.sort(key=lambda x: x.scraped_at, reverse=True)
    
    return ProductDetailResponse(
        id=product.id,
        name=product.name,
        url=product.url,
        brand=product.brand,
        store_id=product.store_id,
        external_id=product.external_id,
        image_url=product.image_url,
        description=product.description,
        is_available=product.is_available,
        created_at=product.created_at,
        updated_at=product.updated_at,
        store=StoreResponse(
            id=product.store.id,
            name=product.store.name,
            base_url=product.store.base_url,
            is_active=product.store.is_active,
            created_at=product.store.created_at
        ),
        price_history=price_history
    )


@router.get("/products/{product_id}/history", response_model=list[PriceHistoryResponse], tags=["products"])
async def get_product_price_history(
    product_id: int, 
    limit: Optional[int] = Query(None, ge=1, le=365, description="Limit number of records"),
    db: Session = Depends(get_db)
):
    """Get price history for a product."""
    product_repo = ProductRepository(db)
    product = product_repo.get_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price_repo = PriceHistoryRepository(db)
    history = price_repo.get_by_product(product_id, limit=limit)
    
    return [
        PriceHistoryResponse(
            id=ph.id,
            price=ph.price,
            original_price=ph.original_price,
            currency=ph.currency,
            scraped_at=ph.scraped_at,
            discount_percentage=ph.discount_percentage
        )
        for ph in history
    ]


@router.get("/products/{product_id}/statistics", response_model=PriceStatistics, tags=["products"])
async def get_product_statistics(product_id: int, db: Session = Depends(get_db)):
    """Get price statistics for a product."""
    product_repo = ProductRepository(db)
    product = product_repo.get_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price_repo = PriceHistoryRepository(db)
    history = price_repo.get_by_product(product_id)
    
    if not history:
        return PriceStatistics()
    
    prices = [h.price for h in history]
    current = prices[0]  # Most recent (already sorted desc)
    first = prices[-1]  # Oldest
    
    change = current - first
    change_percent = (change / first * 100) if first > 0 else None
    
    return PriceStatistics(
        current_price=current,
        min_price=min(prices),
        max_price=max(prices),
        avg_price=round(sum(prices) / len(prices), 2),
        price_change=round(change, 2),
        price_change_percent=round(change_percent, 1) if change_percent else None
    )
