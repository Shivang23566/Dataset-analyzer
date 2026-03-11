import { useState, useEffect } from 'react';
import { fetchSubscription, applyCoupon, getPaymentStatus } from '../lib/api';
import { showToastGlobal } from '../hooks/useToast';
import { useRazorpay } from '../hooks/useRazorpay';
import type { SubscriptionData, PaymentStatus } from '../lib/types';

const FREE_FEATURES = [
  { label: 'Up to 3 datasets', included: true },
  { label: 'Full EDA analysis', included: true },
  { label: 'Visualization tools', included: true },
  { label: 'Preprocessing pipeline', included: false },
  { label: 'ML Model Builder', included: false },
  { label: 'Export & downloads', included: false },
];

const PRO_FEATURES = [
  'Unlimited datasets',
  '9-step preprocessing pipeline',
  '12 ML algorithms',
  'Model export & inference code',
  'Priority support',
];

export default function BillingSection() {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [payment, setPayment] = useState<PaymentStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // Coupon form
  const [couponCode, setCouponCode] = useState('');
  const [applyingCoupon, setApplyingCoupon] = useState(false);

  // Razorpay payment
  const { initiatePayment, isProcessing: upgrading, error: paymentError } = useRazorpay(() => {
    showToastGlobal({
      type: 'success',
      title: 'Payment Successful!',
      message: 'Welcome to DataLens Pro! Your account has been upgraded.',
    });
    setLoading(true);
    loadData();
  });

  useEffect(() => {
    if (paymentError) {
      showToastGlobal({ type: 'error', title: 'Payment Failed', message: paymentError });
    }
  }, [paymentError]);

  async function loadData() {
    try {
      const [subRes, payRes] = await Promise.all([
        fetchSubscription(),
        getPaymentStatus(),
      ]);
      setSubscription(subRes);
      setPayment(payRes);
    } catch {
      showToastGlobal({ type: 'error', title: 'Error', message: 'Failed to load subscription data' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  const plan = payment?.plan || subscription?.plan || 'free';
  const isPro = plan === 'pro';
  const status = subscription?.status || payment?.status || 'inactive';
  const expiresAt = subscription?.expires_at || payment?.expires_at;
  const startedAt = subscription?.started_at || payment?.subscription?.started_at;

  async function handleApplyCoupon() {
    const code = couponCode.trim();
    if (!code) {
      showToastGlobal({ type: 'error', title: 'Validation', message: 'Please enter a coupon code' });
      return;
    }
    setApplyingCoupon(true);
    try {
      const result = await applyCoupon(code);
      showToastGlobal({
        type: 'success',
        title: 'Coupon Applied!',
        message: result.message || `You now have Pro access${result.days_granted ? ` for ${result.days_granted} days` : ''}`,
      });
      setCouponCode('');
      // Refresh subscription data
      setLoading(true);
      await loadData();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Invalid coupon code';
      showToastGlobal({ type: 'error', title: 'Coupon Error', message: msg });
    } finally {
      setApplyingCoupon(false);
    }
  }

  function handleUpgrade() {
    initiatePayment();
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'long', year: 'numeric',
    });
  }

  if (loading) {
    return (
      <div style={{
        padding: '60px 0', textAlign: 'center',
        color: '#4a4840', fontStyle: 'italic', fontSize: 13,
        fontFamily: "'Inter', sans-serif",
      }}>Loading subscription...</div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }} className="db-fade-up">
      <div>
        <div style={{
          fontFamily: "'Inter', sans-serif", fontSize: 10,
          color: '#4a4840', letterSpacing: '0.12em', marginBottom: 6,
        }}>SUBSCRIPTION</div>
        <h2 style={{
          fontFamily: "'Inter', sans-serif",
          fontSize: 34, color: '#d4cfc8', fontWeight: 700,
        }}>Billing & Subscription</h2>
      </div>

      {/* ── Current Plan Card ── */}
      <div className="db-account-card">
        <div className="db-account-card-header" style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span className="db-account-card-title">CURRENT PLAN</span>
          {isPro && (
            <span style={{
              fontSize: 10, letterSpacing: '0.1em',
              color: '#2eb8a0', fontFamily: "'Inter', sans-serif",
              background: 'rgba(46,184,160,0.1)',
              border: '1px solid rgba(46,184,160,0.22)',
              padding: '3px 10px', borderRadius: 20,
            }}>✓ ACTIVE</span>
          )}
        </div>
        <div style={{ padding: '28px' }}>
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
            {/* Plan badge */}
            <div style={{
              width: 90, minHeight: 90,
              background: isPro
                ? 'linear-gradient(135deg, rgba(201,168,76,0.15), rgba(201,168,76,0.05))'
                : 'linear-gradient(135deg, rgba(122,118,105,0.15), rgba(122,118,105,0.05))',
              border: `1px solid ${isPro ? 'rgba(201,168,76,0.25)' : 'rgba(122,118,105,0.25)'}`,
              borderRadius: 14,
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              padding: '16px 0', flexShrink: 0,
            }}>
              <span style={{
                fontSize: 18, fontWeight: 700,
                color: isPro ? '#c9a84c' : '#7a7669',
                fontFamily: "'Inter', sans-serif",
              }}>{isPro ? 'PRO' : 'FREE'}</span>
              <span style={{
                fontSize: 10, color: isPro ? '#a07830' : '#5a5648',
                marginTop: 2, fontFamily: "'Inter', sans-serif",
              }}>Plan</span>
              {isPro && (
                <span style={{
                  fontSize: 10, color: '#c9a84c', marginTop: 4,
                  fontFamily: "'Inter', sans-serif",
                }}>₹219/mo</span>
              )}
            </div>

            {/* Plan details */}
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: 16, color: '#d4cfc8', fontWeight: 600,
                marginBottom: 8, fontFamily: "'Inter', sans-serif",
              }}>
                You're on the {isPro ? 'Pro' : 'Free'} plan
              </div>

              {isPro && (
                <div style={{
                  display: 'flex', flexDirection: 'column', gap: 6,
                  marginBottom: 16,
                }}>
                  <div style={{ fontSize: 12, color: '#5a5648' }}>
                    <span style={{ color: '#8a8272' }}>Status:</span>{' '}
                    <span style={{ color: status === 'active' ? '#2eb8a0' : '#c9933a' }}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </span>
                  </div>
                  {expiresAt && (
                    <div style={{ fontSize: 12, color: '#5a5648' }}>
                      <span style={{ color: '#8a8272' }}>Expires:</span>{' '}
                      {formatDate(expiresAt)}
                    </div>
                  )}
                  {startedAt && (
                    <div style={{ fontSize: 12, color: '#5a5648' }}>
                      <span style={{ color: '#8a8272' }}>Started:</span>{' '}
                      {formatDate(startedAt)}
                    </div>
                  )}
                  {payment?.days_remaining != null && payment.days_remaining > 0 && (
                    <div style={{ fontSize: 12, color: '#5a5648' }}>
                      <span style={{ color: '#8a8272' }}>Days remaining:</span>{' '}
                      <span style={{ color: '#2eb8a0' }}>{payment.days_remaining}</span>
                    </div>
                  )}
                </div>
              )}

              <div style={{ fontSize: 12, color: '#8a8272', marginBottom: 10 }}>
                {isPro ? 'Your plan includes:' : 'Includes:'}
              </div>

              {isPro ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {PRO_FEATURES.map((f, i) => (
                    <div key={i} style={{
                      fontSize: 12, color: '#9a9688',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <span style={{ color: '#2eb8a0', fontSize: 13 }}>✓</span>
                      {f}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {FREE_FEATURES.map((f, i) => (
                    <div key={i} style={{
                      fontSize: 12,
                      color: f.included ? '#9a9688' : '#3d3b34',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <span style={{
                        color: f.included ? '#2eb8a0' : '#3d3b34',
                        fontSize: 13,
                      }}>{f.included ? '✓' : '✗'}</span>
                      {f.label}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Upgrade Card (free users only) ── */}
      {!isPro && (
        <div className="db-account-card" style={{
          borderColor: 'rgba(201,168,76,0.2)',
        }}>
          <div className="db-account-card-header">
            <span className="db-account-card-title">UPGRADE TO PRO</span>
          </div>
          <div style={{ padding: '28px' }}>
            <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
              {/* Pro badge */}
              <div style={{
                width: 90, minHeight: 90,
                background: 'linear-gradient(135deg, rgba(201,168,76,0.18), rgba(201,168,76,0.06))',
                border: '1px solid rgba(201,168,76,0.3)',
                borderRadius: 14,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                padding: '16px 0', flexShrink: 0,
              }}>
                <span style={{
                  fontSize: 18, fontWeight: 700, color: '#c9a84c',
                  fontFamily: "'Inter', sans-serif",
                }}>PRO</span>
                <span style={{
                  fontSize: 10, color: '#a07830', marginTop: 2,
                  fontFamily: "'Inter', sans-serif",
                }}>Plan</span>
                <span style={{
                  fontSize: 10, color: '#c9a84c', marginTop: 4,
                  fontFamily: "'Inter', sans-serif",
                }}>₹219/mo</span>
              </div>

              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 14, color: '#d4cfc8', fontWeight: 600,
                  marginBottom: 6, fontFamily: "'Inter', sans-serif",
                }}>
                  Everything in Free, plus:
                </div>
                <div style={{
                  display: 'flex', flexDirection: 'column', gap: 7,
                  marginBottom: 20,
                }}>
                  {PRO_FEATURES.map((f, i) => (
                    <div key={i} style={{
                      fontSize: 12, color: '#9a9688',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <span style={{ color: '#c9a84c', fontSize: 13 }}>✓</span>
                      {f}
                    </div>
                  ))}
                </div>

                <button
                  className="db-btn-primary"
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  style={{
                    background: 'linear-gradient(135deg, #c9a84c, #a07830)',
                    color: '#fff', padding: '12px 28px', borderRadius: 10,
                    fontSize: 13, letterSpacing: '0.06em',
                    fontFamily: "'Inter', sans-serif", fontWeight: 600,
                    boxShadow: '0 4px 24px rgba(201,168,76,0.25)',
                    opacity: upgrading ? 0.6 : 1,
                  }}
                >
                  {upgrading ? 'Processing...' : 'Upgrade to Pro — ₹219/month'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Coupon Card ── */}
      <div className="db-account-card">
        <div className="db-account-card-header">
          <span className="db-account-card-title">HAVE A COUPON?</span>
        </div>
        <div style={{ padding: '24px 28px' }}>
          <div style={{
            display: 'flex', gap: 12, alignItems: 'flex-start',
          }}>
            <input
              className="db-input"
              type="text"
              value={couponCode}
              onChange={e => setCouponCode(e.target.value)}
              placeholder="Enter coupon code"
              onKeyDown={e => e.key === 'Enter' && handleApplyCoupon()}
              style={{ flex: 1 }}
            />
            <button
              className="db-btn-primary"
              onClick={handleApplyCoupon}
              disabled={applyingCoupon}
              style={{
                background: 'linear-gradient(135deg, #2eb8a0, #1a9a88)',
                color: '#fff', padding: '10px 20px', borderRadius: 9,
                fontSize: 12, letterSpacing: '0.06em',
                fontFamily: "'Inter', sans-serif", fontWeight: 500,
                boxShadow: '0 4px 20px rgba(46,184,160,0.2)',
                whiteSpace: 'nowrap', flexShrink: 0,
                opacity: applyingCoupon ? 0.6 : 1,
              }}
            >
              {applyingCoupon ? 'Applying...' : 'Apply Coupon'}
            </button>
          </div>
          {isPro && (
            <p style={{
              fontSize: 11, color: '#5a5648', fontStyle: 'italic', marginTop: 10,
            }}>
              You already have an active Pro subscription.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
