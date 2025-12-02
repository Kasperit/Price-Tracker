import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { searchProducts, getProducts, getStores, Store, SearchResponse } from '../api';
import ProductCard from '../components/ProductCard';

function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState<number | null>(
    searchParams.get('store') ? parseInt(searchParams.get('store')!) : null
  );
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Load stores on mount
  useEffect(() => {
    getStores()
      .then(setStores)
      .catch((err) => console.error('Failed to load stores:', err));
  }, []);

  // Debounced search - triggers when query changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setCurrentPage(1);
      if (query.length >= 1) {
        setSearchParams({ q: query, ...(selectedStore && { store: selectedStore.toString() }) });
      } else if (query.length === 0) {
        // Clear search and show all products
        if (selectedStore) {
          setSearchParams({ store: selectedStore.toString() });
        } else {
          setSearchParams({});
        }
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [query]);

  // Load products when params change
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && q.length >= 1) {
      performSearch(q, selectedStore, currentPage);
    } else {
      loadAllProducts(selectedStore, currentPage);
    }
  }, [searchParams, selectedStore, currentPage]);

  const loadAllProducts = async (storeId: number | null, page: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getProducts(storeId || undefined, page);
      setResults(data);
    } catch (err) {
      setError('Failed to load products. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const performSearch = async (q: string, storeId: number | null, page: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await searchProducts(q, storeId || undefined, page);
      setResults(data);
    } catch (err) {
      setError('Failed to search products. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStoreFilter = (storeId: number | null) => {
    setSelectedStore(storeId);
    setCurrentPage(1);
    if (query) {
      setSearchParams({ 
        q: query, 
        ...(storeId && { store: storeId.toString() }) 
      });
    } else {
      // Clear search params when no query, just filter by store
      if (storeId) {
        setSearchParams({ store: storeId.toString() });
      } else {
        setSearchParams({});
      }
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div>
      <div className="search-container">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search products (e.g., iPhone, Samsung TV, laptop...)"
          className="search-input"
        />

        {stores.length > 0 && (
          <div className="store-filter">
            <button
              className={`store-chip ${selectedStore === null ? 'active' : ''}`}
              onClick={() => handleStoreFilter(null)}
            >
              All Stores
            </button>
            {stores.map((store) => (
              <button
                key={store.id}
                className={`store-chip ${selectedStore === store.id ? 'active' : ''}`}
                onClick={() => handleStoreFilter(store.id)}
              >
                {store.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">Searching products...</div>
      ) : results ? (
        <>
          <p style={{ marginBottom: '1rem', color: '#64748b' }}>
            Found {results.total} products
            {selectedStore && ` in ${stores.find(s => s.id === selectedStore)?.name}`}
          </p>

          {results.items.length > 0 ? (
            <>
              <div className="product-grid">
                {results.items.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>

              {results.total_pages > 1 && (
                <div className="pagination">
                  <button
                    className="pagination-button"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                  
                  {Array.from({ length: Math.min(5, results.total_pages) }, (_, i) => {
                    let pageNum: number;
                    if (results.total_pages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= results.total_pages - 2) {
                      pageNum = results.total_pages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        className={`pagination-button ${currentPage === pageNum ? 'active' : ''}`}
                        onClick={() => handlePageChange(pageNum)}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  
                  <button
                    className="pagination-button"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === results.total_pages}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              No products found. Try a different search term.
            </div>
          )}
        </>
      ) : (
        <div className="empty-state">
          <h2>Welcome to Historical Price Tracker</h2>
          <p style={{ marginTop: '1rem' }}>
            Search for products from Finnish electronics stores to see their price history.
          </p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
            Tracking prices from Verkkokauppa.com and Gigantti.fi
          </p>
        </div>
      )}
    </div>
  );
}

export default HomePage;
