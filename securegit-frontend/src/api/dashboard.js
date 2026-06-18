import client from './client';

export const getStats     = () => client.get('/dashboard/stats');
export const getActivity  = (limit = 20) => client.get('/dashboard/activity', { params: { limit } });
