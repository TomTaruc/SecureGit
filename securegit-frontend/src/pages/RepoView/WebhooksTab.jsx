import React, { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import useUIStore from '../../store/uiStore';
import * as webhooksApi from '../../api/webhooks';

export default function WebhooksTab() {
  const { username, projectName } = useOutletContext();
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [name, setName] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [adding, setAdding] = useState(false);
  
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError   = useUIStore(s => s.toastError);

  const fetchWebhooks = () => {
    setLoading(true);
    webhooksApi.listWebhooks(username, projectName)
      .then(res => setWebhooks(res.data || []))
      .catch(() => toastError('Failed to load webhooks'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchWebhooks(); }, [username, projectName]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!name || !targetUrl) return;
    setAdding(true);
    try {
      await webhooksApi.createWebhook(username, projectName, { name, target_url: targetUrl, secret });
      toastSuccess('Webhook created');
      setName('');
      setTargetUrl('');
      setSecret('');
      fetchWebhooks();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to create webhook');
    } finally {
      setAdding(false);
    }
  };

  const handleUpdate = async (webhookId, field, value) => {
    try {
      await webhooksApi.updateWebhook(username, projectName, webhookId, { [field]: value });
      toastSuccess('Webhook updated');
      fetchWebhooks();
    } catch (err) {
      toastError('Failed to update webhook');
    }
  };

  const handleDelete = async (webhookId) => {
    if (!window.confirm('Delete this webhook?')) return;
    try {
      await webhooksApi.deleteWebhook(username, projectName, webhookId);
      toastSuccess('Webhook deleted');
      fetchWebhooks();
    } catch (err) {
      toastError('Failed to delete webhook');
    }
  };

  const handleTest = async (webhookId) => {
    try {
      const res = await webhooksApi.testWebhook(username, projectName, webhookId);
      if (res.data.delivery_status >= 200 && res.data.delivery_status < 300) {
        toastSuccess(`Webhook test successful (HTTP ${res.data.delivery_status})`);
      } else {
        toastError(`Webhook test failed: ${res.data.error_message || 'HTTP ' + res.data.delivery_status}`);
      }
    } catch (err) {
      toastError('Failed to test webhook');
    }
  };

  return (
    <div>
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Add Webhook</h2>
        <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Name</label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. CI Server" required />
            </div>
            <div style={{ flex: 2, minWidth: '300px' }}>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Payload URL</label>
              <Input value={targetUrl} onChange={e => setTargetUrl(e.target.value)} placeholder="http://10.0.0.5:8080/webhook" type="url" required />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Secret (optional)</label>
              <Input value={secret} onChange={e => setSecret(e.target.value)} placeholder="Webhook secret" type="password" />
            </div>
            <Button type="submit" loading={adding} disabled={!name || !targetUrl}>Add Webhook</Button>
          </div>
        </form>
      </div>

      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 'var(--space-4)' }}><Skeleton height="40px" /></div>
        ) : webhooks.length === 0 ? (
          <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>No webhooks configured.</div>
        ) : (
          webhooks.map((w, i) => (
            <div key={w.webhook_id} style={{ padding: 'var(--space-5)', borderBottom: i < webhooks.length - 1 ? 'var(--border)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <span style={{ fontSize: 'var(--font-size-md)', fontWeight: '500', color: 'var(--color-text-primary)' }}>{w.name}</span>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{w.events.join(', ')}</span>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <Button variant="outline" size="sm" onClick={() => handleTest(w.webhook_id)}>Test</Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(w.webhook_id)}>Delete</Button>
                </div>
              </div>
              
              <div style={{ marginBottom: 'var(--space-3)' }}>
                <code style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>{w.target_url}</code>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                <input type="checkbox" checked={w.is_active} onChange={e => handleUpdate(w.webhook_id, 'is_active', e.target.checked)} />
                Active (receive events)
              </label>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
