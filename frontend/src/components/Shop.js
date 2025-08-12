import React, { useState, useEffect } from 'react';
import { cartAPI, productAPI, adminAPI } from '../services/api';

function Shop({ token }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState({});
  const [pageLoading, setPageLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  useEffect(() => {
    fetchProducts();
  }, [selectedCategory]);

  const fetchProducts = async () => {
    try {
      setPageLoading(true);
      setError('');
      
      const response = await productAPI.getProducts(selectedCategory || null);
      
      if (response.data.products.length === 0) {
        // If no products, try to seed them (for development)
        setMessage('No products found. Seeding initial products...');
        try {
          await adminAPI.seedProducts();
          const seededResponse = await productAPI.getProducts(selectedCategory || null);
          setProducts(seededResponse.data.products);
          setMessage('Products loaded successfully!');
        } catch (seedError) {
          setError('No products available. Please contact administrator.');
        }
      } else {
        setProducts(response.data.products);
      }
    } catch (error) {
      console.error('Failed to fetch products:', error);
      setError('Failed to load products. Please try again.');
    } finally {
      setPageLoading(false);
    }
  };

  const addToCart = async (product) => {
    if (!token) {
      setMessage('Please sign in to add items to cart');
      return;
    }

    setLoading({ ...loading, [product.id]: true });
    setMessage('');
    setError('');
    
    try {
      const response = await cartAPI.addToCart(product.id, 1);
      setMessage(`${product.name} added to cart! Cart total: $${response.data.cart_total.toFixed(2)}`);
    } catch (error) {
      console.error('Add to cart error:', error);
      setError(error.response?.data?.error || 'Failed to add item to cart');
    } finally {
      setLoading({ ...loading, [product.id]: false });
    }
  };

  const getUniqueCategories = () => {
    const categories = products.map(p => p.category).filter(Boolean);
    return [...new Set(categories)];
  };

  if (pageLoading) {
    return (
      <div className="page-content">
        <div className="container">
          <div className="loading">Loading products...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="container">
        <h2 style={{ fontSize: '2.5rem', color: 'var(--primary-color)', marginBottom: '2rem', textAlign: 'center' }}>
          Shop Our Products
        </h2>
        
        {/* Category Filter */}
        {getUniqueCategories().length > 0 && (
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <select 
              value={selectedCategory} 
              onChange={(e) => setSelectedCategory(e.target.value)}
              style={{ 
                padding: '0.5rem 1rem', 
                fontSize: '1rem', 
                borderRadius: '4px',
                border: '2px solid var(--border-color)'
              }}
            >
              <option value="">All Categories</option>
              {getUniqueCategories().map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
        )}
        
        {message && (
          <div className="alert alert-success">
            {message}
          </div>
        )}
        
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {products.length === 0 ? (
          <div className="empty-state">
            <h3>No products available</h3>
            <p>Please check back later or contact us for more information.</p>
            <button 
              onClick={fetchProducts}
              className="btn btn-primary"
            >
              Refresh Products
            </button>
          </div>
        ) : (
          <div className="product-grid">
            {products.map((product) => (
              <div key={product.id} className="product-card">
                {product.image_url && (
                  <img 
                    src={product.image_url} 
                    alt={product.name}
                    style={{ width: '100%', height: '200px', objectFit: 'cover', marginBottom: '1rem' }}
                  />
                )}
                
                <h3 className="product-name">{product.name}</h3>
                <p className="product-description">{product.description}</p>
                
                {product.category && (
                  <div style={{ 
                    display: 'inline-block', 
                    backgroundColor: 'var(--primary-color)', 
                    color: 'white', 
                    padding: '0.25rem 0.5rem', 
                    borderRadius: '12px', 
                    fontSize: '0.8rem',
                    marginBottom: '0.5rem'
                  }}>
                    {product.category}
                  </div>
                )}
                
                <p className="product-price">${product.price.toFixed(2)}</p>
                
                {product.stock_quantity > 0 ? (
                  <>
                    <p style={{ color: 'var(--success-color)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                      {product.stock_quantity} in stock
                    </p>
                    <button
                      onClick={() => addToCart(product)}
                      disabled={loading[product.id]}
                      className={`btn ${loading[product.id] ? '' : 'btn-primary'}`}
                      style={{ width: '100%' }}
                    >
                      {loading[product.id] ? 'Adding...' : 'Add to Cart'}
                    </button>
                  </>
                ) : (
                  <button 
                    disabled 
                    className="btn" 
                    style={{ width: '100%', backgroundColor: '#ccc', color: '#666' }}
                  >
                    Out of Stock
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

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
