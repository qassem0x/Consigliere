import React from 'react';
import { FileText, Cpu, ArrowRight, Target, ShieldAlert } from 'lucide-react';
import { Dossier } from '../types';

interface DossierViewProps {
  dossier: Dossier;
  onActionClick: (action: string) => void;
}

export const DossierView: React.FC<DossierViewProps> = ({ dossier, onActionClick }) => {
  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header Block */}
      <div className="bg-[#0a0a0b] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
        <div className="bg-white/[0.02] border-b border-white/5 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-500/10 rounded-lg border border-rose-500/20">
              <Cpu size={16} className="text-rose-500" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">INTELLIGENCE BRIEFING</h3>
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">
                {dossier.file_type || 'Unknown Data Source'}
              </p>
            </div>
          </div>
          <div className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-mono text-emerald-500 uppercase tracking-widest">
            Analysis Complete
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* The Briefing Text */}
          <div className="prose prose-invert prose-sm max-w-none">
            <p className="text-slate-300 leading-relaxed font-light">
              {dossier.briefing}
            </p>
          </div>

          {/* Key Entities (Tags) */}
          {dossier.key_entities && dossier.key_entities.length > 0 && (
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest flex items-center gap-2">
                <Target size={12} /> Key Vectors Detected
              </span>
              <div className="flex flex-wrap gap-2">
                {dossier.key_entities.map((entity, i) => (
                  <span 
                    key={i} 
                    className="px-2.5 py-1 bg-white/5 border border-white/10 rounded-md text-xs text-slate-300 font-mono"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recommended Actions (The Interactive Buttons) */}
      {dossier.recommended_actions && dossier.recommended_actions.length > 0 && (
        <div className="space-y-3">
           <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest flex items-center gap-2 pl-1">
              <ShieldAlert size={12} /> Recommended Protocols
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {dossier.recommended_actions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => onActionClick(action)}
                className="group relative p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-rose-500/5 hover:border-rose-500/30 text-left transition-all hover:shadow-[0_0_20px_rgba(244,63,94,0.1)] active:scale-[0.98]"
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="text-sm text-slate-300 group-hover:text-rose-100 transition-colors">
                    {action}
                  </span>
                  <ArrowRight 
                    size={16} 
                    className="text-slate-600 group-hover:text-rose-500 group-hover:-rotate-45 transition-all duration-300 flex-shrink-0 mt-0.5" 
                  />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};