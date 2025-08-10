import React, { useState, useEffect } from 'react';
import { cartAPI } from '../services/api';

function Cart({ token }) {
  const [cartItems, setCartItems] = useState([]);
  const [cartTotal, setCartTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (token) {
      fetchCart();
    }
  }, [token]);

  const fetchCart = async () => {
    try {
      setLoading(true);
      const response = await cartAPI.getCart();
      setCartItems(response.data.cart_items);
      setCartTotal(response.data.cart_total);
      setError('');
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to fetch cart');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckout = async () => {
    if (cartItems.length === 0) {
      setMessage('Your cart is empty!');
      return;
    }

    setCheckoutLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await cartAPI.checkout();
      setMessage(`Checkout successful! Order #${response.data.order.id} for $${response.data.order.total_amount.toFixed(2)}`);
      
      // Clear cart after successful checkout
      setCartItems([]);
      setCartTotal(0);
    } catch (error) {
      setError(error.response?.data?.error || 'Checkout failed');
    } finally {
      setCheckoutLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content">
        <div className="container">
          <div className="loading">Loading your cart...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      <div className="container">
        <h2 style={{ fontSize: '2.5rem', color: 'var(--primary-color)', marginBottom: '2rem', textAlign: 'center' }}>
          Shopping Cart
        </h2>

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

        {cartItems.length === 0 ? (
          <div className="empty-state">
            <h3>Your cart is empty</h3>
            <p>Go to the <a href="/shop" style={{ color: 'var(--primary-color)', fontWeight: 'bold' }}>shop</a> to add some items!</p>
            <a href="/shop" className="btn btn-primary">
              Continue Shopping
            </a>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '2rem' }}>
              {cartItems.map((item) => (
                <div key={item.id} className="cart-item">
                  <div className="cart-item-info">
                    <h4>{item.product_name}</h4>
                    <p>${item.price.toFixed(2)} x {item.quantity}</p>
                  </div>
                  <div className="cart-item-total">
                    ${item.total.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>

            <div className="cart-total">
              <span>Total:</span>
              <span className="cart-total-amount">${cartTotal.toFixed(2)}</span>
            </div>

            <button
              onClick={handleCheckout}
              disabled={checkoutLoading}
              className={`btn ${checkoutLoading ? '' : 'btn-success'} btn-large`}
              style={{ width: '100%' }}
            >
              {checkoutLoading ? 'Processing...' : `Checkout - $${cartTotal.toFixed(2)}`}
            </button>

            <div style={{ textAlign: 'center', marginTop: '2rem' }}>
              <a href="/shop" className="btn btn-secondary" style={{ marginRight: '1rem' }}>
                Continue Shopping
              </a>
              <button
                onClick={fetchCart}
                className="btn btn-primary"
              >
                Refresh Cart
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Cart;
