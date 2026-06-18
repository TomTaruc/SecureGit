import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  withCredentials: true,  // Send httpOnly cookies
  timeout: 30000,
});

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrf_access_token=([^;]+)/);
  return match ? match[1] : null;
}

// Attach CSRF token
client.interceptors.request.use((config) => {
  if (config.method && ['post', 'put', 'patch', 'delete'].includes(config.method.toLowerCase())) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      config.headers['X-CSRF-TOKEN'] = csrfToken;
    }
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
        const match = document.cookie.match(/(?:^|; )csrf_refresh_token=([^;]+)/);
        const refreshCsrf = match ? match[1] : null;
        const headers = refreshCsrf ? { 'X-CSRF-TOKEN': refreshCsrf } : {};
        
        _refreshPromise = axios.post('/api/auth/refresh', {}, { 
          withCredentials: true,
          headers
        })
          .finally(() => { _refreshPromise = null; });
      }
      try {
        await _refreshPromise;
        return client(originalRequest);
      } catch (refreshErr) {
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(err);
  }
);

export default client;
