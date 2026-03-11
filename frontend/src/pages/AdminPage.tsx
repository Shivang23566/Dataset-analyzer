import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getCurrentUser,
  adminListCoupons,
  adminCreateCoupon,
  adminDeleteCoupon,
  adminListUsers,
  adminUpdateUserPlan,
} from '../lib/api';

interface Coupon {
  id: number;
  code: string;
  duration_days: number;
  max_uses: number;
  uses_count: number;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  subscription_plan: string;
  subscription_status: string | null;
  subscription_expires_at: string | null;
  is_superuser: boolean;
  is_active: boolean;
  created_at: string | null;
}

export default function AdminPage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [activeTab, setActiveTab] = useState<'coupons' | 'users'>('coupons');
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Coupons state
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [couponsLoading, setCouponsLoading] = useState(false);
  const [newCoupon, setNewCoupon] = useState({ code: '', duration_days: 7, max_uses: 10 });

  // Users state
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const loadCoupons = useCallback(async () => {
    setCouponsLoading(true);
    try {
      const data = await adminListCoupons();
      setCoupons((data.coupons || []) as Coupon[]);
    } catch {
      showToast('error', 'Failed to load coupons');
    } finally {
      setCouponsLoading(false);
    }
  }, [showToast]);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await adminListUsers();
      setUsers((data.users || []) as AdminUser[]);
    } catch {
      showToast('error', 'Failed to load users');
    } finally {
      setUsersLoading(false);
    }
  }, [showToast]);

  // Auth check
  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const user = await getCurrentUser();
        if (!user.is_superuser) {
          navigate('/dashboard');
          return;
        }
        setAuthorized(true);
        loadCoupons();
        loadUsers();
      } catch {
        navigate('/login');
      } finally {
        setIsLoading(false);
      }
    };
    checkAdmin();
  }, [navigate, loadCoupons, loadUsers]);

  const createCoupon = async () => {
    if (!newCoupon.code.trim()) {
      showToast('error', 'Coupon code is required');
      return;
    }
    try {
      await adminCreateCoupon(newCoupon);
      setNewCoupon({ code: '', duration_days: 7, max_uses: 10 });
      showToast('success', 'Coupon created successfully');
      loadCoupons();
    } catch (e: unknown) {
      showToast('error', e instanceof Error ? e.message : 'Failed to create coupon');
    }
  };

  const deleteCoupon = async (couponId: number) => {
    if (!confirm('Delete this coupon? This cannot be undone.')) return;
    try {
      await adminDeleteCoupon(couponId);
      showToast('success', 'Coupon deleted');
      loadCoupons();
    } catch (e: unknown) {
      showToast('error', e instanceof Error ? e.message : 'Failed to delete coupon');
    }
  };

  const updateUserPlan = async (userId: number, plan: 'free' | 'pro') => {
    try {
      await adminUpdateUserPlan(userId, plan, 30);
      showToast('success', `User plan updated to ${plan}`);
      loadUsers();
    } catch (e: unknown) {
      showToast('error', e instanceof Error ? e.message : 'Failed to update plan');
    }
  };

  if (isLoading) {
    return (
      <div className="admin-loading">
        <div className="admin-spinner" />
        <span>Verifying admin access…</span>
      </div>
    );
  }

  if (!authorized) return null;

  return (
    <div className="admin-page">
      {/* Toast */}
      {toast && (
        <div className={`admin-toast admin-toast-${toast.type}`}>
          <span>{toast.type === 'success' ? '✓' : '✕'}</span>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="admin-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, #c9a84c, #b8973f)',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, color: '#0e0f0d',
          }}>⚙</div>
          <div>
            <h1>Admin Dashboard</h1>
            <p style={{ fontSize: 12, color: '#5a5648', margin: 0 }}>
              Manage coupons, users, and system settings
            </p>
          </div>
        </div>
        <button className="admin-back-btn" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        <button
          className={activeTab === 'coupons' ? 'active' : ''}
          onClick={() => setActiveTab('coupons')}
        >
          <span style={{ marginRight: 6 }}>🎟</span> Coupons
        </button>
        <button
          className={activeTab === 'users' ? 'active' : ''}
          onClick={() => setActiveTab('users')}
        >
          <span style={{ marginRight: 6 }}>👥</span> Users
        </button>
      </div>

      {/* ─── COUPONS TAB ─── */}
      {activeTab === 'coupons' && (
        <div className="admin-section">
          <h2>Create New Coupon</h2>
          <div className="admin-form">
            <div className="admin-form-group">
              <label>Code</label>
              <input
                type="text"
                placeholder="e.g. PROMO_10"
                value={newCoupon.code}
                onChange={(e) => setNewCoupon({ ...newCoupon, code: e.target.value })}
              />
            </div>
            <div className="admin-form-group">
              <label>Duration (days)</label>
              <input
                type="number"
                min={-1}
                max={365}
                value={newCoupon.duration_days}
                onChange={(e) => setNewCoupon({ ...newCoupon, duration_days: parseInt(e.target.value) || 0 })}
              />
              <span className="admin-hint">-1 = lifetime</span>
            </div>
            <div className="admin-form-group">
              <label>Max Uses</label>
              <input
                type="number"
                min={1}
                value={newCoupon.max_uses}
                onChange={(e) => setNewCoupon({ ...newCoupon, max_uses: parseInt(e.target.value) || 1 })}
              />
            </div>
            <button className="admin-create-btn" onClick={createCoupon}>+ Create Coupon</button>
          </div>

          <h2 style={{ marginTop: 32 }}>All Coupons {couponsLoading && <span className="admin-loading-text">Loading…</span>}</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Duration</th>
                  <th>Usage</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Expires</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {coupons.length === 0 && !couponsLoading && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: '#5a5648', padding: 32 }}>No coupons yet</td></tr>
                )}
                {coupons.map((c) => (
                  <tr key={c.id}>
                    <td><code className="admin-code">{c.code}</code></td>
                    <td>{c.duration_days === -1 ? 'Lifetime' : `${c.duration_days} days`}</td>
                    <td>
                      <span className="admin-usage">
                        {c.uses_count} / {c.max_uses}
                      </span>
                    </td>
                    <td>
                      <span className={`admin-badge ${c.is_active ? 'admin-badge-active' : 'admin-badge-inactive'}`}>
                        {c.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="admin-date">{c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</td>
                    <td className="admin-date">{c.expires_at && c.expires_at !== 'never' ? new Date(c.expires_at).toLocaleDateString() : 'Never'}</td>
                    <td>
                      <button className="admin-delete-btn" onClick={() => deleteCoupon(c.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── USERS TAB ─── */}
      {activeTab === 'users' && (
        <div className="admin-section">
          <h2>All Users ({users.length}) {usersLoading && <span className="admin-loading-text">Loading…</span>}</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Plan</th>
                  <th>Expires</th>
                  <th>Role</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 && !usersLoading && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: '#5a5648', padding: 32 }}>No users found</td></tr>
                )}
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ color: '#5a5648' }}>#{u.id}</td>
                    <td>{u.email}</td>
                    <td>{u.full_name || <span style={{ color: '#3d3b34' }}>—</span>}</td>
                    <td>
                      <span className={`admin-badge ${u.subscription_plan === 'pro' ? 'admin-badge-pro' : 'admin-badge-free'}`}>
                        {u.subscription_plan?.toUpperCase() || 'FREE'}
                      </span>
                    </td>
                    <td className="admin-date">
                      {u.subscription_expires_at
                        ? new Date(u.subscription_expires_at).toLocaleDateString()
                        : '—'}
                    </td>
                    <td>
                      {u.is_superuser
                        ? <span className="admin-badge admin-badge-admin">Admin</span>
                        : <span style={{ color: '#5a5648' }}>User</span>}
                    </td>
                    <td>
                      {u.subscription_plan === 'free' ? (
                        <button className="admin-action-btn admin-upgrade-btn" onClick={() => updateUserPlan(u.id, 'pro')}>
                          ↑ Upgrade
                        </button>
                      ) : (
                        <button className="admin-action-btn admin-downgrade-btn" onClick={() => updateUserPlan(u.id, 'free')}>
                          ↓ Downgrade
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
