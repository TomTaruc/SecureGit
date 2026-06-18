import client from './client';

export const login = (credentials) =>
  client.post('/auth/login', credentials);

export const register = (credentials) =>
  client.post('/auth/register', credentials);

export const logout = () =>
  client.post('/auth/logout');

export const refresh = () =>
  client.post('/auth/refresh');

export const me = () =>
  client.get('/auth/me');
