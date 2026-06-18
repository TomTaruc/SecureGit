import React, { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import useUIStore from '../../store/uiStore';
import * as branchesApi from '../../api/branches';

export default function BranchesTab() {
  const { username, projectName, project } = useOutletContext();
  const [branches, setBranches] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [newBranch, setNewBranch] = useState('');
  const [creating, setCreating] = useState(false);
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError   = useUIStore(s => s.toastError);

  const fetchBranches = () => {
    setLoading(true);
    branchesApi.listBranches(username, projectName)
      .then(res => setBranches(res.data || []))
      .catch(() => toastError('Failed to load branches'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchBranches(); }, [username, projectName]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newBranch) return;
    setCreating(true);
    try {
      await branchesApi.createBranch(username, projectName, { branch_name: newBranch, from_branch: project.default_branch });
      toastSuccess(`Branch ${newBranch} created`);
      setNewBranch('');
      fetchBranches();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to create branch');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (branchName) => {
    if (!window.confirm(`Delete branch '${branchName}'?`)) return;
    try {
      await branchesApi.deleteBranch(username, projectName, branchName);
      toastSuccess('Branch deleted');
      fetchBranches();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to delete branch');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-6)', alignItems: 'flex-end' }}>
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: 'var(--space-2)', flex: 1, maxWidth: '400px' }}>
          <Input
            id="new-branch"
            placeholder="New branch name"
            value={newBranch}
            onChange={e => setNewBranch(e.target.value)}
            style={{ flex: 1 }}
          />
          <Button type="submit" loading={creating} disabled={!newBranch}>
            Create Branch
          </Button>
        </form>
      </div>

      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        {loading ? (
          [1,2,3].map(i => <div key={i} style={{ padding: 'var(--space-4)' }}><Skeleton height="20px" width="40%" /></div>)
        ) : branches.length === 0 ? (
          <EmptyState title="No branches" description="Create a branch to get started." />
        ) : (
          branches.map((b, i) => (
            <div key={b.name} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: 'var(--space-4) var(--space-5)',
              borderBottom: i < branches.length - 1 ? 'var(--border)' : 'none',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                <span style={{ fontWeight: '500', color: 'var(--color-text-primary)' }}>{b.name}</span>
                {b.is_default && <Badge variant="success">Default</Badge>}
                {b.is_protected && <Badge variant="warning">Protected</Badge>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                {b.hash && (
                  <code style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {b.hash.slice(0, 7)}
                  </code>
                )}
                {!b.is_default && (
                  <Button variant="danger" size="sm" onClick={() => handleDelete(b.name)}>
                    Delete
                  </Button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
