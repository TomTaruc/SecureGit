import client from './client';

export const getProfile = () => client.get('/users/profile');
export const updateProfile = (data) => client.patch('/users/profile', data);
export const changePassword = (data) => client.patch('/users/profile/password', data);
export const searchUsers = (q) => client.get('/users/search', { params: { q } });
