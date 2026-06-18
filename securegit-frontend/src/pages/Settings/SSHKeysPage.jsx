import React, { useEffect, useState } from 'react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { Skeleton } from '../../components/ui/Spinner';
import EmptyState from '../../components/ui/EmptyState';
import useUIStore from '../../store/uiStore';
import * as sshKeysApi from '../../api/sshKeys';
import { TimeAgo } from '../../components/shared/SharedComponents';

export default function SSHKeysPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState('');
  const [keyData, setKeyData] = useState('');

  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError = useUIStore(s => s.toastError);

  const fetchKeys = () => {
    setLoading(true);
    sshKeysApi.listKeys()
      .then(r => setKeys(r.data || []))
      .catch(() => toastError('Failed to load SSH keys'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchKeys(); }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!title || !keyData) return;
    setAdding(true);
    try {
      await sshKeysApi.addKey({ title, key_data: keyData });
      toastSuccess('SSH key added');
      setTitle('');
      setKeyData('');
      fetchKeys();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to add SSH key');
    } finally {
      setAdding(false);
    }
  };

  const handleRevoke = async (keyId) => {
    if (!window.confirm('Revoke this SSH key? Any connected devices will lose access immediately.')) return;
    try {
      await sshKeysApi.revokeKey(keyId);
      toastSuccess('SSH key revoked');
      fetchKeys();
    } catch (err) {
      toastError('Failed to revoke SSH key');
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600', marginBottom: 'var(--space-6)', paddingBottom: 'var(--space-4)', borderBottom: 'var(--border)' }}>SSH Keys</h1>

      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-6)', fontSize: 'var(--font-size-sm)' }}>
        These are the SSH keys associated with your account. Keys allow you to securely pull and push code without a password.
      </p>

      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
        <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Add new SSH key</h2>
        <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input label="Title" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Personal MacBook Air" required />
          <Input label="Key" textarea value={keyData} onChange={e => setKeyData(e.target.value)} placeholder="Begins with 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521', 'ssh-ed25519', 'sk-ecdsa-sha2-nistp256@openssh.com', or 'sk-ssh-ed25519@openssh.com'" required style={{ fontFamily: 'var(--font-mono)' }} rows={5} />
          <div style={{ alignSelf: 'flex-start' }}>
            <Button type="submit" loading={adding} disabled={!title || !keyData}>Add SSH key</Button>
          </div>
        </form>
      </div>

      <div style={{ border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 'var(--space-4)' }}><Skeleton height="40px" /></div>
        ) : keys.length === 0 ? (
          <EmptyState title="No SSH keys" description="There are no SSH keys associated with your account." icon="🔑" />
        ) : (
          keys.map((k, i) => (
            <div key={k.key_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-5)', borderBottom: i < keys.length - 1 ? 'var(--border)' : 'none', background: 'var(--color-surface)' }}>
              <div>
                <div style={{ fontWeight: '600', color: 'var(--color-text-primary)', marginBottom: 'var(--space-1)' }}>{k.title}</div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  Fingerprint: <code style={{ fontFamily: 'var(--font-mono)' }}>{k.fingerprint}</code>
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
                  Added on <TimeAgo dateString={k.created_at} />
                </div>
              </div>
              <Button variant="danger" size="sm" onClick={() => handleRevoke(k.key_id)}>Delete</Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
