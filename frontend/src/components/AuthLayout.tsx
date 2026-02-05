import React from 'react';
import { Rose } from 'lucide-react';

interface AuthLayoutProps {
  children?: React.ReactNode;
  title: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title }) => {
  const BackgroundDecor = React.lazy(() => import('./BackgroundDecor').then(m => ({ default: m.BackgroundDecor })));
  
  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      <React.Suspense fallback={null}>
        <BackgroundDecor />
      </React.Suspense>
      <div className="max-w-md w-full relative z-10 animate-fade-in">
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-rose-500 flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(244,63,94,0.4)]">
            <Rose className="w-10 h-10 text-black" />
          </div>
          <h2 className="text-3xl font-serif text-white tracking-tight">{title}</h2>
        </div>
        <div className="bg-white/5 border border-white/10 backdrop-blur-2xl rounded-[2.5rem] p-10 shadow-2xl">
          {children}
        </div>
      </div>
    </div>
  );
};
