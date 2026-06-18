import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PageShell from '../components/layout/PageShell';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import useAuthStore from '../store/authStore';
import useUIStore from '../store/uiStore';
import * as projectsApi from '../api/projects';

export default function NewProjectPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const toastError = useUIStore(s => s.toastError);

  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [visibility, setVisibility] = useState('private');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.match(/^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/)) {
      return toastError('Invalid project name. Use alphanumeric characters and hyphens only.');
    }
    setLoading(true);
    try {
      await projectsApi.createProject({ project_name: name, description: desc, visibility });
      navigate(`/${user.username}/${name}`);
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div style={{ maxWidth: '600px', margin: '0 auto', paddingTop: 'var(--space-8)' }}>
        <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: '600', marginBottom: 'var(--space-2)' }}>Create a new repository</h1>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-8)' }}>A repository contains all project files, including the revision history.</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 'var(--space-3)' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500', marginBottom: 'var(--space-2)' }}>Owner</label>
              <div style={{ padding: '7px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-secondary)', cursor: 'not-allowed' }}>
                {user?.username}
              </div>
            </div>
            <span style={{ fontSize: 'var(--font-size-xl)', color: 'var(--color-text-muted)', marginBottom: '4px' }}>/</span>
            <div style={{ flex: 2 }}>
              <Input
                label="Repository name"
                id="project-name"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                placeholder="e.g. awesome-project"
              />
            </div>
          </div>

          <Input
            label="Description (optional)"
            id="project-desc"
            value={desc}
            onChange={e => setDesc(e.target.value)}
          />

          <div style={{ borderTop: 'var(--border)', paddingTop: 'var(--space-6)' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500', marginBottom: 'var(--space-4)' }}>Visibility</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <label style={{ display: 'flex', gap: 'var(--space-3)', cursor: 'pointer' }}>
                <input type="radio" name="visibility" value="private" checked={visibility === 'private'} onChange={e => setVisibility(e.target.value)} />
                <div>
                  <div style={{ fontWeight: '500' }}>🔒 Private</div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>You choose who can see and commit to this repository.</div>
                </div>
              </label>
              <label style={{ display: 'flex', gap: 'var(--space-3)', cursor: 'pointer' }}>
                <input type="radio" name="visibility" value="internal" checked={visibility === 'internal'} onChange={e => setVisibility(e.target.value)} />
                <div>
                  <div style={{ fontWeight: '500' }}>🏢 Internal</div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>Anyone logged into SecureGit can view this repository.</div>
                </div>
              </label>
            </div>
          </div>

          <div style={{ borderTop: 'var(--border)', paddingTop: 'var(--space-6)', display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="submit" loading={loading} disabled={!name}>Create repository</Button>
          </div>
        </form>
      </div>
    </PageShell>
  );
}
