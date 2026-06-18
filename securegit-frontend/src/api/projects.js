import client from './client';

export const listProjects = () => client.get('/projects');

export const createProject = (data) => client.post('/projects', data);

export const getProject = (username, projectName) =>
  client.get(`/projects/${username}/${projectName}`);

export const updateProject = (username, projectName, data) =>
  client.patch(`/projects/${username}/${projectName}`, data);

export const deleteProject = (username, projectName) =>
  client.delete(`/projects/${username}/${projectName}`);

// Collaborators
export const listCollaborators = (username, projectName) =>
  client.get(`/projects/${username}/${projectName}/collaborators`);

export const addCollaborator = (username, projectName, data) =>
  client.post(`/projects/${username}/${projectName}/collaborators`, data);

export const updateCollaborator = (username, projectName, uid, data) =>
  client.patch(`/projects/${username}/${projectName}/collaborators/${uid}`, data);

export const removeCollaborator = (username, projectName, uid) =>
  client.delete(`/projects/${username}/${projectName}/collaborators/${uid}`);

// Repository file tree
export const getTree = (username, projectName, params) =>
  client.get(`/repos/${username}/${projectName}/tree`, { params });

export const getBlob = (username, projectName, params) =>
  client.get(`/repos/${username}/${projectName}/blob`, { params });

export const getReadme = (username, projectName, branch) =>
  client.get(`/repos/${username}/${projectName}/readme`, { params: { branch } });
