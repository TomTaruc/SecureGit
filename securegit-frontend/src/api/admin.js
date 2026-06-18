import client from './client';

// Users
export const adminListUsers   = ()           => client.get('/admin/users');
export const adminCreateUser  = (data)       => client.post('/admin/users', data);
export const adminUpdateUser  = (id, data)   => client.patch(`/admin/users/${id}`, data);
export const adminDeleteUser  = (id)         => client.delete(`/admin/users/${id}`);

// System
export const systemHealth     = ()           => client.get('/admin/system/health');

// Projects & SSH keys
export const adminAllProjects = ()           => client.get('/admin/projects');
export const adminAllSSHKeys  = ()           => client.get('/admin/ssh-keys');

// Audit log
export const adminAuditLog    = (params)     => client.get('/admin/audit-log', { params });
export const adminChrootJails = ()           => client.get('/admin/chroot-jails');

// Config
export const getConfig        = ()           => client.get('/admin/config');
export const updateConfig     = (data)       => client.patch('/admin/config', data);

// Metrics
export const getMetrics       = ()           => client.get('/admin/metrics');
export const getGitMetrics    = ()           => client.get('/admin/metrics/git');

// Backups
export const listBackupJobs   = ()           => client.get('/backups');
export const triggerBackup    = (data)       => client.post('/backups', data);
export const listBackupFiles  = (dest)       => client.get('/backups/files', { params: { dest } });

// Merge
export const compareBranches  = (u, p, params) => client.get(`/merge/${u}/${p}/compare`, { params });
export const checkConflicts   = (u, p, params) => client.get(`/merge/${u}/${p}/conflicts`, { params });
export const doMerge          = (u, p, data)   => client.post(`/merge/${u}/${p}/merge`, data);
