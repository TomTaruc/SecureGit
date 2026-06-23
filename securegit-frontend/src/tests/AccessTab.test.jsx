import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AccessTab from '../pages/RepoView/AccessTab';
import * as projectsApi from '../api/projects';

const mocks = vi.hoisted(() => ({
  useOutletContext: vi.fn()
}));

vi.mock('react-router-dom', () => ({
  useOutletContext: mocks.useOutletContext,
}));
vi.mock('../api/projects', () => ({
  listCollaborators: vi.fn(),
  addCollaborator: vi.fn(),
  updateCollaborator: vi.fn(),
  removeCollaborator: vi.fn()
}));
vi.mock('../api/users', () => ({
  searchUsers: vi.fn()
}));
vi.mock('../store/uiStore', () => ({
  default: vi.fn(() => vi.fn())
}));

describe('AccessTab', () => {
  beforeEach(() => {
    projectsApi.listCollaborators.mockResolvedValue({ data: [] });
  });

  it('read collaborator cannot see role dropdown or remove button', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_manage_collaborators: false }
    });

    render(<AccessTab />);
    
    await waitFor(() => {
      expect(screen.getByText(/You do not have permission to view or manage collaborators/i)).toBeInTheDocument();
      expect(screen.queryByText('Add Collaborator')).not.toBeInTheDocument();
    });
  });

  it('manager can see add collaborator and remove button', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_manage_collaborators: true }
    });
    projectsApi.listCollaborators.mockResolvedValue({ data: [{ user_id: 1, username: 'user1', permission: 'read', granted_at: new Date().toISOString() }] });

    render(<AccessTab />);
    
    expect(screen.getByRole('heading', { name: 'Add Collaborator' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Remove')).toBeInTheDocument();
    });
  });
});
