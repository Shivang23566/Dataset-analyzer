import { useState, useEffect } from 'react';
import { fetchProfile, updateProfile, updatePassword } from '../lib/api';
import { showToastGlobal } from '../hooks/useToast';
import type { ProfileData } from '../lib/types';

export default function AccountSection() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  // Profile form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchProfile();
        setProfile(data);
        setFullName(data.full_name || '');
        setEmail(data.email || '');
      } catch {
        showToastGlobal({ type: 'error', title: 'Error', message: 'Failed to load profile' });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleSaveProfile() {
    if (!fullName.trim()) {
      showToastGlobal({ type: 'error', title: 'Validation', message: 'Name cannot be empty' });
      return;
    }
    setSavingProfile(true);
    try {
      const updated = await updateProfile({ full_name: fullName.trim() });
      setProfile(updated);
      showToastGlobal({ type: 'success', title: 'Saved', message: 'Profile updated successfully' });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to update profile';
      showToastGlobal({ type: 'error', title: 'Error', message: msg });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleUpdatePassword() {
    if (!currentPassword || !newPassword) {
      showToastGlobal({ type: 'error', title: 'Validation', message: 'Please fill in all password fields' });
      return;
    }
    if (newPassword !== confirmPassword) {
      showToastGlobal({ type: 'error', title: 'Validation', message: 'New passwords do not match' });
      return;
    }
    if (newPassword.length < 8) {
      showToastGlobal({ type: 'error', title: 'Validation', message: 'Password must be at least 8 characters' });
      return;
    }
    setSavingPassword(true);
    try {
      await updatePassword({ current_password: currentPassword, new_password: newPassword });
      showToastGlobal({ type: 'success', title: 'Updated', message: 'Password changed successfully' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to update password';
      showToastGlobal({ type: 'error', title: 'Error', message: msg });
    } finally {
      setSavingPassword(false);
    }
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'long', year: 'numeric',
    });
  }

  function formatDateTime(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric', month: 'long', year: 'numeric',
    }) + ' at ' + d.toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit',
    });
  }

  if (loading) {
    return (
      <div className="db-loading-state">Loading profile...</div>
    );
  }

  return (
    <div className="db-fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <div className="db-section-overline">SETTINGS</div>
        <h2 className="db-section-title">Account Settings</h2>
      </div>

      {/* ── Profile Information Card ── */}
      <div className="db-account-card">
        <div className="db-account-card-header">
          <span className="db-account-card-title">PROFILE INFORMATION</span>
        </div>
        <div className="db-card-body">
          <div className="db-form-group">
            <label className="db-label">Full Name</label>
            <input
              className="db-input"
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder="Enter your full name"
              maxLength={100}
            />
          </div>
          <div className="db-form-group">
            <label className="db-label">Email Address</label>
            <input
              className="db-input db-input-disabled"
              type="email"
              value={email}
              disabled
              title="Email cannot be changed"
            />
            <span className="db-input-hint">Email address cannot be changed</span>
          </div>

          <div className="db-meta-row">
            <div>
              <span className="db-meta-label">Member Since</span>
              <span className="db-meta-value">{formatDate(profile?.created_at ?? null)}</span>
            </div>
            <div>
              <span className="db-meta-label">Last Login</span>
              <span className="db-meta-value">{formatDateTime(profile?.last_login_at ?? null)}</span>
            </div>
          </div>

          <div className="db-btn-row">
            <button
              className="db-btn-primary db-btn-teal"
              onClick={handleSaveProfile}
              disabled={savingProfile}
            >
              {savingProfile ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Change Password Card ── */}
      <div className="db-account-card">
        <div className="db-account-card-header">
          <span className="db-account-card-title">CHANGE PASSWORD</span>
        </div>
        <div className="db-card-body">
          <div className="db-form-group">
            <label className="db-label">Current Password</label>
            <input
              className="db-input"
              type="password"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              placeholder="Enter current password"
            />
          </div>
          <div className="db-form-group">
            <label className="db-label">New Password</label>
            <input
              className="db-input"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="Enter new password"
            />
          </div>
          <div className="db-form-group">
            <label className="db-label">Confirm New Password</label>
            <input
              className="db-input"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
            />
          </div>

          <div className="db-btn-row" style={{ marginTop: 4 }}>
            <button
              className="db-btn-primary db-btn-gold"
              onClick={handleUpdatePassword}
              disabled={savingPassword}
            >
              {savingPassword ? 'Updating...' : 'Update Password'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
