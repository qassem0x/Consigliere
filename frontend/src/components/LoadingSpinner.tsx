import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC = () => {
  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4">
        <Loader2 
          size={48} 
          className="text-rose-500 animate-spin" 
        />
        <p className="text-slate-400 font-mono text-sm uppercase tracking-widest">
          Loading...
        </p>
      </div>
    </div>
  );
};
