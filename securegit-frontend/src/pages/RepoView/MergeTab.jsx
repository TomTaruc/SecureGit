import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Spinner';
import DiffViewer from '../../components/code/DiffViewer';
import useUIStore from '../../store/uiStore';
import * as adminApi from '../../api/admin';
import * as branchesApi from '../../api/branches';
import ErrorBoundary from '../../components/shared/ErrorBoundary';

function MergeTabContent() {
  const { username, projectName, project } = useOutletContext();
  const [branches, setBranches] = useState([]);
  const [base, setBase] = useState(project?.default_branch || 'main');
  const [head, setHead] = useState('');
  const [compareData, setCompareData] = useState(null);
  const [conflicts, setConflicts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [merging, setMerging] = useState(false);
  const [strategy, setStrategy] = useState('ff');

  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError = useUIStore(s => s.toastError);

  const runCompare = async () => {
    if (!head || head === base) return;
    setLoading(true);
    setCompareData(null);
    setConflicts(null);
    try {
      const [compRes, confRes] = await Promise.all([
        adminApi.compareBranches(username, projectName, { base, head }),
        adminApi.checkConflicts(username, projectName, { base, head })
      ]);
      setCompareData(compRes?.data || null);
      setConflicts(confRes?.data || null);
      if (compRes?.data?.fast_forward?.available) {
        setStrategy('ff');
      } else {
        setStrategy('squash');
      }
    } catch (err) {
      console.error("Compare error:", err);
      toastError(err?.response?.data?.message || 'Failed to compare branches');
      setCompareData({}); // Fallback empty object to prevent null crashes
      setConflicts({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { runCompare(); }, [base, head]);

  useEffect(() => {
    branchesApi.listBranches(username, projectName)
      .then(res => setBranches(res?.data || []))
      .catch(err => {
        console.error(err);
        setBranches([]);
      });
  }, [username, projectName]);

  const handleMerge = async () => {
    if (!window.confirm(`Merge ${head} into ${base} using ${strategy} strategy?`)) return;
    setMerging(true);
    try {
      await adminApi.doMerge(username, projectName, { base, head, strategy, message: `Merge ${head} into ${base}` });
      toastSuccess('Merge successful');
      setHead('');
      setCompareData(null);
      setConflicts(null);
    } catch (err) {
      toastError(err?.response?.data?.message || err?.response?.data?.error || 'Merge failed');
    } finally {
      setMerging(false);
    }
  };

  // Safe data access
  const safeBranches = Array.isArray(branches) ? branches : [];
  const safeCompareData = compareData || {};
  const commits = Array.isArray(safeCompareData.commits) ? safeCompareData.commits : [];
  const diffs = Array.isArray(safeCompareData.diff) ? safeCompareData.diff : [];
  const hasConflicts = Boolean(conflicts?.has_conflicts);
  const conflictList = Array.isArray(conflicts?.conflicts) ? conflicts.conflicts : [];
  const ffPossible = safeCompareData?.fast_forward?.available === true;
  const squashPossible = safeCompareData?.squash?.available === true;
  const rebasePossible = safeCompareData?.rebase?.available === true;

  return (
    <div>
      {!project?.can_push ? (
        <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)', background: 'var(--color-surface)', borderRadius: 'var(--radius-md)', border: 'var(--border)' }}>
          You do not have permission to merge branches in this repository.
        </div>
      ) : (
        <div>
          <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Base branch</label>
                <select
                  value={base} onChange={e => setBase(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }}
                >
                  {safeBranches.map((b, i) => <option key={b?.name || i} value={b?.name || ''}>{b?.name || 'Unknown'}</option>)}
                </select>
              </div>
              <span style={{ marginTop: '20px', color: 'var(--color-text-muted)' }}>←</span>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Compare branch</label>
                <select
                  value={head} onChange={e => setHead(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }}
                >
                  <option value="">Select branch...</option>
                  {safeBranches.map((b, i) => <option key={b?.name || i} value={b?.name || ''}>{b?.name || 'Unknown'}</option>)}
                </select>
              </div>
            </div>
          </div>

          {loading && <div style={{ padding: 'var(--space-4)' }}><Skeleton height="40px" style={{ marginBottom: '10px' }}/><Skeleton height="200px" /></div>}

          {!loading && compareData && (
            <div>
              {/* Status Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4) var(--space-5)', background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-5)' }}>
                <div>
                  {hasConflicts ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Badge variant="error">✕ Conflicts Detected</Badge>
                      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Cannot merge automatically.</span>
                    </div>
                  ) : commits.length === 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Badge variant="info">✓ Up to date</Badge>
                      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>There are no commits to merge.</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Badge variant="success">
                        ✓ {ffPossible ? "Fast-forward available" : "Branch diverged: A squash or rebase is required"}
                      </Badge>
                      <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                        {ffPossible ? "This pull request can be safely fast-forwarded without creating a merge commit." : "These branches can be automatically merged using a non-linear strategy."}
                      </span>
                    </div>
                  )}
                </div>

                {commits.length > 0 && !hasConflicts && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                    <select
                      value={strategy} onChange={e => setStrategy(e.target.value)}
                      style={{ padding: '6px 12px', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}
                    >
                      {ffPossible && <option value="ff">Fast-forward</option>}
                      {squashPossible && <option value="squash">Squash and Merge</option>}
                      {rebasePossible && <option value="rebase">Rebase and Merge</option>}
                    </select>
                    <Button variant="success" loading={merging} onClick={handleMerge}>
                      Merge Branch
                    </Button>
                  </div>
                )}
              </div>

              {/* Commits List */}
              {commits.length > 0 && (
                <div style={{ marginBottom: 'var(--space-6)' }}>
                  <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-3)' }}>Commits ({commits.length})</h3>
                  <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                    {commits.map((c, i) => (
                      <div key={c?.hash || i} style={{ padding: 'var(--space-3) var(--space-5)', borderBottom: i < commits.length - 1 ? 'var(--border)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: '500', color: 'var(--color-text-primary)' }}>{c?.message || 'No commit message'}</div>
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{c?.author || 'Unknown'} · {c?.date || ''}</div>
                        </div>
                        <code style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>{c?.short_hash || ''}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Conflict List */}
              {hasConflicts && conflictList.length > 0 && (
                <div style={{ marginBottom: 'var(--space-6)' }}>
                  <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-3)' }}>Conflicting Files</h3>
                  <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-error)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                    {conflictList.map((c, i) => (
                      <div key={i} style={{ borderBottom: i < conflictList.length - 1 ? 'var(--border)' : 'none' }}>
                        <div style={{ padding: 'var(--space-3) var(--space-5)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)', fontWeight: '500' }}>
                          {c?.file || 'Unknown file'}
                        </div>
                        {c?.content && (
                          <pre style={{ margin: 0, padding: 'var(--space-3) var(--space-5)', background: 'var(--color-surface-2)', borderTop: 'var(--border)', fontSize: '11px', color: 'var(--color-text-muted)', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                            {c.content}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Diff */}
              {diffs.length > 0 && (
                <div>
                  <h3 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-3)' }}>Changes</h3>
                  <DiffViewer fileDiffs={diffs} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function MergeTab() {
  return (
    <ErrorBoundary>
      <MergeTabContent />
    </ErrorBoundary>
  );
}
