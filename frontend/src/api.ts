import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Store {
  id: number;
  name: string;
  base_url: string;
  is_active: boolean;
  created_at: string;
}

export interface PriceHistory {
  id: number;
  price: number;
  original_price: number | null;
  currency: string;
  scraped_at: string;
  discount_percentage: number | null;
}

export interface ProductListItem {
  id: number;
  name: string;
  url: string;
  brand: string | null;
  store_id: number;
  external_id: string;
  image_url: string | null;
  is_available: boolean;
  latest_price: number | null;
  store_name: string | null;
}

export interface ProductDetail {
  id: number;
  name: string;
  url: string;
  brand: string | null;
  store_id: number;
  external_id: string;
  image_url: string | null;
  description: string | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
  store: Store;
  price_history: PriceHistory[];
}

export interface PriceStatistics {
  current_price: number | null;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  price_change: number | null;
  price_change_percent: number | null;
}

export interface SearchResponse {
  items: ProductListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// API functions
export const getStores = async (): Promise<Store[]> => {
  const response = await api.get<Store[]>('/stores');
  return response.data;
};

export const getProducts = async (
  storeId?: number,
  page: number = 1,
  pageSize: number = 20,
  sortBy: string = 'name'
): Promise<SearchResponse> => {
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
    sort_by: sortBy,
  };
  if (storeId) {
    params.store_id = storeId;
  }
  const response = await api.get<SearchResponse>('/products', { params });
  return response.data;
};

export const searchProducts = async (
  query: string,
  storeId?: number,
  page: number = 1,
  pageSize: number = 20,
  sortBy: string = 'name'
): Promise<SearchResponse> => {
  const params: Record<string, string | number> = {
    q: query,
    page,
    page_size: pageSize,
    sort_by: sortBy,
  };
  if (storeId) {
    params.store_id = storeId;
  }
  const response = await api.get<SearchResponse>('/products/search', { params });
  return response.data;
};

export const getProduct = async (id: number): Promise<ProductDetail> => {
  const response = await api.get<ProductDetail>(`/products/${id}`);
  return response.data;
};

export const getProductHistory = async (
  id: number,
  limit?: number
): Promise<PriceHistory[]> => {
  const params = limit ? { limit } : {};
  const response = await api.get<PriceHistory[]>(`/products/${id}/history`, { params });
  return response.data;
};

export const getProductStatistics = async (id: number): Promise<PriceStatistics> => {
  const response = await api.get<PriceStatistics>(`/products/${id}/statistics`);
  return response.data;
};

export default api;
