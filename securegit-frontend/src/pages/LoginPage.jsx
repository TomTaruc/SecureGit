import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const { login, isLoading }    = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const result = await login({ username, password });
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--color-bg)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-6)',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '380px',
        background: 'var(--color-surface)',
        border: 'var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-8)',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
          <div style={{
            width: '40px', height: '40px',
            border: '1px solid var(--color-border-light)',
            borderRadius: 'var(--radius-md)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--font-mono)', fontWeight: '700', fontSize: '16px',
            color: 'var(--color-white)', background: 'var(--color-surface-2)',
            margin: '0 auto var(--space-4)',
          }}>
            SG
          </div>
          <h1 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--space-1)' }}>
            SecureGit
          </h1>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Self-hosted version control platform
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            id="login-username"
            label="Username or Email"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <Input
            id="login-password"
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <div style={{
              padding: 'var(--space-3) var(--space-4)',
              background: 'var(--color-error-bg)',
              border: '1px solid var(--color-error)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-error-text)',
            }}>
              {error}
            </div>
          )}

          <Button type="submit" fullWidth loading={isLoading} style={{ marginTop: 'var(--space-2)' }}>
            Sign in
          </Button>
        </form>

        {/* SSH hint */}
        <p style={{
          marginTop: 'var(--space-5)',
          textAlign: 'center',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-muted)',
        }}>
          Secure SSH key authentication also available
        </p>

        {/* Sign up link */}
        <p style={{
          marginTop: 'var(--space-4)',
          textAlign: 'center',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--color-text-muted)',
        }}>
          Don't have an account?{' '}
          <a
            href="/register"
            onClick={(e) => { e.preventDefault(); navigate('/register'); }}
            style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: '500' }}
          >
            Create Account
          </a>
        </p>
      </div>

      {/* Footer */}
      <p style={{
        marginTop: 'var(--space-6)',
        fontSize: 'var(--font-size-xs)',
        color: 'var(--color-text-muted)',
        textAlign: 'center',
      }}>
        SecureGit v1.0 — Private Instance — Unauthorized access is prohibited
      </p>
    </div>
  );
}
