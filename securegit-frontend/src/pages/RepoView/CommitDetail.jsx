import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate, useOutletContext } from 'react-router-dom';
import DiffViewer from '../../components/code/DiffViewer';
import { Skeleton } from '../../components/ui/Spinner';
import { Avatar, TimeAgo } from '../../components/shared/SharedComponents';
import Button from '../../components/ui/Button';
import * as commitsApi from '../../api/commits';

export default function CommitDetail() {
  const { commitHash } = useParams();
  const { username, projectName } = useOutletContext();
  const [detail, setDetail] = useState(null);
  const [diff,   setDiff]   = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      commitsApi.getCommit(username, projectName, commitHash),
      commitsApi.getCommitDiff(username, projectName, commitHash),
    ]).then(([d, df]) => {
      setDetail(d.data);
      setDiff(df.data || []);
    }).finally(() => setLoading(false));
  }, [username, projectName, commitHash]);

  const totalAdded   = diff.reduce((s, f) => s + (f.lines_added ?? f.linesAdded ?? 0), 0);
  const totalDeleted = diff.reduce((s, f) => s + (f.lines_deleted ?? f.linesDeleted ?? 0), 0);

  return (
    <div>
      <div style={{ maxWidth: '1000px' }}>
        {/* Breadcrumb */}
        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Link to={`/${username}/${projectName}`} style={{ color: 'var(--color-text-secondary)', textDecoration: 'none' }}>{username}/{projectName}</Link>
          <span>/</span>
          <Link to={`/${username}/${projectName}/commits`} style={{ color: 'var(--color-text-secondary)', textDecoration: 'none' }}>commits</Link>
          <span>/</span>
          <code style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>{commitHash?.slice(0,7)}</code>
        </div>

        {loading ? (
          <>
            <Skeleton height="28px" width="70%" style={{ marginBottom: 'var(--space-4)' }} />
            <Skeleton height="16px" width="40%" style={{ marginBottom: 'var(--space-6)' }} />
          </>
        ) : (
          <>
            <h1 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600', marginBottom: 'var(--space-4)', lineHeight: 'var(--line-height-tight)' }}>
              {detail?.message}
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginBottom: 'var(--space-5)' }}>
              <Avatar username={detail?.author_name} size={24} />
              <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {detail?.author_name}
              </span>
              <TimeAgo dateString={detail?.date} />
            </div>

            {/* Stats bar */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
              padding: 'var(--space-3) var(--space-5)',
              background: 'var(--color-surface)', border: 'var(--border)',
              borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-5)',
              fontSize: 'var(--font-size-sm)',
            }}>
              <span style={{ color: 'var(--color-text-muted)' }}>
                {diff.length} file{diff.length !== 1 ? 's' : ''} changed
              </span>
              <span style={{ color: 'var(--color-success-text)' }}>+{totalAdded}</span>
              <span style={{ color: 'var(--color-error-text)' }}>−{totalDeleted}</span>
              <code style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                {commitHash}
              </code>
            </div>

            {/* Diff */}
            <DiffViewer fileDiffs={diff} />

            {/* Navigation */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginTop: 'var(--space-6)', paddingTop: 'var(--space-4)', borderTop: 'var(--border)',
            }}>
              <Button variant="ghost" size="sm">← Previous commit</Button>
              <Link to={`/${username}/${projectName}/commits`}>
                <Button variant="ghost" size="sm">← Back to history</Button>
              </Link>
              <Button variant="ghost" size="sm">Next commit →</Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
