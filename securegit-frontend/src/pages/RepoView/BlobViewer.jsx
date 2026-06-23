import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageShell from '../../components/layout/PageShell';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import { CopyButton } from '../../components/shared/SharedComponents';
import * as projectsApi from '../../api/projects';

export default function BlobViewer() {
  const { username, projectName, '*': filePath } = useParams();
  const [blobData, setBlobData] = useState(null);
  const [branch,   setBranch]   = useState('');
  const [loading,  setLoading]  = useState(true);
  const navigate = useNavigate();

  // Extract branch from path (e.g. main/src/file.py)
  const parts    = filePath?.split('/') || [];
  const branchFromPath = parts[0] || 'main';
  const actualPath     = parts.slice(1).join('/');

  useEffect(() => {
    setBranch(branchFromPath);
    setLoading(true);
    projectsApi.getBlob(username, projectName, { branch: branchFromPath, path: actualPath })
      .then(r => setBlobData(r.data))
      .catch(() => navigate('/404'))
      .finally(() => setLoading(false));
  }, [username, projectName, filePath]);

  const lineCount = blobData?.content?.split('\n').length || 0;
  const sizeKB = blobData?.size ? (blobData.size / 1024).toFixed(1) : '0';

  return (
    <PageShell>
      <div style={{ width: '100%', maxWidth: 'none' }}>
        {/* File info header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'var(--color-surface)', border: 'var(--border)',
          borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
          padding: 'var(--space-3) var(--space-5)',
          borderBottom: 'none',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <code style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)', fontWeight: '500' }}>
              {actualPath}
            </code>
            {!loading && (
              <>
                <Badge variant="default">{blobData?.language}</Badge>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {lineCount} lines · {sizeKB} KB
                </span>
              </>
            )}
          </div>
          {!loading && blobData?.content && (
            <CopyButton text={blobData.content} label="Copy" />
          )}
        </div>

        {/* File content */}
        <div style={{
          background: 'var(--color-surface)', border: 'var(--border)',
          borderRadius: '0 0 var(--radius-md) var(--radius-md)',
          overflow: 'auto',
        }}>
          {loading ? (
            <div style={{ padding: 'var(--space-6)' }}>
              {[...Array(8)].map((_, i) => <Skeleton key={i} height="18px" width={`${50 + Math.random() * 40}%`} style={{ marginBottom: '6px' }} />)}
            </div>
          ) : blobData?.is_binary ? (
            <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              Binary file — cannot display as text.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
              <tbody>
                {(blobData?.content || '').split('\n').map((line, i) => (
                  <tr key={i} id={`L${i+1}`} style={{ lineHeight: '20px' }}>
                    <td style={{
                      width: '50px', padding: '0 12px',
                      textAlign: 'right', verticalAlign: 'top',
                      color: 'var(--color-text-muted)',
                      userSelect: 'none', borderRight: 'var(--border)',
                      fontSize: 'var(--font-size-xs)',
                    }}>
                      {i + 1}
                    </td>
                    <td style={{
                      padding: '0 16px',
                      color: 'var(--color-text-primary)',
                      whiteSpace: 'pre',
                      verticalAlign: 'top',
                    }}>
                      {line || ' '}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </PageShell>
  );
}
