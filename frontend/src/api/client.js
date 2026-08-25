import axios from 'axios';

// const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const BASE_URL = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || err.message || 'Unknown error';
    console.error(`[API] ${err.config?.method?.toUpperCase()} ${err.config?.url} → ${message}`);
    err.message = message; // annotate in place — keep err.response/err.config intact
    return Promise.reject(err);
  }
);

// export const WS_URL = BASE_URL.replace(/^http/, 'ws');
export const WS_URL = (BASE_URL || window.location.origin).replace(/^http/, 'ws');