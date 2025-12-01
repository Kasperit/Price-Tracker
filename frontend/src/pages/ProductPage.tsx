import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProduct, getProductStatistics, ProductDetail, PriceStatistics } from '../api';
import PriceChart from '../components/PriceChart';

function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [stats, setStats] = useState<PriceStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [productData, statsData] = await Promise.all([
          getProduct(parseInt(id)),
          getProductStatistics(parseInt(id)),
        ]);
        setProduct(productData);
        setStats(statsData);
      } catch (err) {
        setError('Failed to load product. Please try again.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const formatPrice = (price: number | null) => {
    if (price === null) return 'N/A';
    return new Intl.NumberFormat('fi-FI', {
      style: 'currency',
      currency: 'EUR',
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fi-FI', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (loading) {
    return <div className="loading">Loading product...</div>;
  }

  if (error || !product) {
    return (
      <div>
        <Link to="/" className="back-link">← Back to search</Link>
        <div className="error-message">{error || 'Product not found'}</div>
      </div>
    );
  }

  const latestPrice = product.price_history.length > 0 ? product.price_history[0] : null;

  return (
    <div>
      <Link to="/" className="back-link">← Back to search</Link>

      <div className="product-detail">
        <div className="product-detail-image">
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} />
          ) : (
            <span className="product-image-placeholder">No image available</span>
          )}
        </div>

        <div className="product-detail-info">
          <h1 className="product-detail-name">{product.name}</h1>
          {product.brand && (
            <p className="product-detail-brand">{product.brand}</p>
          )}
          
          <p className="product-detail-price">
            {formatPrice(latestPrice?.price ?? null)}
          </p>
          
          {latestPrice?.original_price && latestPrice.original_price > latestPrice.price && (
            <p style={{ color: '#22c55e', marginBottom: '1rem' }}>
              <span style={{ textDecoration: 'line-through', color: '#64748b' }}>
                {formatPrice(latestPrice.original_price)}
              </span>
              {' '}
              Save {latestPrice.discount_percentage}%
            </p>
          )}

          <p className="product-detail-store">
            From: <strong>{product.store.name}</strong>
          </p>

          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="product-link"
          >
            View on {product.store.name} →
          </a>

          <div style={{ marginTop: '1.5rem', fontSize: '0.875rem', color: '#64748b' }}>
            <p>First tracked: {formatDate(product.created_at)}</p>
            <p>Last updated: {formatDate(product.updated_at)}</p>
          </div>
        </div>
      </div>

      <div className="price-history-section">
        <h2 className="section-title">Price History</h2>

        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Current</div>
              <div className="stat-value">{formatPrice(stats.current_price)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Lowest</div>
              <div className="stat-value" style={{ color: '#22c55e' }}>
                {formatPrice(stats.min_price)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Highest</div>
              <div className="stat-value" style={{ color: '#ef4444' }}>
                {formatPrice(stats.max_price)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Average</div>
              <div className="stat-value">{formatPrice(stats.avg_price)}</div>
            </div>
            {stats.price_change_percent !== null && (
              <div className="stat-card">
                <div className="stat-label">Change</div>
                <div className={`stat-value ${stats.price_change_percent < 0 ? 'positive' : stats.price_change_percent > 0 ? 'negative' : ''}`}>
                  {stats.price_change_percent > 0 ? '+' : ''}{stats.price_change_percent}%
                </div>
              </div>
            )}
          </div>
        )}

        <PriceChart history={product.price_history} />

        {product.price_history.length > 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Price History Table</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <th style={{ padding: '0.5rem', textAlign: 'left' }}>Date</th>
                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>Price</th>
                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>Original</th>
                  <th style={{ padding: '0.5rem', textAlign: 'right' }}>Discount</th>
                </tr>
              </thead>
              <tbody>
                {product.price_history.slice(0, 12).map((ph) => (
                  <tr key={ph.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '0.5rem' }}>{formatDate(ph.scraped_at)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', fontWeight: 600 }}>
                      {formatPrice(ph.price)}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#64748b' }}>
                      {ph.original_price ? formatPrice(ph.original_price) : '-'}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'right', color: '#22c55e' }}>
                      {ph.discount_percentage ? `${ph.discount_percentage}%` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProductPage;
