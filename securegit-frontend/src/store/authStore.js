import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as authApi from '../api/auth';

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (credentials) => {
        set({ isLoading: true });
        try {
          const res = await authApi.login(credentials);
          set({ user: res.data.user, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (err) {
          set({ isLoading: false });
          const message = err.response?.data?.message
            || (err.response ? 'Login failed. Please try again.' : 'Network error. Please check your connection.');
          return { success: false, error: message };
        }
      },

      register: async (credentials) => {
        set({ isLoading: true });
        try {
          const res = await authApi.register(credentials);
          set({ user: res.data.user, isAuthenticated: true, isLoading: false });
          return { success: true };
        } catch (err) {
          set({ isLoading: false });
          const message = err.response?.data?.message
            || (err.response ? 'Registration failed. Please try again.' : 'Network error. Please check your connection.');
          return { success: false, error: message };
        }
      },

      logout: async () => {
        try { await authApi.logout(); } catch { /* ignore */ }
        set({ user: null, isAuthenticated: false });
      },

      fetchMe: async () => {
        try {
          const res = await authApi.me();
          set({ user: res.data, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },

      setUser: (user) => set({ user, isAuthenticated: !!user }),
    }),
    {
      name: 'securegit-auth',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);

export default useAuthStore;
