// ============================================================
// SalesOS AI — Auth Context
// React context for authentication state management.
// ============================================================

'use client';

import { createContext, useContext, useCallback, useEffect, useReducer } from 'react';
import { useRouter } from 'next/navigation';
import { api, setTokens, clearTokens, getTokens } from './api';

// State
const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

function authReducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: true, error: null };
    case 'SET_USER':
      return { ...state, user: action.payload, isAuthenticated: true, isLoading: false, error: null };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'LOGOUT':
      return { ...initialState, isLoading: false };
    default:
      return state;
  }
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);
  const router = useRouter();

  // Check for existing session on mount
  useEffect(() => {
    const { accessToken } = getTokens();
    if (accessToken) {
      loadUser();
    } else {
      dispatch({ type: 'LOGOUT' });
    }
  }, []);

  const loadUser = useCallback(async () => {
    try {
      dispatch({ type: 'SET_LOADING' });
      const res = await api.getMe();
      dispatch({ type: 'SET_USER', payload: res.data });
    } catch {
      clearTokens();
      dispatch({ type: 'LOGOUT' });
    }
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      dispatch({ type: 'SET_LOADING' });
      const res = await api.login(email, password);
      setTokens(res.data.access_token, res.data.refresh_token);
      dispatch({ type: 'SET_USER', payload: res.data.user });
      router.push('/dashboard');
      return res.data;
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message || 'Login failed' });
      throw err;
    }
  }, [router]);

  const register = useCallback(async (data) => {
    try {
      dispatch({ type: 'SET_LOADING' });
      const res = await api.register(data);
      setTokens(res.data.access_token, res.data.refresh_token);
      // Load user profile after registration
      await loadUser();
      router.push('/dashboard');
      return res.data;
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message || 'Registration failed' });
      throw err;
    }
  }, [router, loadUser]);

  const logout = useCallback(() => {
    clearTokens();
    dispatch({ type: 'LOGOUT' });
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, loadUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
