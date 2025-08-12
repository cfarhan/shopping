import axios from 'axios';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? process.env.REACT_APP_API_URL || window.location.origin
  : 'http://localhost:5000';

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

export const productAPI = {
  getProducts: (category = null) => {
    const params = category ? { category } : {};
    return api.get('/v1/products', { params });
  },
  
  getProduct: (productId) =>
    api.get(`/v1/products/${productId}`),
};

export const cartAPI = {
  addToCart: (product_id, quantity = 1) =>
    api.post('/v1/cart/add', { product_id, quantity }),
  
  updateCartItem: (product_id, quantity) =>
    api.put('/v1/cart/update', { product_id, quantity }),
  
  removeFromCart: (product_id) =>
    api.delete('/v1/cart/remove', { data: { product_id } }),
  
  getCart: () =>
    api.get('/v1/cart'),
  
  checkout: () =>
    api.post('/v1/checkout'),
};

export const paymentAPI = {
  getStripeConfig: () =>
    api.get('/v1/stripe-config'),
  
  createPaymentIntent: () =>
    api.post('/v1/create-payment-intent'),
  
  confirmPayment: (payment_intent_id) =>
    api.post('/v1/confirm-payment', { payment_intent_id }),
};

export const orderAPI = {
  getOrders: () =>
    api.get('/v1/orders'),
};

export const healthAPI = {
  check: () =>
    api.get('/health'),
};

export const adminAPI = {
  seedProducts: () =>
    api.post('/admin/seed-products'),
};

export default api;
