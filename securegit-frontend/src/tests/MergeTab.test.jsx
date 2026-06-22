import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MergeTab from '../pages/RepoView/MergeTab';
import * as adminApi from '../api/admin';
import * as branchesApi from '../api/branches';

const mocks = vi.hoisted(() => ({
  useOutletContext: vi.fn()
}));

vi.mock('react-router-dom', () => ({
  useOutletContext: mocks.useOutletContext,
}));
vi.mock('../api/admin', () => ({
  compareBranches: vi.fn(),
  checkConflicts: vi.fn(),
  doMerge: vi.fn()
}));
vi.mock('../api/branches', () => ({
  listBranches: vi.fn()
}));
vi.mock('../store/uiStore', () => ({
  default: vi.fn(() => vi.fn())
}));

describe('MergeTab', () => {
  beforeEach(() => {
    adminApi.compareBranches.mockResolvedValue({ data: {} });
    adminApi.checkConflicts.mockResolvedValue({ data: {} });
    branchesApi.listBranches.mockResolvedValue({ data: [] });
  });

  it('shows permission error if can_push is false', () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_push: false }
    });

    render(<MergeTab />);
    
    expect(screen.getByText(/You do not have permission to merge branches/i)).toBeInTheDocument();
  });

  it('shows merge UI if can_push is true', () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_push: true, default_branch: 'main' }
    });

    render(<MergeTab />);
    
    expect(screen.queryByText(/You do not have permission to merge branches/i)).not.toBeInTheDocument();
    expect(screen.getByText('Base branch')).toBeInTheDocument();
    expect(screen.getByText('Compare branch')).toBeInTheDocument();
  });
});
