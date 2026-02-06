import React from 'react';
import { Zap, Plus, Database, FileSpreadsheet, HardDrive } from 'lucide-react';

interface HomeViewProps {
    onNewChat: () => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onNewChat }) => {
    return (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-8 animate-in fade-in duration-700">

            {/* Decorative Background Elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-rose-500/5 rounded-full blur-[100px]"></div>
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-[100px]"></div>
            </div>

            <div className="relative z-10 text-center max-w-2xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-sm">
                    <Zap size={12} className="text-yellow-500 fill-current" />
                    <span className="text-[10px] font-mono text-slate-300 uppercase tracking-widest">System Operational</span>
                </div>

                <h1 className="text-5xl md:text-7xl font-serif text-white mb-6 tracking-tight">
                    Consigliere
                    <span className="text-rose-600">.</span>
                </h1>

                <p className="text-slate-400 text-lg font-light leading-relaxed mb-12">
                    Your private intelligence node is ready. <br />
                    Connect a data source to begin tactical analysis.
                </p>

                <div className="flex items-center justify-center gap-4">
                    <button
                        onClick={onNewChat}
                        className="group px-8 py-4 bg-rose-600 hover:bg-rose-500 text-white font-mono font-bold rounded-xl transition-all shadow-[0_0_30px_rgba(225,29,72,0.2)] hover:shadow-[0_0_50px_rgba(225,29,72,0.4)] active:scale-95 flex items-center gap-3"
                    >
                        <Plus size={18} className="group-hover:rotate-90 transition-transform" />
                        <span>INITIALIZE MISSION</span>
                    </button>
                </div>

                <div className="mt-16 grid grid-cols-3 gap-8 opacity-50">
                    <div className="flex flex-col items-center gap-2">
                        <Database className="text-slate-600" />
                        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">Local SQL</span>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <FileSpreadsheet className="text-slate-600" />
                        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">Excel / CSV</span>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <HardDrive className="text-slate-600" />
                        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">Secure Drive</span>
                    </div>
                </div>
            </div>
        </div>
    );
};