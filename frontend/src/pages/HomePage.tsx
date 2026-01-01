import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { searchProducts, getProducts, getStores, Store, SearchResponse } from '../api';
import ProductCard from '../components/ProductCard';

function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const scrollPositions = useRef<Map<string, number>>(new Map());
  const debounceTimer = useRef<number | null>(null);
  
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState<number | null>(
    searchParams.get('store') ? parseInt(searchParams.get('store')!) : null
  );
  const [sortBy, setSortBy] = useState<string>(searchParams.get('sort') || 'name');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1'));
  const firstRender = useRef(true);

  // Save scroll position before leaving
  useEffect(() => {
    const handleScroll = () => {
      const key = `${query}_${selectedStore}_${currentPage}_${sortBy}`;
      scrollPositions.current.set(key, window.scrollY);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [query, selectedStore, currentPage, sortBy]);

  // Restore scroll position when page loads
  useEffect(() => {
    if (!loading && results) {
      const key = `${query}_${selectedStore}_${currentPage}_${sortBy}`;
      const savedScroll = scrollPositions.current.get(key);
      
      if (savedScroll !== undefined) {
        requestAnimationFrame(() => {
          window.scrollTo(0, savedScroll);
        });
      } else if (!firstRender.current) {
        // New page/filter - scroll to top
        window.scrollTo(0, 0);
      }
      
      firstRender.current = false;
    }
  }, [loading, results, query, selectedStore, currentPage, sortBy]);

  // Load stores on mount
  useEffect(() => {
    getStores()
      .then(setStores)
      .catch((err) => console.error('Failed to load stores:', err));
  }, []);

  // Sync state with URL params
  useEffect(() => {
    const page = parseInt(searchParams.get('page') || '1');
    const sort = searchParams.get('sort') || 'name';
    const store = searchParams.get('store') ? parseInt(searchParams.get('store')!) : null;
    const q = searchParams.get('q') || '';
    
    setCurrentPage(page);
    setSortBy(sort);
    setSelectedStore(store);
    setQuery(q);
  }, [searchParams]);

  // Restore scroll position when navigating back
  useEffect(() => {
    const savedScrollY = sessionStorage.getItem('homeScrollY');
    if (savedScrollY) {
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedScrollY));
        sessionStorage.removeItem('homeScrollY');
      }, 100);
    }
  }, []);

  // Load products when params change
  useEffect(() => {
    const page = parseInt(searchParams.get('page') || '1');
    const sort = searchParams.get('sort') || 'name';
    const store = searchParams.get('store') ? parseInt(searchParams.get('store')!) : null;
    const q = searchParams.get('q');
    
    if (q && q.length >= 2) {
      performSearch(q, store, page, sort);
    } else {
      loadAllProducts(store, page, sort);
    }
  }, [searchParams]);

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

  const updateURLParams = (updates: any) => {
    const params: any = { ...Object.fromEntries(searchParams) };
    
    Object.keys(updates).forEach(key => {
      if (updates[key] !== null && updates[key] !== undefined && updates[key] !== '') {
        params[key] = updates[key].toString();
      } else {
        delete params[key];
      }
    });
    
    // Remove defaults
    if (params.page === '1') delete params.page;
    if (params.sort === 'name') delete params.sort;
    
    setSearchParams(params);
  };

  const handleStoreFilter = (storeId: number | null) => {
    updateURLParams({ store: storeId, page: null });
  };

  const handleSortChange = (newSort: string) => {
    updateURLParams({ sort: newSort, page: null });
  };

  const handlePageChange = (page: number) => {
    updateURLParams({ page: page > 1 ? page : null });
  };

  const handleQueryChange = (newQuery: string) => {
    setQuery(newQuery);
    
    // Clear previous timeout
    if (debounceTimer.current !== null) {
      clearTimeout(debounceTimer.current);
    }
    
    // Debounce URL update - only update if 2+ characters or empty
    debounceTimer.current = window.setTimeout(() => {
      if (newQuery.length >= 2 || newQuery.length === 0) {
        updateURLParams({ q: newQuery || null, page: null });
      }
    }, 800);
  };

  return (
    <div>
      <div className="search-container">
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
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
