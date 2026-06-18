import axios from 'axios';

// In-memory token storage (not localStorage for XSS protection)
let _accessToken = null;

export const setAccessToken = (token) => { _accessToken = token; };
export const clearAccessToken = () => { _accessToken = null; };
export const getAccessToken = () => _accessToken;

const client = axios.create({
  baseURL: '/api',
  withCredentials: true,  // Send httpOnly refresh token cookie
  timeout: 30000,
});

// Attach access token from memory
client.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`;
  }
  return config;
});

// Auto-refresh on 401
let _refreshPromise = null;

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;
    if (err.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      // Deduplicate concurrent refresh calls
      if (!_refreshPromise) {
        _refreshPromise = axios.post('/api/auth/refresh', {}, { withCredentials: true })
          .finally(() => { _refreshPromise = null; });
      }
      try {
        await _refreshPromise;
        return client(originalRequest);
      } catch (refreshErr) {
        clearAccessToken();
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(err);
  }
);

export default client;
