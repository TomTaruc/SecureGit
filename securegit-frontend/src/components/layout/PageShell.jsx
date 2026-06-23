import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function PageShell({ children, sidebar }) {
  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      paddingTop: 'var(--nav-height)',
      background: 'var(--color-bg)',
    }}>
      {sidebar && (
        <aside style={{
          width: 'var(--sidebar-width)',
          flexShrink: 0,
          borderRight: 'var(--border)',
          position: 'fixed',
          top: 'var(--nav-height)',
          bottom: 0,
          left: 0,
          overflowY: 'auto',
          background: 'var(--color-surface)',
          padding: 'var(--space-4) 0',
        }}>
          {sidebar}
        </aside>
      )}
      <main style={{
        flex: 1,
        marginLeft: sidebar ? 'var(--sidebar-width)' : 0,
        width: sidebar ? 'calc(100vw - var(--sidebar-width))' : '100%',
        maxWidth: 'none',
        minWidth: 0,
        boxSizing: 'border-box',
        padding: 'var(--space-6)',
        overflowX: 'hidden',
      }}>
        {children}
      </main>
    </div>
  );
}
