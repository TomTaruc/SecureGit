import React, { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import { Avatar } from '../../components/shared/SharedComponents';
import useUIStore from '../../store/uiStore';
import * as projectsApi from '../../api/projects';

export default function AccessTab() {
  const { username, projectName, project } = useOutletContext();
  const [collabs, setCollabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newUserId, setNewUserId] = useState('');
  const [newPerm, setNewPerm] = useState('read');
  const [adding, setAdding] = useState(false);
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError   = useUIStore(s => s.toastError);

  const fetchCollabs = () => {
    setLoading(true);
    projectsApi.listCollaborators(username, projectName)
      .then(res => setCollabs(res.data || []))
      .catch(() => toastError('Failed to load collaborators'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchCollabs(); }, [username, projectName]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newUserId) return;
    setAdding(true);
    try {
      await projectsApi.addCollaborator(username, projectName, { user_id: parseInt(newUserId), permission: newPerm });
      toastSuccess('Collaborator added');
      setNewUserId('');
      fetchCollabs();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to add collaborator');
    } finally {
      setAdding(false);
    }
  };

  const handleUpdate = async (uid, permission) => {
    try {
      await projectsApi.updateCollaborator(username, projectName, uid, { permission });
      toastSuccess('Permission updated');
      fetchCollabs();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to update permission');
    }
  };

  const handleRemove = async (uid) => {
    if (!window.confirm('Remove collaborator?')) return;
    try {
      await projectsApi.removeCollaborator(username, projectName, uid);
      toastSuccess('Collaborator removed');
      fetchCollabs();
    } catch (err) {
      toastError('Failed to remove collaborator');
    }
  };

  const perms = ['read', 'push', 'manage_collaborators', 'manage_settings', 'admin'];

  return (
    <div>
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Add Collaborator</h2>
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>User ID</label>
            <Input type="number" value={newUserId} onChange={e => setNewUserId(e.target.value)} placeholder="e.g. 2" required />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Role</label>
            <select
              value={newPerm} onChange={e => setNewPerm(e.target.value)}
              style={{ width: '100%', padding: '7px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }}
            >
              {perms.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <Button type="submit" loading={adding} disabled={!newUserId}>Add</Button>
        </form>
      </div>

      <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Collaborators</h2>
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 'var(--space-4)' }}><Skeleton height="40px" /></div>
        ) : collabs.length === 0 ? (
          <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>No collaborators added.</div>
        ) : (
          collabs.map((c, i) => (
            <div key={c.user_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4) var(--space-5)', borderBottom: i < collabs.length - 1 ? 'var(--border)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                <Avatar username={`User${c.user_id}`} />
                <div>
                  <div style={{ fontWeight: '500', color: 'var(--color-text-primary)' }}>User ID: {c.user_id}</div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Added {new Date(c.added_at).toLocaleDateString()}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                <select
                  value={c.permission} onChange={e => handleUpdate(c.user_id, e.target.value)}
                  style={{ padding: '4px 8px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }}
                >
                  {perms.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <Button variant="danger" size="sm" onClick={() => handleRemove(c.user_id)}>Remove</Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
