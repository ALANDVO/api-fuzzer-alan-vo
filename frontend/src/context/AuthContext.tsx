import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, setAccessToken } from '../api/client';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  role: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, role: string) => Promise<void>;
  logout: () => Promise<void>;
  switchRole: (newRole: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<string>('operator');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const initAuth = async () => {
    try {
      setIsLoading(true);
      const authData = await api.login('operator@example.com', 'operator');
      setUser({
        user_id: authData.user_id,
        email: authData.email,
        roles: authData.roles,
        auth_method: 'demo_bearer',
      });
      setRole('operator');
    } catch (err) {
      console.error('Initial demo auth failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email: string, targetRole: string) => {
    setIsLoading(true);
    try {
      const authData = await api.login(email, targetRole);
      setUser({
        user_id: authData.user_id,
        email: authData.email,
        roles: authData.roles,
        auth_method: 'bearer',
      });
      setRole(targetRole);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.logout();
      setUser(null);
      setAccessToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  const switchRole = async (newRole: string) => {
    const currentEmail = user?.email || `${newRole}@example.com`;
    await login(currentEmail, newRole);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
