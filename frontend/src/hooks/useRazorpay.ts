import { useState } from 'react';
import { createPaymentOrder, verifyPayment } from '../lib/api';

export interface UseRazorpayReturn {
  initiatePayment: (prefill?: { name?: string; email?: string }) => Promise<void>;
  isProcessing: boolean;
  error: string | null;
}

export function useRazorpay(onSuccess: () => void): UseRazorpayReturn {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initiatePayment = async (prefill?: { name?: string; email?: string }) => {
    setIsProcessing(true);
    setError(null);

    try {
      // Step 1: Create order on backend
      const orderData = await createPaymentOrder();

      // Step 2: Open Razorpay checkout
      const options: RazorpayOptions = {
        key: orderData.razorpay_key_id,
        amount: orderData.amount,
        currency: orderData.currency || 'INR',
        name: 'DataLens',
        description: 'Pro Plan — Monthly Subscription',
        order_id: orderData.order_id,
        handler: async (response: RazorpayResponse) => {
          // Step 3: Verify payment on backend
          try {
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setIsProcessing(false);
            onSuccess();
          } catch {
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
            setIsProcessing(false);
          },
        },
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to initiate payment. Please try again.';
      setError(msg);
      setIsProcessing(false);
    }
  };

  return { initiatePayment, isProcessing, error };
}
