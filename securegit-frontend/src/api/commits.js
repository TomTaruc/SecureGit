import client from './client';

export const listCommits = (username, projectName, params) =>
  client.get(`/commits/${username}/${projectName}`, { params });

export const getCommit = (username, projectName, hash) =>
  client.get(`/commits/${username}/${projectName}/${hash}`);

export const getCommitDiff = (username, projectName, hash) =>
  client.get(`/commits/${username}/${projectName}/${hash}/diff`);
