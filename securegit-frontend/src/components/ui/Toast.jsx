import React from 'react';
import useUIStore from '../../store/uiStore';

const typeStyles = {
  success: { borderColor: 'var(--color-success)', iconColor: 'var(--color-success-text)', icon: '✓' },
  error:   { borderColor: 'var(--color-error)',   iconColor: 'var(--color-error-text)',   icon: '✕' },
  info:    { borderColor: 'var(--color-border-light)', iconColor: 'var(--color-text-secondary)', icon: 'ℹ' },
};

function ToastItem({ toast }) {
  const removeToast = useUIStore((s) => s.removeToast);
  const t = typeStyles[toast.type] || typeStyles.info;

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)',
      padding: 'var(--space-3) var(--space-4)',
      background: 'var(--color-surface)',
      border: `1px solid ${t.borderColor}`,
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-md)',
      minWidth: '260px', maxWidth: '400px',
      animation: 'slideInRight 200ms ease',
    }}>
      <span style={{ color: t.iconColor, fontWeight: 'bold', flexShrink: 0, lineHeight: '1.4' }}>
        {t.icon}
      </span>
      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)', lineHeight: '1.5', flex: 1 }}>
        {toast.message}
      </span>
      <button
        onClick={() => removeToast(toast.id)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--color-text-muted)', fontSize: '14px', flexShrink: 0, lineHeight: '1.4',
        }}
      >
        ✕
      </button>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(40px); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export default function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts);

  return (
    <div style={{
      position: 'fixed', bottom: 'var(--space-6)', right: 'var(--space-6)',
      display: 'flex', flexDirection: 'column', gap: 'var(--space-2)',
      zIndex: 'var(--z-toast)',
    }}>
      {toasts.map((t) => <ToastItem key={t.id} toast={t} />)}
    </div>
  );
}
