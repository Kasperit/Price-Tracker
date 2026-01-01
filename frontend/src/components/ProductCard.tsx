import { Link } from 'react-router-dom';
import { ProductListItem } from '../api';

interface ProductCardProps {
  product: ProductListItem;
}

function ProductCard({ product }: ProductCardProps) {
  const formatPrice = (price: number | null) => {
    if (price === null) return 'N/A';
    return new Intl.NumberFormat('fi-FI', {
      style: 'currency',
      currency: 'EUR',
    }).format(price);
  };

  // Save scroll position before navigating
  const handleClick = () => {
    sessionStorage.setItem('homeScrollY', window.scrollY.toString());
  };

  return (
    <div className="product-card">
      <Link 
        to={`/product/${product.id}`} 
        className="product-card-link"
        onClick={handleClick}
      >
        <div className="product-image-container">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="product-image"
              loading="lazy"
            />
          ) : (
            <span className="product-image-placeholder">No image</span>
          )}
        </div>
        <div className="product-info">
          <h3 className="product-name">{product.name}</h3>
          {product.brand && <p className="product-brand">{product.brand}</p>}
          <p className="product-price">{formatPrice(product.latest_price)}</p>
          {product.store_name && (
            <p className="product-store">{product.store_name}</p>
          )}
        </div>
      </Link>
    </div>
  );
}

export default ProductCard;
