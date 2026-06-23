import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import PageShell from '../../components/layout/PageShell';

export default function SettingsLayout() {
  const navItems = [
    { to: '/settings/profile', label: 'Profile' },
    { to: '/settings/ssh-keys', label: 'SSH Keys' },
    { to: '/settings/account', label: 'Account' },
  ];

  const sidebar = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '0 var(--space-3)' }}>
      <div style={{ padding: 'var(--space-2) var(--space-3)', fontSize: 'var(--font-size-xs)', fontWeight: '600', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 'var(--space-2)' }}>
        User Settings
      </div>
      {navItems.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          style={({ isActive }) => ({
            display: 'block', padding: 'var(--space-2) var(--space-3)',
            fontSize: 'var(--font-size-sm)', textDecoration: 'none',
            color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            background: isActive ? 'var(--color-surface-2)' : 'transparent',
            borderRadius: 'var(--radius-md)',
            transition: 'background var(--transition-fast)',
            fontWeight: isActive ? '500' : '400',
          })}
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );

  return (
    <PageShell sidebar={sidebar}>
      <div style={{ width: '100%', maxWidth: 'none' }}>
        <Outlet />
      </div>
    </PageShell>
  );
}
