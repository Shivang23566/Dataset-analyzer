import { useState, useEffect } from 'react';
import type { ToastType } from '../components/Toast';

export interface ToastOptions {
  type: ToastType;
  title: string;
  message: string;
  ctaText?: string;
  onCtaClick?: () => void;
  duration?: number;
}

export interface ToastItem extends ToastOptions {
  id: string;
}

// ── Module-level singleton ─────────────────────────────────────
// All components share the same store so any component can trigger
// a toast and the ToastContainer will see it.
let _store: ToastItem[] = [];
let _subs: Array<(t: ToastItem[]) => void> = [];

function _notify() {
  _subs.forEach((fn) => fn([..._store]));
}

export function showToastGlobal(opts: ToastOptions) {
  const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  _store = [..._store, { ...opts, id }];
  _notify();
}

export function dismissToastGlobal(id: string) {
  _store = _store.filter((t) => t.id !== id);
  _notify();
}

// ── React hook ────────────────────────────────────────────────
export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>(_store);

  useEffect(() => {
    _subs.push(setToasts);
    return () => {
      _subs = _subs.filter((fn) => fn !== setToasts);
    };
  }, []);

  return {
    toasts,
    showToast: showToastGlobal,
    dismissToast: dismissToastGlobal,
  };
}

// Kept for backward compat with ToastContainer import
export function registerToastHandler(_fn: (opts: ToastOptions) => void) {
  // no-op: store is already module-level
}
