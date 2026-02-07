import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Mail, LockKeyhole, Building2, Loader2, AlertCircle } from 'lucide-react';
import { AuthLayout, InputGroup } from '../components';
import { useTranslation } from '../contexts/TranslationContext';
import { api } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login } = useAuth(); 

  // Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState(''); 
  const [password, setPassword] = useState('');
  
  // UI State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        email: email,
        password: password,
        full_name: name,
      };

      const res = await api.post('/auth/register', payload);

      if (res.status === 201) {
        await login(res.data.access_token);
        
        navigate('/'); 
      }
    } catch (err: any) {
      console.error('Registration failed:', err);
      
      if (err.response?.status === 409) {
        setError("This email is already registered.");
      } else if (err.response?.status === 422) {
        setError("Invalid data. Password might be too short.");
      } else {
        setError("Registration failed. Please try again later.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title={t.auth.registerTitle}>
      <form onSubmit={handleSubmit} className="space-y-4">
        
        {/* Error Banner */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 text-xs font-mono mb-4">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <InputGroup
          label={t.auth.name}
          icon={User}
          placeholder="Vincenzo"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isLoading}
        />
        
        <InputGroup
          label={t.auth.email}
          icon={Mail}
          type="email"
          placeholder="agent@project.io"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isLoading}
        />
        
        <InputGroup
          label={t.auth.password}
          icon={LockKeyhole}
          type="password"
          placeholder="Complex Key Required"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isLoading}
        />

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-4 bg-rose-500 text-black font-mono font-black rounded-2xl 
                   hover:bg-rose-400 hover:shadow-[0_0_30px_rgba(244,63,94,0.3)] 
                   active:scale-[0.98] transition-all uppercase tracking-[0.2em] mb-6 mt-4
                   disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              <span>CREATING ID...</span>
            </>
          ) : (
            t.auth.submitRegister
          )}
        </button>

        <div className="text-center">
          <p className="text-[11px] font-mono text-slate-500 uppercase tracking-widest">
            {t.auth.hasAccount}{' '}
            <button
              type="button"
              onClick={() => navigate('/login')}
              className="text-rose-500 hover:underline hover:text-rose-400 transition-colors"
            >
              {t.nav.login}
            </button>
          </p>
        </div>
      </form>
    </AuthLayout>
  );
};