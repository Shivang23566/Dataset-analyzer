/**
 * Razorpay Payment Hook
 * Handles Razorpay checkout integration with proper script loading
 */

import { useCallback, useEffect, useState } from 'react';
import { createPaymentOrder, verifyPayment } from '../lib/api';

// Check if Razorpay script is loaded
const isRazorpayLoaded = (): boolean => {
  return typeof window !== 'undefined' && typeof window.Razorpay === 'function';
};

// Load Razorpay script dynamically if not already loaded
const loadRazorpayScript = (): Promise<boolean> => {
  return new Promise((resolve) => {
    // Already loaded
    if (isRazorpayLoaded()) {
      console.log('✅ Razorpay already loaded');
      resolve(true);
      return;
    }

    // Check if script tag already exists
    const existingScript = document.querySelector('script[src*="razorpay"]');
    if (existingScript) {
      // Wait for it to load
      existingScript.addEventListener('load', () => resolve(true));
      existingScript.addEventListener('error', () => resolve(false));
      // Check if already loaded after adding listeners
      if (isRazorpayLoaded()) {
        resolve(true);
      }
      return;
    }

    // Create and append script
    console.log('📜 Loading Razorpay script...');
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;

    script.onload = () => {
      console.log('✅ Razorpay script loaded successfully');
      resolve(true);
    };

    script.onerror = () => {
      console.error('❌ Failed to load Razorpay script');
      resolve(false);
    };

    document.body.appendChild(script);
  });
};

export interface UseRazorpayReturn {
  initiatePayment: (prefill?: { name?: string; email?: string }) => Promise<void>;
  isProcessing: boolean;
  isScriptLoaded: boolean;
  error: string | null;
}

export function useRazorpay(onSuccess: () => void): UseRazorpayReturn {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isScriptLoaded, setIsScriptLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load script on mount
  useEffect(() => {
    loadRazorpayScript().then((loaded) => {
      setIsScriptLoaded(loaded);
      if (!loaded) {
        console.error('Failed to load Razorpay SDK');
      }
    });
  }, []);

  const initiatePayment = useCallback(async (prefill?: { name?: string; email?: string }) => {
    console.log('🚀 Initiating payment...');
    setError(null);

    // Ensure script is loaded
    if (!isRazorpayLoaded()) {
      console.log('⏳ Razorpay not loaded, attempting to load...');
      const loaded = await loadRazorpayScript();
      if (!loaded) {
        setError('Payment service unavailable. Please refresh and try again.');
        return;
      }
      setIsScriptLoaded(true);
    }

    setIsProcessing(true);

    try {
      // Step 1: Create order on backend
      console.log('📦 Creating payment order...');
      const orderData = await createPaymentOrder();
      console.log('📦 Order created:', orderData);

      if (!orderData.order_id || !orderData.razorpay_key_id) {
        throw new Error('Invalid order response from server');
      }

      // Step 2: Configure Razorpay options
      const options: RazorpayOptions = {
        key: orderData.razorpay_key_id,
        amount: orderData.amount,
        currency: orderData.currency || 'INR',
        name: 'DataLens',
        description: 'Pro Plan — Monthly Subscription',
        order_id: orderData.order_id,

        handler: async (response: RazorpayResponse) => {
          console.log('💳 Payment successful, verifying...');
          console.log('   Payment ID:', response.razorpay_payment_id);
          console.log('   Order ID:', response.razorpay_order_id);

          try {
            // Step 3: Verify payment on backend
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });

            console.log('✅ Payment verified successfully');
            setIsProcessing(false);
            onSuccess();
          } catch (verifyError) {
            console.error('❌ Verification failed:', verifyError);
            setError('Payment verification failed. Please contact support.');
            setIsProcessing(false);
          }
        },

        prefill: {
          name: prefill?.name || orderData.user_name || '',
          email: prefill?.email || orderData.user_email || '',
        },

        theme: {
          color: '#c9a84c',
        },

        modal: {
          ondismiss: () => {
            console.log('🚪 Payment modal closed');
            setIsProcessing(false);
          },
        },
      };

      // Step 3: Open Razorpay checkout
      console.log('🪟 Opening Razorpay checkout...');

      // Double-check Razorpay is available
      if (typeof window.Razorpay !== 'function') {
        throw new Error('Razorpay SDK not available');
      }

      const razorpay = new window.Razorpay(options);

      razorpay.on('payment.failed', (response: RazorpayFailedResponse) => {
        console.error('❌ Payment failed:', response.error);
        setError(`Payment failed: ${response.error.description || 'Unknown error'}`);
        setIsProcessing(false);
      });

      razorpay.open();

    } catch (err) {
      console.error('❌ Payment initiation error:', err);
      const msg = err instanceof Error ? err.message : 'Failed to initiate payment. Please try again.';
      setError(msg);
      setIsProcessing(false);
    }
  }, [onSuccess]);

  return { initiatePayment, isProcessing, isScriptLoaded, error };
}

// Type definitions for Razorpay
interface RazorpayFailedResponse {
  error: {
    code: string;
    description: string;
    source: string;
    step: string;
    reason: string;
    metadata: {
      order_id: string;
      payment_id: string;
    };
  };
}

export default useRazorpay;
