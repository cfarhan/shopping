import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { cartAPI, paymentAPI } from '../services/api';
import CheckoutForm from './CheckoutForm';

let stripePromise = null;

function Cart({ token }) {
  const [cartItems, setCartItems] = useState([]);
  const [cartTotal, setCartTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [showStripeCheckout, setShowStripeCheckout] = useState(false);
  const [stripeConfig, setStripeConfig] = useState(null);

  useEffect(() => {
    if (token) {
      fetchCart();
      fetchStripeConfig();
    }
  }, [token]);

  const fetchStripeConfig = async () => {
    try {
      const response = await paymentAPI.getStripeConfig();
      setStripeConfig(response.data);
      
      if (response.data.publicKey && !stripePromise) {
        stripePromise = loadStripe(response.data.publicKey);
      }
    } catch (error) {
      console.error('Failed to fetch Stripe config:', error);
    }
  };

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

  const handleLegacyCheckout = async () => {
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

  const handleStripePaymentSuccess = (result) => {
    setMessage(`Payment successful! Order completed for $${cartTotal.toFixed(2)}`);
    setShowStripeCheckout(false);
    
    // Clear cart after successful payment
    setCartItems([]);
    setCartTotal(0);
  };

  const handleStripePaymentError = (errorMessage) => {
    setError(errorMessage);
    setShowStripeCheckout(false);
  };

  if (loading) {
    return <div className="loading">Loading cart...</div>;
  }

  return (
    <div className="cart">
      <h2>Shopping Cart</h2>
      
      {message && (
        <div className="success-message">
          {message}
        </div>
      )}
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {cartItems.length === 0 ? (
        <div className="empty-cart">
          <p>Your cart is empty</p>
        </div>
      ) : (
        <>
          <div className="cart-items">
            {cartItems.map((item) => (
              <div key={item.id} className="cart-item">
                <div className="item-info">
                  <h4>{item.product_name}</h4>
                  <p>Price: ${item.price.toFixed(2)}</p>
                  <p>Quantity: {item.quantity}</p>
                  <p className="item-total">Total: ${item.total.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="cart-summary">
            <div className="cart-total">
              <h3>Total: ${cartTotal.toFixed(2)}</h3>
            </div>

            <div className="checkout-options">
              {!showStripeCheckout ? (
                <>
                  <button
                    onClick={() => setShowStripeCheckout(true)}
                    className="stripe-checkout-button"
                    disabled={!stripeConfig?.publicKey}
                  >
                    Pay with Card (Stripe)
                  </button>
                  
                  <button
                    onClick={handleLegacyCheckout}
                    disabled={checkoutLoading}
                    className="legacy-checkout-button"
                  >
                    {checkoutLoading ? 'Processing...' : 'Quick Checkout (Legacy)'}
                  </button>
                </>
              ) : (
                <div className="stripe-checkout">
                  {stripePromise && stripeConfig?.publicKey ? (
                    <Elements stripe={stripePromise}>
                      <CheckoutForm
                        cartTotal={cartTotal}
                        onPaymentSuccess={handleStripePaymentSuccess}
                        onPaymentError={handleStripePaymentError}
                      />
                    </Elements>
                  ) : (
                    <div>Loading payment form...</div>
                  )}
                  
                  <button
                    onClick={() => setShowStripeCheckout(false)}
                    className="cancel-payment-button"
                  >
                    Cancel Payment
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Cart;
