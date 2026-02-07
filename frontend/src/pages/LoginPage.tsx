import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, LockKeyhole, AlertCircle, Loader2 } from 'lucide-react';
import { AuthLayout, InputGroup } from '../components';
import { useTranslation } from '../contexts/TranslationContext';
import { api } from '../utils/api'; 
import {useAuth} from "../contexts/AuthContext"

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email); 
      formData.append('password', password);

      const res = await api.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      if (res.status === 200) {
        const { access_token } = res.data;
        localStorage.setItem('token', access_token);
        
        navigate('/');
      }
    } catch (err: any) {
      console.error('Login failed:', err);
      if (err.response?.status === 401) {
        setError("Invalid credentials. Please check your email and password.");
      } else if (err.response?.status === 403) {
        setError("This account has been disabled.");
      } else {
        setError("Connection failed. Is the server running?");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title={t.auth.loginTitle}>
      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Error Banner */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 text-xs font-mono">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <InputGroup
            label={t.auth.email}
            icon={Mail}
            type="email"
            placeholder="admin@sovereign.local"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
          />
          <InputGroup
            label={t.auth.password}
            icon={LockKeyhole}
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-4 bg-rose-500 text-black font-mono font-black rounded-2xl 
                   hover:bg-rose-400 hover:shadow-[0_0_30px_rgba(244,63,94,0.3)] 
                   active:scale-[0.98] transition-all uppercase tracking-[0.2em] 
                   disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              <span>AUTHENTICATING...</span>
            </>
          ) : (
            t.auth.submitLogin
          )}
        </button>

        <div className="text-center">
          <p className="text-[11px] font-mono text-slate-500 uppercase tracking-widest">
            {t.auth.noAccount}{' '}
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="text-rose-500 hover:underline hover:text-rose-400 transition-colors"
            >
              {t.nav.register}
            </button>
          </p>
        </div>
      </form>
    </AuthLayout>
  );
};