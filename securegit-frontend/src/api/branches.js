import client from './client';

export const listBranches = (username, projectName) =>
  client.get(`/branches/${username}/${projectName}`);

export const createBranch = (username, projectName, data) =>
  client.post(`/branches/${username}/${projectName}`, data);

export const deleteBranch = (username, projectName, branchName) =>
  client.delete(`/branches/${username}/${projectName}/${branchName}`);

// Protection rules
export const listProtectionRules = (username, projectName) =>
  client.get(`/branches/${username}/${projectName}/protection`);

export const createProtectionRule = (username, projectName, data) =>
  client.post(`/branches/${username}/${projectName}/protection`, data);

export const updateProtectionRule = (username, projectName, ruleId, data) =>
  client.patch(`/branches/${username}/${projectName}/protection/${ruleId}`, data);

export const deleteProtectionRule = (username, projectName, ruleId) =>
  client.delete(`/branches/${username}/${projectName}/protection/${ruleId}`);
