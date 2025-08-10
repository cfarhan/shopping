import React, { useState } from 'react';
import { cartAPI } from '../services/api';

// Sample products - in a real app, this would come from your backend
const SAMPLE_PRODUCTS = [
  { id: 1, name: 'iPhone 15', price: 999.99, description: 'Latest iPhone with amazing features' },
  { id: 2, name: 'MacBook Pro', price: 1999.99, description: 'Powerful laptop for professionals' },
  { id: 3, name: 'AirPods Pro', price: 249.99, description: 'Wireless earbuds with noise cancellation' },
  { id: 4, name: 'iPad Air', price: 599.99, description: 'Versatile tablet for work and play' },
  { id: 5, name: 'Apple Watch', price: 399.99, description: 'Smart watch with health tracking' },
  { id: 6, name: 'Magic Keyboard', price: 129.99, description: 'Wireless keyboard for Mac' },
];

function Shop({ token }) {
  const [loading, setLoading] = useState({});
  const [message, setMessage] = useState('');

  const addToCart = async (product) => {
    if (!token) {
      setMessage('Please sign in to add items to cart');
      return;
    }

    setLoading({ ...loading, [product.id]: true });
    
    try {
      const response = await cartAPI.addToCart(product.name, product.price, 1);
      setMessage(`${product.name} added to cart! Cart total: $${response.data.cart_total.toFixed(2)}`);
    } catch (error) {
      setMessage(error.response?.data?.error || 'Failed to add item to cart');
    } finally {
      setLoading({ ...loading, [product.id]: false });
    }
  };

  return (
    <div className="page-content">
      <div className="container">
        <h2 style={{ fontSize: '2.5rem', color: 'var(--primary-color)', marginBottom: '2rem', textAlign: 'center' }}>
          Shop Our Products
        </h2>
        
        {message && (
          <div className={`alert ${message.includes('Failed') ? 'alert-error' : 'alert-success'}`}>
            {message}
          </div>
        )}

        <div className="product-grid">
          {SAMPLE_PRODUCTS.map((product) => (
            <div key={product.id} className="product-card">
              <h3 className="product-name">{product.name}</h3>
              <p className="product-description">{product.description}</p>
              <p className="product-price">${product.price.toFixed(2)}</p>
              
              <button
                onClick={() => addToCart(product)}
                disabled={loading[product.id]}
                className={`btn ${loading[product.id] ? '' : 'btn-primary'}`}
                style={{ width: '100%' }}
              >
                {loading[product.id] ? 'Adding...' : 'Add to Cart'}
              </button>
            </div>
          ))}
        </div>

        {!token && (
          <div className="alert alert-warning" style={{ marginTop: '3rem', textAlign: 'center' }}>
            <p style={{ fontSize: '1.1rem', margin: 0 }}>
              Please <a href="/signin" style={{ color: 'var(--primary-color)', fontWeight: 'bold' }}>sign in</a> or{' '}
              <a href="/signup" style={{ color: 'var(--primary-color)', fontWeight: 'bold' }}>sign up</a> to add items to your cart!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Shop;
