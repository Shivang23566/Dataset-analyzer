/**
 * Profile Dropdown Component
 * Shows user info and menu options with logout
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  CreditCard,
  LogOut,
  ChevronDown,
  LayoutDashboard,
  Database,
  Download
} from 'lucide-react';
import { clearAuth, getLoggedInEmail } from '../lib/authStore';
import { logout as apiLogout } from '../lib/api';
import './ProfileDropdown.css';

interface ProfileDropdownProps {
  userName?: string;
  userEmail?: string;
  userPlan?: 'FREE' | 'PRO' | 'ADMIN';
  onTabChange?: (tab: string) => void;
}

interface MenuItem {
  label: string;
  icon: React.ReactNode;
  action: () => void;
  badge?: string;
  badgeColor?: 'purple' | 'green' | 'blue';
}

export default function ProfileDropdown({
  userName = 'User',
  userEmail,
  userPlan = 'FREE',
  onTabChange
}: ProfileDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const email = userEmail || getLoggedInEmail() || 'user@example.com';
  const initials = userName
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'U';

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
      navigate('/login');
    }
  };

  const handleNavigation = (tab: string) => {
    setIsOpen(false);
    if (onTabChange) {
      onTabChange(tab);
    }
  };

  const menuItems: MenuItem[] = [
    {
      label: 'Overview',
      icon: <LayoutDashboard className="menu-icon" />,
      action: () => handleNavigation('overview'),
    },
    {
      label: 'Datasets',
      icon: <Database className="menu-icon" />,
      action: () => handleNavigation('datasets'),
    },
    {
      label: 'Downloads',
      icon: <Download className="menu-icon" />,
      action: () => handleNavigation('downloads'),
    },
    {
      label: 'Account',
      icon: <User className="menu-icon" />,
      action: () => handleNavigation('account'),
    },
    {
      label: 'Billing',
      icon: <CreditCard className="menu-icon" />,
      action: () => handleNavigation('billing'),
      badge: userPlan,
      badgeColor: userPlan === 'PRO' ? 'purple' : userPlan === 'ADMIN' ? 'blue' : 'green',
    },
  ];

  return (
    <div className="profile-dropdown" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        className={`profile-trigger ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <div className="profile-avatar">
          <span className="avatar-initials">{initials}</span>
        </div>
        <ChevronDown className={`chevron-icon ${isOpen ? 'rotated' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="profile-menu">
          {/* User Info Header */}
          <div className="menu-header">
            <div className="header-avatar">
              <span className="avatar-initials">{initials}</span>
            </div>
            <div className="header-info">
              <span className="header-name">{userName}</span>
              <span className="header-email">{email}</span>
            </div>
            {userPlan && (
              <span className={`header-badge badge-${userPlan.toLowerCase()}`}>
                {userPlan}
              </span>
            )}
          </div>

          <div className="menu-divider" />

          {/* Menu Items */}
          <div className="menu-items">
            {menuItems.map((item) => (
              <button
                key={item.label}
                type="button"
                className="menu-item"
                onClick={item.action}
              >
                {item.icon}
                <span className="menu-label">{item.label}</span>
                {item.badge && (
                  <span className={`menu-badge badge-${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="menu-divider" />

          {/* Logout Button */}
          <button
            type="button"
            className="menu-item logout-item"
            onClick={handleLogout}
          >
            <LogOut className="menu-icon" />
            <span className="menu-label">Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}
