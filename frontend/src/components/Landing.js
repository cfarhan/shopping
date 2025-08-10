import React from 'react';
import { Link } from 'react-router-dom';

function Landing() {
  return (
    <div className="page-content">
      {/* Promotional Banner */}
      <div className="promo-banner">
        <p className="promo-text">🎉 GRAND OPENING SALE - Up to 50% OFF Select Items + Free Shipping!</p>
      </div>

      {/* Hero Section */}
      <div className="hero-section">
        <div className="container">
          <h1 className="hero-title">Welcome to Flask Shop! 🛍️</h1>
          <p className="hero-subtitle">Your one-stop shop for everything you need!</p>
          
          <div className="hero-buttons">
            <Link to="/shop" className="btn btn-primary btn-large">
              Start Shopping
            </Link>
            <Link to="/signin" className="btn btn-secondary btn-large">
              Sign In
            </Link>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="container">
        <div className="product-grid">
          <div className="product-card">
            <h3 className="product-name">🚚 Free Shipping</h3>
            <p className="product-description">Free shipping on orders over $50. Fast and reliable delivery to your doorstep.</p>
          </div>
          
          <div className="product-card">
            <h3 className="product-name">🔒 Secure Checkout</h3>
            <p className="product-description">Your personal information is protected with industry-standard encryption.</p>
          </div>
          
          <div className="product-card">
            <h3 className="product-name">⭐ Quality Products</h3>
            <p className="product-description">Carefully curated selection of high-quality products from trusted brands.</p>
          </div>
        </div>

        {/* Call to Action */}
        <div style={{ textAlign: 'center', marginTop: '3rem', padding: '2rem', backgroundColor: 'var(--light-gray)', borderRadius: '8px' }}>
          <h2 style={{ color: 'var(--primary-color)', marginBottom: '1rem' }}>Ready to Get Started?</h2>
          <p style={{ fontSize: '1.1rem', marginBottom: '2rem', color: '#666' }}>
            New here? <Link to="/signup" style={{ color: 'var(--primary-color)', fontWeight: 'bold' }}>Create an account</Link> to start shopping with exclusive member benefits!
          </p>
          <Link to="/signup" className="btn btn-success btn-large">
            Join Now - It's Free!
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Landing;
