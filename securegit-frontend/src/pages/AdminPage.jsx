import React, { useEffect, useState } from 'react';
import PageShell from '../components/layout/PageShell';
import { Skeleton } from '../components/ui/Spinner';
import Badge from '../components/ui/Badge';
import { TimeAgo } from '../components/shared/SharedComponents';
import * as adminApi from '../api/admin';

export default function AdminPage() {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [gitMetrics, setGitMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminApi.systemHealth().catch(() => ({ data: null })),
      adminApi.getMetrics().catch(() => ({ data: null })),
      adminApi.getGitMetrics().catch(() => ({ data: null })),
      adminApi.adminListUsers().catch(() => ({ data: [] }))
    ]).then(([h, m, gm, u]) => {
      setHealth(h.data);
      setMetrics(m.data);
      setGitMetrics(gm.data);
      setUsers(u.data || []);
      setLoading(false);
    });
  }, []);

  return (
    <PageShell>
      <div style={{ maxWidth: '1200px' }}>
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
