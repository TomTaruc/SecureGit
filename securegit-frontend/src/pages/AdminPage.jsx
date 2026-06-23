import React, { useEffect, useState } from 'react';
import PageShell from '../components/layout/PageShell';
import { Skeleton } from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import { TimeAgo } from '../components/shared/SharedComponents';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import useUIStore from '../store/uiStore';
import * as adminApi from '../api/admin';

export default function AdminPage() {
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError = useUIStore(s => s.toastError);
  
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [gitMetrics, setGitMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [config, setConfig] = useState({});
  const [savingConfig, setSavingConfig] = useState(false);
  const [backupFiles, setBackupFiles] = useState([]);
  const [backupJobs, setBackupJobs] = useState([]);
  const [triggeringBackup, setTriggeringBackup] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchBackups = () => {
    adminApi.listBackupFiles().then(res => setBackupFiles(res.data)).catch(() => {});
    adminApi.listBackupJobs().then(res => setBackupJobs(res.data)).catch(() => {});
  };

  useEffect(() => {
    Promise.all([
      adminApi.systemHealth().catch(() => ({ data: null })),
      adminApi.getMetrics().catch(() => ({ data: null })),
      adminApi.getGitMetrics().catch(() => ({ data: null })),
      adminApi.adminListUsers().catch(() => ({ data: [] })),
      adminApi.getConfig().catch(() => ({ data: [] }))
    ]).then(([h, m, gm, u, c]) => {
      setHealth(h.data);
      setMetrics(m.data);
      setGitMetrics(gm.data);
      setUsers(u.data || []);
      
      const confMap = {};
      if (c.data) c.data.forEach(item => confMap[item.key] = item.value);
      setConfig(confMap);
      
      fetchBackups();
      setLoading(false);
    });
  }, []);

  const handleConfigSave = async (e) => {
    e.preventDefault();
    setSavingConfig(true);
    try {
      await adminApi.updateConfig(config);
      toastSuccess('Configuration saved');
    } catch (err) {
      toastError('Failed to save configuration');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleTriggerBackup = async () => {
    setTriggeringBackup(true);
    try {
      await adminApi.triggerBackup({});
      toastSuccess('Backup started');
      setTimeout(fetchBackups, 2000);
    } catch (err) {
      toastError('Failed to start backup');
    } finally {
      setTriggeringBackup(false);
    }
  };

  const handleRestore = async (filename) => {
    if (!window.confirm(`Are you sure you want to restore ${filename}? This may overwrite existing data.`)) return;
    try {
      await adminApi.adminRestore({ filename });
      toastSuccess(`Restore started for ${filename}`);
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to start restore');
    }
  };

  return (
    <PageShell>
      <div style={{ width: '100%', maxWidth: 'none' }}>
        <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: '600', marginBottom: 'var(--space-6)' }}>Site Administration</h1>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
          {/* Health */}
          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-5)' }}>
            <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>System Services</h2>
            {loading ? <Skeleton height="100px" /> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {health?.services?.map(s => (
                  <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>{s.name}</span>
                    <Badge variant={s.status === 'running' || s.status === 'connected' ? 'success' : 'error'}>{s.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Metrics */}
          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-5)' }}>
            <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Server Metrics</h2>
            {loading ? <Skeleton height="100px" /> : metrics?.cpu_percent != null ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <MetricBar label={`CPU (${metrics.cpu_percent}%)`} percent={metrics.cpu_percent} />
                <MetricBar label={`RAM (${metrics.memory?.used_gb} / ${metrics.memory?.total_gb} GB)`} percent={metrics.memory?.percent} />
                <MetricBar label={`Disk (${metrics.disk?.used_gb} / ${metrics.disk?.total_gb} GB)`} percent={metrics.disk?.percent} />
              </div>
            ) : <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>Metrics not available (psutil missing).</div>}
          </div>

          {/* Git Stats */}
          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-5)' }}>
            <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Git Usage</h2>
            {loading ? <Skeleton height="100px" /> : gitMetrics ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Repositories</span>
                  <span style={{ fontWeight: '600' }}>{gitMetrics.total_repositories}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Commits</span>
                  <span style={{ fontWeight: '600' }}>{gitMetrics.total_commits}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Disk Size (/srv/git)</span>
                  <span style={{ fontWeight: '600' }}>{gitMetrics.repos_dir_size_gb} GB</span>
                </div>
              </div>
            ) : <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>Git metrics not available.</div>}
          </div>
        </div>

        {/* Configuration */}
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Global Configuration</h2>
        <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
          {loading ? <Skeleton height="150px" /> : (
            <form onSubmit={handleConfigSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '250px' }}>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500', marginBottom: '4px' }}>Storage Quota (MB)</label>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>Default repository storage limit per user/project.</div>
                  <Input 
                    type="number" 
                    value={config.storage_quota_mb || ''} 
                    onChange={e => setConfig(prev => ({ ...prev, storage_quota_mb: e.target.value }))} 
                  />
                </div>
                <div style={{ flex: 1, minWidth: '250px' }}>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: '500', marginBottom: '4px' }}>Max File Size (MB)</label>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>Maximum file size allowed per push.</div>
                  <Input 
                    type="number" 
                    value={config.max_file_size_mb || ''} 
                    onChange={e => setConfig(prev => ({ ...prev, max_file_size_mb: e.target.value }))} 
                  />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button type="submit" loading={savingConfig}>Save Configuration</Button>
              </div>
            </form>
          )}
        </div>

        {/* Backups */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600' }}>Backups & Restore</h2>
          <Button onClick={handleTriggerBackup} loading={triggeringBackup}>Run Full Backup</Button>
        </div>
        <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
          {loading ? <Skeleton height="150px" /> : (
            <>
              <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '500', marginBottom: 'var(--space-3)' }}>Available Archives</h3>
              {backupFiles.length === 0 ? (
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>No backup archives found in destination.</div>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  {backupFiles.map(f => (
                    <li key={f.filename} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-3)', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-sm)' }}>
                      <div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>{f.filename}</div>
                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          {(f.size_bytes / 1024 / 1024).toFixed(2)} MB • Modified: {new Date(f.modified_at).toLocaleString()}
                        </div>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => handleRestore(f.filename)}>Restore</Button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>

        {/* Users */}
        <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Users</h2>
        <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
            <thead style={{ background: 'var(--color-surface-2)' }}>
              <tr>
                <th style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: 'var(--border)', fontWeight: '500' }}>ID</th>
                <th style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: 'var(--border)', fontWeight: '500' }}>Username</th>
                <th style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: 'var(--border)', fontWeight: '500' }}>Role</th>
                <th style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: 'var(--border)', fontWeight: '500' }}>Status</th>
                <th style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: 'var(--border)', fontWeight: '500' }}>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={u.user_id} style={{ borderBottom: i < users.length - 1 ? 'var(--border)' : 'none' }}>
                  <td style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-text-muted)' }}>{u.user_id}</td>
                  <td style={{ padding: 'var(--space-3) var(--space-4)', fontWeight: '500' }}>{u.username}</td>
                  <td style={{ padding: 'var(--space-3) var(--space-4)' }}><Badge variant={u.role === 'admin' ? 'warning' : 'default'}>{u.role}</Badge></td>
                  <td style={{ padding: 'var(--space-3) var(--space-4)' }}>{u.is_suspended ? <Badge variant="error">Suspended</Badge> : <Badge variant="success">Active</Badge>}</td>
                  <td style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-text-muted)' }}><TimeAgo dateString={u.created_at} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageShell>
  );
}

function MetricBar({ label, percent = 0 }) {
  const isHigh = percent > 85;
  const color = isHigh ? 'var(--color-error)' : 'var(--color-text-primary)';
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', marginBottom: '4px', color: 'var(--color-text-secondary)' }}>
        {label}
      </div>
      <div style={{ height: '6px', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.min(100, Math.max(0, percent))}%`, background: color, transition: 'width 0.5s ease' }} />
      </div>
    </div>
  );
}
