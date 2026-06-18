import React, { useState } from 'react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import useAuthStore from '../../store/authStore';
import useUIStore from '../../store/uiStore';
import { Avatar } from '../../components/shared/SharedComponents';

export default function ProfileSettingsPage() {
  const { user } = useAuthStore();
  const [email, setEmail] = useState(user?.email || '');
  const [loading, setLoading] = useState(false);
  const toastSuccess = useUIStore(s => s.toastSuccess);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    // Mock save
    setTimeout(() => {
      toastSuccess('Profile updated successfully');
      setLoading(false);
    }, 500);
  };

  return (
    <div>
      <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600', marginBottom: 'var(--space-6)', paddingBottom: 'var(--space-4)', borderBottom: 'var(--border)' }}>Public profile</h1>

      <div style={{ display: 'flex', gap: 'var(--space-8)', flexWrap: 'wrap-reverse' }}>
        <form onSubmit={handleSubmit} style={{ flex: 2, minWidth: '300px', display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
          <div>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500', marginBottom: 'var(--space-2)' }}>Username</label>
            <div style={{ padding: '7px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-secondary)', cursor: 'not-allowed' }}>
              {user?.username}
            </div>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>Your username cannot be changed.</p>
          </div>

          <Input
            label="Email"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />

          <div>
            <Button type="submit" loading={loading}>Update profile</Button>
          </div>
        </form>

        <div style={{ flex: 1, minWidth: '200px', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 'var(--space-4)' }}>
          <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500' }}>Profile picture</label>
          <div style={{ padding: 'var(--space-4)', border: 'var(--border)', borderRadius: 'var(--radius-md)', display: 'inline-block' }}>
            <Avatar username={user?.username} size={150} />
          </div>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Avatars are automatically generated based on your username.</p>
        </div>
      </div>
    </div>
  );
}
