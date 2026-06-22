import React, { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Skeleton } from '../../components/ui/Spinner';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import useUIStore from '../../store/uiStore';
import * as branchesApi from '../../api/branches';

export default function ProtectionTab() {
  const { username, projectName } = useOutletContext();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pattern, setPattern] = useState('');
  const [adding, setAdding] = useState(false);
  const toastSuccess = useUIStore(s => s.toastSuccess);
  const toastError   = useUIStore(s => s.toastError);

  const fetchRules = () => {
    setLoading(true);
    branchesApi.listProtectionRules(username, projectName)
      .then(res => setRules(res.data || []))
      .catch(() => toastError('Failed to load protection rules'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchRules(); }, [username, projectName]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!pattern) return;
    setAdding(true);
    try {
      const res = await branchesApi.createProtectionRule(username, projectName, { branch_pattern: pattern });
      if (res.data?.warning) {
        toastError(res.data.warning);
      } else {
        toastSuccess('Rule created');
      }
      setPattern('');
      fetchRules();
    } catch (err) {
      toastError(err.response?.data?.message || 'Failed to create rule');
    } finally {
      setAdding(false);
    }
  };

  const handleUpdate = async (ruleId, field, value) => {
    try {
      await branchesApi.updateProtectionRule(username, projectName, ruleId, { [field]: value });
      toastSuccess('Rule updated');
      fetchRules();
    } catch (err) {
      toastError('Failed to update rule');
    }
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm('Delete this rule?')) return;
    try {
      await branchesApi.deleteProtectionRule(username, projectName, ruleId);
      toastSuccess('Rule deleted');
      fetchRules();
    } catch (err) {
      toastError('Failed to delete rule');
    }
  };

  return (
    <div>
      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 'var(--font-size-md)', fontWeight: '600', marginBottom: 'var(--space-4)' }}>Add Protection Rule</h2>
        <form onSubmit={handleAdd} style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, maxWidth: '300px' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Branch pattern</label>
            <Input value={pattern} onChange={e => setPattern(e.target.value)} placeholder="e.g. main, release-*" required />
          </div>
          <Button type="submit" loading={adding} disabled={!pattern}>Add Rule</Button>
        </form>
      </div>

      <div style={{ background: 'var(--color-surface)', border: 'var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 'var(--space-4)' }}><Skeleton height="40px" /></div>
        ) : rules.length === 0 ? (
          <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>No protection rules.</div>
        ) : (
          rules.map((r, i) => (
            <div key={r.rule_id} style={{ padding: 'var(--space-5)', borderBottom: i < rules.length - 1 ? 'var(--border)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                <code style={{ fontSize: 'var(--font-size-md)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>{r.branch_pattern}</code>
                <Button variant="danger" size="sm" onClick={() => handleDelete(r.rule_id)}>Delete Rule</Button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                  <input type="checkbox" checked={r.disable_force_push} onChange={e => handleUpdate(r.rule_id, 'disable_force_push', e.target.checked)} />
                  Disable Force Push
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                  <input type="checkbox" checked={r.disable_deletion} onChange={e => handleUpdate(r.rule_id, 'disable_deletion', e.target.checked)} />
                  Disable Deletion
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                  <input type="checkbox" checked={r.restrict_push} onChange={e => handleUpdate(r.rule_id, 'restrict_push', e.target.checked)} />
                  Restrict Push
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                  <input type="checkbox" checked={r.require_admin_for_push} onChange={e => handleUpdate(r.rule_id, 'require_admin_for_push', e.target.checked)} />
                  Require Admin for Push
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                  <input type="checkbox" checked={r.require_linear_history} onChange={e => handleUpdate(r.rule_id, 'require_linear_history', e.target.checked)} />
                  Require Linear History
                </label>
              </div>
              {r.restrict_push && (
                <div style={{ marginTop: 'var(--space-4)' }}>
                  <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>Allowed push roles (when Restrict Push is enabled)</label>
                  <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                    {['read', 'write', 'admin'].map(role => (
                      <label key={role} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
                        <input
                          type="checkbox"
                          checked={(r.allowed_push_roles || []).includes(role)}
                          onChange={e => {
                            const next = e.target.checked
                              ? [...(r.allowed_push_roles || []), role]
                              : (r.allowed_push_roles || []).filter(x => x !== role);
                            handleUpdate(r.rule_id, 'allowed_push_roles', next);
                          }}
                        />
                        {role}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
