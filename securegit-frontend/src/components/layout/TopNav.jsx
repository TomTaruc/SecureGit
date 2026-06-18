import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../../store/authStore';
import { Avatar } from '../shared/SharedComponents';

export default function TopNav() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [dropOpen, setDropOpen] = useState(false);
  const dropRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) setDropOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0,
      height: 'var(--nav-height)',
      background: 'var(--color-surface)',
      borderBottom: 'var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 var(--space-6)',
      gap: 'var(--space-8)',
      zIndex: 'var(--z-nav)',
    }}>
      {/* Logo */}
      <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', textDecoration: 'none' }}>
        <div style={{
          width: '36px', height: '36px',
          border: '1px solid var(--color-border-light)',
          borderRadius: 'var(--radius-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-mono)', fontWeight: '700',
          fontSize: '14px', color: 'var(--color-white)',
          background: 'var(--color-surface-2)',
          letterSpacing: '-0.5px',
        }}>
          SG
        </div>
        <span style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', color: 'var(--color-text-primary)' }}>
          SecureGit
        </span>
      </Link>

      {/* Navigation links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/projects">Projects</NavLink>
        {user?.role === 'admin' && <NavLink to="/admin">Admin</NavLink>}
      </div>

      {/* Right side */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
        <div ref={dropRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setDropOpen(!dropOpen)}
            style={{
              display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
              background: 'none', border: 'none', cursor: 'pointer',
              padding: 'var(--space-1)',
            }}
          >
            <Avatar username={user?.username} size={28} />
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
              {user?.username}
            </span>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>▾</span>
          </button>

          {dropOpen && (
            <div style={{
              position: 'absolute', right: 0, top: 'calc(100% + 8px)',
              background: 'var(--color-surface)',
              border: 'var(--border)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-md)',
              minWidth: '160px',
              zIndex: 'var(--z-dropdown)',
              overflow: 'hidden',
              animation: 'fadeIn 100ms ease',
            }}>
              <DropItem to="/settings/profile" onClick={() => setDropOpen(false)}>Profile</DropItem>
              <DropItem to="/settings/ssh-keys" onClick={() => setDropOpen(false)}>SSH Keys</DropItem>
              <DropItem to="/settings/account" onClick={() => setDropOpen(false)}>Settings</DropItem>
              <div style={{ borderTop: 'var(--border)', margin: 'var(--space-1) 0' }} />
              <DropItem onClick={handleLogout} color="var(--color-error-text)">Logout</DropItem>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

function NavLink({ to, children }) {
  const isActive = window.location.pathname === to || window.location.pathname.startsWith(to + '/');
  return (
    <Link to={to} style={{
      padding: 'var(--space-2) var(--space-3)',
      fontSize: 'var(--font-size-sm)',
      fontWeight: '500',
      color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
      borderRadius: 'var(--radius-md)',
      transition: 'color var(--transition-fast), background var(--transition-fast)',
      textDecoration: 'none',
    }}
    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-2)'; }}
    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      {children}
    </Link>
  );
}

function DropItem({ to, onClick, children, color }) {
  const content = (
    <div
      onClick={onClick}
      style={{
        padding: 'var(--space-2) var(--space-4)',
        fontSize: 'var(--font-size-sm)',
        color: color || 'var(--color-text-secondary)',
        cursor: 'pointer',
        transition: 'background var(--transition-fast)',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-2)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      {children}
    </div>
  );
  return to ? <Link to={to} style={{ textDecoration: 'none' }}>{content}</Link> : content;
}
