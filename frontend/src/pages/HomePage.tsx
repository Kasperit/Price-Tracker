import { useState, useEffect } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import { searchProducts, getProducts, getStores, Store, SearchResponse } from '../api';
import ProductCard from '../components/ProductCard';

function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  
  // Check if returning from product page with saved state
  const hasLocationState = location.state && (location.state as any)?.page;
  
  // Restore state from location state if returning from product page, otherwise use URL params
  const initialPage = hasLocationState 
    ? (location.state as any).page 
    : parseInt(searchParams.get('page') || '1');
  const initialSortBy = hasLocationState
    ? (location.state as any).sortBy
    : (searchParams.get('sort') || 'name');
  const initialScrollY = hasLocationState ? (location.state as any).scrollY : 0;
  
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState<number | null>(
    searchParams.get('store') ? parseInt(searchParams.get('store')!) : null
  );
  const [sortBy, setSortBy] = useState<string>(initialSortBy);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [isRestoringState, setIsRestoringState] = useState(hasLocationState);

  // Restore scroll position when returning from product page
  useEffect(() => {
    if (initialScrollY > 0 && isRestoringState) {
      // Wait for content to load before scrolling
      setTimeout(() => {
        window.scrollTo(0, initialScrollY);
        // Clear the scroll position from location state
        window.history.replaceState({}, '');
        setIsRestoringState(false);
      }, 100);
    } else if (hasLocationState) {
      // Clear location state even if no scroll
      window.history.replaceState({}, '');
      setIsRestoringState(false);
    }
  }, [results]); // Trigger when results load

  // Load stores on mount
  useEffect(() => {
    getStores()
      .then(setStores)
      .catch((err) => console.error('Failed to load stores:', err));
  }, []);

  // Debounced search - triggers when query changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      // Don't reset page if we're restoring state
      if (!isRestoringState) {
        setCurrentPage(1);
      }
      const params: any = {};
      if (query.length >= 1) {
        params.q = query;
      }
      if (selectedStore) {
        params.store = selectedStore.toString();
      }
      if (sortBy !== 'name') {
        params.sort = sortBy;
      }
      if (currentPage > 1 && !isRestoringState) {
        params.page = currentPage.toString();
      }
      if (Object.keys(params).length > 0) {
        setSearchParams(params, { replace: isRestoringState });
      } else {
        setSearchParams({}, { replace: isRestoringState });
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [query]);

  // Update URL params when filters change (but not during state restoration)
  useEffect(() => {
    if (isRestoringState) return; // Skip URL update during restoration
    
    const params: any = {};
    if (query) params.q = query;
    if (selectedStore) params.store = selectedStore.toString();
    if (currentPage > 1) params.page = currentPage.toString();
    if (sortBy !== 'name') params.sort = sortBy;
    
    if (Object.keys(params).length > 0) {
      setSearchParams(params);
    } else {
      setSearchParams({});
    }
  }, [selectedStore, currentPage, sortBy, isRestoringState]);

  // Load products when params change
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && q.length >= 1) {
      performSearch(q, selectedStore, currentPage, sortBy);
    } else {
      loadAllProducts(selectedStore, currentPage, sortBy);
    }
  }, [searchParams, selectedStore, currentPage, sortBy]);

  const loadAllProducts = async (storeId: number | null, page: number, sort: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getProducts(storeId || undefined, page, 20, sort);
      setResults(data);
    } catch (err) {
      setError('Failed to load products. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const performSearch = async (q: string, storeId: number | null, page: number, sort: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await searchProducts(q, storeId || undefined, page, 20, sort);
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
  };

  const handleSortChange = (newSort: string) => {
    setSortBy(newSort);
    setCurrentPage(1);
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

        {results && results.items.length > 0 && (
          <div className="sort-container">
            <label htmlFor="sort-select">Sort by:</label>
            <select 
              id="sort-select"
              value={sortBy} 
              onChange={(e) => handleSortChange(e.target.value)}
              className="sort-select"
            >
              <option value="name">Name (A-Z)</option>
              <option value="price_asc">Price (Low to High)</option>
              <option value="price_desc">Price (High to Low)</option>
            </select>
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
