import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  signup: (email, password) => 
    api.post('/v1/signup', { email, password }),
  
  signin: (email, password) => 
    api.post('/v1/signin', { email, password }),
};

export const cartAPI = {
  addToCart: (product_name, price, quantity = 1) =>
    api.post('/v1/addToCart', { product_name, price, quantity }),
  
  getCart: () =>
    api.get('/v1/cart'),
  
  checkout: () =>
    api.post('/v1/checkout'),
};

export const healthAPI = {
  check: () =>
    api.get('/health'),
};

export default api;
