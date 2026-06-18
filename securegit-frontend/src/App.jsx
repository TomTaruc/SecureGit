import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import useAuthStore from './store/authStore';
import ToastContainer from './components/ui/Toast';
import TopNav from './components/layout/TopNav';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ProjectsPage from './pages/ProjectsPage';
import NewProjectPage from './pages/NewProjectPage';
import AdminPage from './pages/AdminPage';

// Repo Pages
import RepoLayout from './pages/RepoView/RepoLayout';
import CodeTab from './pages/RepoView/CodeTab';
import CommitsTab from './pages/RepoView/CommitsTab';
import CommitDetail from './pages/RepoView/CommitDetail';
import BranchesTab from './pages/RepoView/BranchesTab';
import AccessTab from './pages/RepoView/AccessTab';
import MergeTab from './pages/RepoView/MergeTab';
import ProtectionTab from './pages/RepoView/ProtectionTab';
import BlobViewer from './pages/RepoView/BlobViewer';

import WebhooksTab from './pages/RepoView/WebhooksTab';

// Settings Pages
import SettingsLayout from './pages/Settings/SettingsLayout';
import ProfileSettingsPage from './pages/Settings/ProfileSettingsPage';
import SSHKeysPage from './pages/Settings/SSHKeysPage';

function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthenticated, user, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) return null; // Or a full screen spinner
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (adminOnly && user?.role !== 'admin') return <Navigate to="/dashboard" replace />;

  return (
    <>
      <TopNav />
      {children}
    </>
  );
}

export default function App() {
  const { fetchMe, isAuthenticated } = useAuthStore();
  const [init, setInit] = useState(false);

  useEffect(() => {
    // Attempt to restore session on load
    fetchMe().finally(() => setInit(true));
  }, []);

  if (!init) return null;

  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />

        {/* Protected general routes */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
        <Route path="/projects/new" element={<ProtectedRoute><NewProjectPage /></ProtectedRoute>} />

        {/* Settings */}
        <Route path="/settings" element={<ProtectedRoute><SettingsLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<ProfileSettingsPage />} />
          <Route path="ssh-keys" element={<SSHKeysPage />} />
          <Route path="account" element={<div style={{ padding: 'var(--space-6)' }}>Account settings coming soon.</div>} />
        </Route>

        {/* Admin only */}
        <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>} />

        {/* Repository routes */}
        <Route path="/:username/:projectName" element={<ProtectedRoute><RepoLayout /></ProtectedRoute>}>
          <Route index element={<CodeTab />} />
          <Route path="commits" element={<CommitsTab />} />
          <Route path="commit/:commitHash" element={<CommitDetail />} />
          <Route path="branches" element={<BranchesTab />} />
          <Route path="access" element={<AccessTab />} />
          <Route path="merge" element={<MergeTab />} />
          <Route path="protection" element={<ProtectionTab />} />
          <Route path="webhooks" element={<WebhooksTab />} />
          <Route path="blob/*" element={<BlobViewer />} />
        </Route>

        {/* Default catch-all */}
        <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
        <Route path="*" element={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-muted)' }}>404 Not Found</div>} />
      </Routes>
    </BrowserRouter>
  );
}
