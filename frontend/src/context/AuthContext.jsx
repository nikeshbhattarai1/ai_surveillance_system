import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { apiClient } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);  // true on mount = "checking token"

  // On mount: validate any stored token and fetch user profile
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) { setLoading(false); return; }

    apiClient.get('/auth/me')
      .then(({ data }) => setUser(data))
      .catch(() => {
        // Token invalid or expired — clear storage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { data } = await apiClient.post('/auth/login', { email, password });

    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);

    // Fetch full user profile
    const { data: profile } = await apiClient.get('/auth/me');
    setUser(profile);
    return profile;
  }, []);

  const register = useCallback(async (email, password, fullName) => {
    await apiClient.post('/auth/register', {
      email, password, full_name: fullName,
    });
    return login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  }, []);

  // Auto-refresh access token using refresh token
  useEffect(() => {
    const interceptor = apiClient.interceptors.response.use(
      (res) => res,
      async (err) => {
        const original = err.config;
        if (err.response?.status === 401 && !original._retry) {
          original._retry = true;
          const refreshToken = localStorage.getItem('refresh_token');
          if (!refreshToken) { logout(); return Promise.reject(err); }

          try {
            const { data } = await apiClient.post('/auth/refresh', {
              refresh_token: refreshToken,
            });
            localStorage.setItem('access_token', data.access_token);
            original.headers.Authorization = `Bearer ${data.access_token}`;
            return apiClient(original);   // retry original request
          } catch {
            logout();
            return Promise.reject(err);
          }
        }
        return Promise.reject(err);
      }
    );
    return () => apiClient.interceptors.response.eject(interceptor);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};