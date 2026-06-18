import React, { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Pagination from '../../components/ui/Pagination';
import EmptyState from '../../components/ui/EmptyState';
import { TimeAgo } from '../../components/shared/SharedComponents';
import Input from '../../components/ui/Input';
import * as commitsApi from '../../api/commits';
import { format } from 'date-fns';

export default function CommitsTab() {
  const { username, projectName, branch } = useOutletContext();
  const [commits, setCommits]   = useState([]);
  const [total,   setTotal]     = useState(0);
  const [page,    setPage]      = useState(1);
  const [pages,   setPages]     = useState(1);
  const [loading, setLoading]   = useState(true);
  const [search,  setSearch]    = useState('');

  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setLoading(true);
    commitsApi.listCommits(username, projectName, { branch, page, per_page: 30, query: debouncedSearch })
      .then(r => {
        setCommits(r.data.commits || []);
        setTotal(r.data.total || 0);
        setPages(r.data.total_pages || 1);
      })
      .finally(() => setLoading(false));
  }, [username, projectName, branch, page, debouncedSearch]);

  // Group by date
  const grouped = {};
  commits.forEach(c => {
    const day = c.date ? c.date.split('T')[0] : 'Unknown';
    if (!grouped[day]) grouped[day] = [];
    grouped[day].push(c);
  });

  return (
    <div>
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <Input
          id="commit-search"
          placeholder="Search commits by message or hash..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        [1,2,3].map(i => <Skeleton key={i} height="68px" style={{ marginBottom: 'var(--space-2)' }} />)
      ) : commits.length === 0 ? (
        <EmptyState icon="📝" title="No commits yet" description="Push your first commit to see it here." />
      ) : (
        <>
          {Object.entries(grouped).map(([day, dayCommits]) => (
            <div key={day} style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{
                fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)',
                textTransform: 'uppercase', letterSpacing: '0.08em',
                padding: 'var(--space-2) 0', marginBottom: 'var(--space-2)',
              }}>
                COMMITS ON {day}
              </div>
              <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                {dayCommits.map((c, i) => (
                  <div key={c.hash} style={{
                    display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
                    padding: 'var(--space-3) var(--space-5)',
                    borderBottom: i < dayCommits.length - 1 ? 'var(--border)' : 'none',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Link
                        to={`/${username}/${projectName}/commit/${c.hash}`}
                        style={{ fontWeight: '500', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)', textDecoration: 'none' }}
                        onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                        onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
                      >
                        {c.message}
                      </Link>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                        {c.author_name} · <TimeAgo dateString={c.date} />
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
                      <code style={{
                        fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)',
                        background: 'var(--color-surface-2)', border: 'var(--border)',
                        borderRadius: 'var(--radius-sm)', padding: '2px 8px',
                        color: 'var(--color-text-muted)',
                      }}>
                        {c.short_hash}
                      </code>
                      <Link
                        to={`/${username}/${projectName}/commit/${c.hash}`}
                        style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', border: 'var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px 8px', textDecoration: 'none' }}
                      >
                        View diff
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <Pagination page={page} totalPages={pages} onPage={setPage} />
        </>
      )}
    </div>
  );
}
