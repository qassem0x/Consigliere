import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../utils/api'; 

interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const initAuth = async () => {
      try {
        const res = await api.get('/auth/me');
        setUser(res.data);
        if (location.pathname === '/login' || location.pathname === '/') {
           navigate('/dashboard');
        }
      } catch (error) {
        console.error("Not authenticated:", error);
        if (location.pathname !== '/' && location.pathname !== '/login' && location.pathname !== '/register') {
          navigate('/login');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async () => {
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      navigate('/dashboard');
    } catch (error) {
      console.error("Failed to fetch user profile", error);
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error("Logout request failed:", error);
    }
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};