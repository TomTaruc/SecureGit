import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import WebhooksTab from '../pages/RepoView/WebhooksTab';
import * as webhooksApi from '../api/webhooks';

const mocks = vi.hoisted(() => ({
  useOutletContext: vi.fn()
}));

vi.mock('react-router-dom', () => ({
  useOutletContext: mocks.useOutletContext,
}));
vi.mock('../api/webhooks', () => ({
  listWebhooks: vi.fn(),
  createWebhook: vi.fn(),
  updateWebhook: vi.fn(),
  deleteWebhook: vi.fn(),
  testWebhook: vi.fn()
}));
vi.mock('../store/uiStore', () => ({
  default: vi.fn(() => vi.fn())
}));

describe('WebhooksTab', () => {
  beforeEach(() => {
    webhooksApi.listWebhooks.mockResolvedValue({ data: [] });
  });

  it('shows permission error if can_manage_settings is false', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_manage_settings: false }
    });

    render(<WebhooksTab />);
    
    await waitFor(() => {
      expect(screen.getByText(/You do not have permission to view or manage webhooks/i)).toBeInTheDocument();
    });
  });

  it('shows webhooks if can_manage_settings is true', async () => {
    mocks.useOutletContext.mockReturnValue({
      username: 'owner',
      projectName: 'test',
      project: { can_manage_settings: true }
    });
    webhooksApi.listWebhooks.mockResolvedValue({ data: [{ webhook_id: 1, name: 'CI', target_url: 'http://test.com', events: ['push'], is_active: true }] });

    render(<WebhooksTab />);
    
    expect(screen.getByRole('button', { name: 'Add Webhook' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('CI')).toBeInTheDocument();
      expect(screen.getByText('http://test.com')).toBeInTheDocument();
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });
});
