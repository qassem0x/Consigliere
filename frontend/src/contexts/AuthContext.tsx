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
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');
      const storedRefreshToken = localStorage.getItem('refresh_token');
      
      if (storedToken) {
        setToken(storedToken);
        setRefreshToken(storedRefreshToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
        
        try {
          const res = await api.get('/auth/me');
          setUser(res.data);
          if (location.pathname === '/login') {
             navigate('/dashboard');
           }
        } catch (error) {
          console.error("Session expired:", error);
          if (storedRefreshToken) {
            try {
              const res = await api.post('/auth/refresh', null, {
                params: { refresh_token: storedRefreshToken }
              });
              const newAccessToken = res.data.access_token;
              localStorage.setItem('token', newAccessToken);
              setToken(newAccessToken);
              api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
              const userRes = await api.get('/auth/me');
              setUser(userRes.data);
            } catch (refreshError) {
              console.error("Token refresh failed:", refreshError);
              logout();
            }
          } else {
            logout(); 
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const refreshTokenFn = async () => {
    if (!refreshToken) {
      logout();
      return;
    }
    try {
      const res = await api.post('/auth/refresh', null, {
        params: { refresh_token: refreshToken }
      });
      const newAccessToken = res.data.access_token;
      localStorage.setItem('token', newAccessToken);
      setToken(newAccessToken);
      api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout();
    }
  };

  const login = async (newToken: string, newRefreshToken?: string) => {
    localStorage.setItem('token', newToken);
    if (newRefreshToken) {
      localStorage.setItem('refresh_token', newRefreshToken);
      setRefreshToken(newRefreshToken);
    }
    setToken(newToken);
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;

    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
      navigate('/dashboard');
    } catch (error) {
      console.error("Failed to fetch user profile", error);
    }
  };

  const logout = async () => {
    const currentToken = token || localStorage.getItem('token');
    try {
      await api.post('/auth/logout', null, {
        params: { token: currentToken }
      });
    } catch (error) {
      console.error("Logout request failed:", error);
    }
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    delete api.defaults.headers.common['Authorization'];
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!user, isLoading, login, logout, refreshToken: refreshTokenFn }}>
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