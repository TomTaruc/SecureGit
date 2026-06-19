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

// Auto-refresh on 401 (skip for auth endpoints to avoid loops)
let _refreshPromise = null;
const AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/logout', '/auth/refresh'];

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;

    // Network / timeout errors
    if (!err.response) {
      err.message = 'Network error. Please check your connection and try again.';
      return Promise.reject(err);
    }

    // Rate limit
    if (err.response.status === 429) {
      const msg = err.response.data?.message || 'Too many requests. Please wait a moment and try again.';
      err.response.data = { ...err.response.data, message: msg };
      return Promise.reject(err);
    }

    // Don't try to refresh if the failing request is itself an auth endpoint
    const requestPath = originalRequest.url || '';
    const isAuthPath = AUTH_PATHS.some(p => requestPath.includes(p));

    if (err.response.status === 401 && !originalRequest._retry && !isAuthPath) {
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
        // Only redirect if not already on login page
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(err);
  }
);

export default client;
