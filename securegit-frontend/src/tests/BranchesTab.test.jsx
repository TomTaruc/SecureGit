import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BranchesTab from '../pages/RepoView/BranchesTab';
import * as branchesApi from '../api/branches';

const mocks = vi.hoisted(() => ({
  useOutletContext: vi.fn()
}));

vi.mock('react-router-dom', () => ({
  useOutletContext: mocks.useOutletContext,
}));
vi.mock('../api/branches', () => ({
  listBranches: vi.fn(),
  createBranch: vi.fn(),
  deleteBranch: vi.fn(),
}));
vi.mock('../store/uiStore', () => ({
  default: vi.fn(() => vi.fn())
}));

describe('BranchesTab', () => {
  beforeEach(() => {
    branchesApi.listBranches.mockResolvedValue({ data: [] });
  });

  it('shows branch creation input if can_create_branch is true', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_create_branch: true, can_delete_branch: true, default_branch: 'main' }
    });
    branchesApi.listBranches.mockResolvedValue({ data: [{ name: 'main', is_default: true, hash: '123' }] });

    render(<BranchesTab />);
    
    expect(screen.getByPlaceholderText('New branch name')).toBeInTheDocument();
    expect(screen.getByText('Create Branch')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('main')).toBeInTheDocument();
    });
  });

  it('hides branch creation input if can_create_branch is false', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_create_branch: false, can_delete_branch: false }
    });
    branchesApi.listBranches.mockResolvedValue({ data: [] });

    render(<BranchesTab />);
    
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('New branch name')).not.toBeInTheDocument();
    });
  });
});
