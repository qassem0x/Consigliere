import React from 'react';
import { Cpu, ArrowRight, Target, ShieldAlert, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Dossier } from '../types';

interface DossierViewProps {
  dossier: Dossier;
  onActionClick: (action: string) => void;
}

export const DossierView: React.FC<DossierViewProps> = ({ dossier, onActionClick }) => {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header Block */}
      <div className="bg-[#0a0a0b] border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative">
        {/* Top Decoration */}
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-rose-500/0 via-rose-500/50 to-rose-500/0 opacity-50"></div>

        <div className="bg-white/[0.02] border-b border-white/5 p-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20 shadow-[0_0_15px_-3px_rgba(244,63,94,0.3)]">
              <FileText size={20} className="text-rose-500" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white tracking-wide uppercase font-mono">
                {'Unknown Source'}
              </h3>
              <p className="text-[10px] text-rose-400/80 font-mono uppercase tracking-widest mt-1">
                Classified Intelligence Briefing
              </p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest">
              Analysis Complete
            </span>
          </div>
        </div>

        <div className="p-8">
          {/* MARKDOWN CONTENT */}
          <div className="prose prose-invert max-w-none 
              /* PARAGRAPH STYLING */
              prose-p:text-slate-300 prose-p:leading-7 prose-p:mb-4
              
              /* HEADER 1 (##) STYLING - The fix you requested */
              prose-h2:text-xl prose-h2:font-bold prose-h2:text-white prose-h2:uppercase prose-h2:tracking-wider prose-h2:mb-4 prose-h2:mt-8 prose-h2:flex prose-h2:items-center prose-h2:gap-2
              prose-h2:border-b prose-h2:border-white/10 prose-h2:pb-2
              
              /* HEADER 2 (###) STYLING */
              prose-h3:text-sm prose-h3:font-bold prose-h3:text-rose-400 prose-h3:uppercase prose-h3:tracking-widest prose-h3:mt-6 prose-h3:mb-2
              
              /* LIST STYLING */
              prose-ul:my-4 prose-ul:space-y-2 
              prose-li:text-slate-300 prose-li:pl-2
              prose-li:marker:text-rose-500 
              
              /* BOLD TEXT */
              prose-strong:text-rose-200 prose-strong:font-semibold
          ">
            <ReactMarkdown
               components={{
                // Custom renderer to add icons to headers automatically if you want
                h2: ({node, ...props}) => <h2 className="text-xl font-bold text-white uppercase tracking-wider mb-4 mt-8 border-b border-white/10 pb-2" {...props} />,
              }}
            >
              {dossier.briefing}
            </ReactMarkdown>
          </div>

          {/* Key Entities Tags */}
          {dossier.key_entities && dossier.key_entities.length > 0 && (
            <div className="mt-8 pt-6 border-t border-white/5">
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-3">
                <Target size={14} className="text-rose-500" /> Key Vectors Identified
              </span>
              <div className="flex flex-wrap gap-2">
                {dossier.key_entities.map((entity, i) => (
                  <span 
                    key={i} 
                    className="px-3 py-1.5 bg-white/[0.03] border border-white/10 rounded-md text-xs text-slate-300 font-mono hover:border-rose-500/40 hover:text-rose-400 transition-colors cursor-default"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Grid */}
      {dossier.recommended_actions && dossier.recommended_actions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="col-span-full mb-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    <ShieldAlert size={14} className="text-rose-500" /> Recommended Protocols
                </span>
            </div>
            {dossier.recommended_actions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => onActionClick(action)}
                className="group relative p-5 rounded-xl border border-white/10 bg-[#0a0a0b] hover:bg-rose-500/[0.02] hover:border-rose-500/30 text-left transition-all hover:shadow-[0_0_20px_rgba(244,63,94,0.05)] active:scale-[0.98]"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-rose-500/0 group-hover:bg-rose-500 rounded-l-xl transition-all duration-300"></div>
                <div className="flex items-start justify-between gap-4">
                  <span className="text-sm font-medium text-slate-300 group-hover:text-rose-100 transition-colors line-clamp-2">
                    {action}
                  </span>
                  <div className="p-1.5 rounded-lg bg-white/5 text-slate-500 group-hover:bg-rose-500 group-hover:text-white transition-all duration-300">
                    <ArrowRight size={14} className="group-hover:-rotate-45 transition-transform duration-300" />
                  </div>
                </div>
              </button>
            ))}
        </div>
      )}
    </div>
  );
};