import React, { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import { Avatar } from '../../components/shared/SharedComponents';
import useUIStore from '../../store/uiStore';
import * as projectsApi from '../../api/projects';
import * as usersApi from '../../api/users';

export default function AccessTab() {
  const { username, projectName, project } = useOutletContext();
  const [collabs, setCollabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newUserId, setNewUserId] = useState('');
  const [newPerm, setNewPerm] = useState('read');
  const [adding, setAdding] = useState(false);
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError   = useUIStore(s => s.toastError);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const fetchCollabs = () => {
    setLoading(true);
    projectsApi.listCollaborators(username, projectName)
      .then(res => setCollabs(res.data || []))
      .catch(() => toastError('Failed to load collaborators'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchCollabs(); }, [username, projectName]);

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setSearching(true);
      usersApi.searchUsers(searchQuery)
        .then(res => setSearchResults(res.data || []))
        .catch(() => {})
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newUserId) return;
    setAdding(true);
    try {
      await projectsApi.addCollaborator(username, projectName, { user_id: parseInt(newUserId), permission: newPerm });
      toastSuccess('Collaborator added');
      setNewUserId('');
      setSearchQuery('');
      setSearchResults([]);
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

  const perms = ['read', 'write', 'admin'];
  const canManage = project?.can_manage_collaborators === true;

  if (!canManage) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)', background: 'var(--color-surface)', borderRadius: 'var(--radius-md)', border: 'var(--border)' }}>
        You do not have permission to view or manage collaborators in this repository.
      </div>
    );
  }

  return (
    <div>
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Add Collaborator</h2>
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Search User</label>
            <Input 
              type="text" 
              value={searchQuery} 
              onChange={e => {
                setSearchQuery(e.target.value);
                if (newUserId && e.target.value !== searchQuery) setNewUserId('');
              }} 
              placeholder="Type username..." 
            />
            {searchResults.length > 0 && !newUserId && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'var(--color-surface-2)', border: 'var(--border)', borderRadius: 'var(--radius-md)', marginTop: '4px', zIndex: 10, maxHeight: '200px', overflowY: 'auto' }}>
                {searchResults.map(u => (
                  <div 
                    key={u.user_id} 
                    onClick={() => {
                      setNewUserId(u.user_id);
                      setSearchQuery(u.username);
                      setSearchResults([]);
                    }}
                    style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '10px' }}
                  >
                    <Avatar username={u.username} size={24} />
                    <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{u.username}</span>
                  </div>
                ))}
              </div>
            )}
            {newUserId && <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-success)', marginTop: '4px' }}>User Selected (ID: {newUserId})</div>}
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
          <div style={{ paddingTop: '22px' }}>
            <Button type="submit" loading={adding} disabled={!newUserId}>Add</Button>
          </div>
        </form>
      </div>
      )}

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
                <Avatar username={c.username || `User${c.user_id}`} />
                <div>
                  <div style={{ fontWeight: '500', color: 'var(--color-text-primary)' }}>{c.username || `User ID: ${c.user_id}`}</div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Added {new Date(c.granted_at).toLocaleDateString()}</div>
                </div>
              </div>
              {canManage ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                  <select
                    value={c.permission} onChange={e => handleUpdate(c.user_id, e.target.value)}
                    style={{ padding: '4px 8px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }}
                  >
                    {perms.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                  <Button variant="danger" size="sm" onClick={() => handleRemove(c.user_id)}>Remove</Button>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                  <Badge variant="outline">{c.permission}</Badge>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
