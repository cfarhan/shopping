import React, { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { paymentAPI } from '../services/api';

const CARD_ELEMENT_OPTIONS = {
  style: {
    base: {
      color: '#424770',
      fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
      fontSmoothing: 'antialiased',
      fontSize: '16px',
      '::placeholder': {
        color: '#aab7c4'
      }
    },
    invalid: {
      color: '#9e2146',
      iconColor: '#9e2146'
    }
  }
};

function CheckoutForm({ onPaymentSuccess, onPaymentError, cartTotal }) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Create payment intent
      const { data } = await paymentAPI.createPaymentIntent();
      const { client_secret, order_id } = data;

      // Confirm payment
      const result = await stripe.confirmCardPayment(client_secret, {
        payment_method: {
          card: elements.getElement(CardElement)
        }
      });

      if (result.error) {
        setError(result.error.message);
        onPaymentError(result.error.message);
      } else {
        // Payment succeeded
        await paymentAPI.confirmPayment(result.paymentIntent.id);
        onPaymentSuccess({
          paymentIntent: result.paymentIntent,
          orderId: order_id
        });
      }
    } catch (err) {
      const errorMessage = err.response?.data?.error || 'Payment failed';
      setError(errorMessage);
      onPaymentError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="checkout-form">
      <div className="payment-info">
        <h3>Payment Information</h3>
        <p>Total: ${cartTotal.toFixed(2)}</p>
      </div>
      
      <div className="card-element-container">
        <CardElement options={CARD_ELEMENT_OPTIONS} />
      </div>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      <button
        type="submit"
        disabled={!stripe || loading}
        className={`pay-button ${loading ? 'processing' : ''}`}
      >
        {loading ? 'Processing...' : `Pay $${cartTotal.toFixed(2)}`}
      </button>
      
      <div className="payment-security">
        <small>🔒 Your payment information is secure and encrypted</small>
      </div>
    </form>
  );
}

export default CheckoutForm; 