import client from './client';

export const listKeys = () => client.get('/ssh-keys');
export const addKey = (data) => client.post('/ssh-keys', data);
export const revokeKey = (keyId) => client.delete(`/ssh-keys/${keyId}`);
