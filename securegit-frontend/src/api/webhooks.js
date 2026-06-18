import api from './client';

export const listWebhooks = (username, projectName) =>
  api.get(`/webhooks/${username}/${projectName}`);

export const createWebhook = (username, projectName, data) =>
  api.post(`/webhooks/${username}/${projectName}`, data);

export const updateWebhook = (username, projectName, webhookId, data) =>
  api.patch(`/webhooks/${username}/${projectName}/${webhookId}`, data);

export const deleteWebhook = (username, projectName, webhookId) =>
  api.delete(`/webhooks/${username}/${projectName}/${webhookId}`);

export const testWebhook = (username, projectName, webhookId) =>
  api.post(`/webhooks/${username}/${projectName}/${webhookId}/test`);
