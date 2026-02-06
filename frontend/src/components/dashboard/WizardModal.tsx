import React from 'react';
import { X, ChevronRight, FileSpreadsheet, Database } from 'lucide-react';

interface WizardModalProps {
    onClose: () => void;
    onFileUpload: () => void;
}

export const WizardModal: React.FC<WizardModalProps> = ({ onClose, onFileUpload }) => {
    return (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-xl flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
            <div className="w-full max-w-3xl bg-[#09090b] border border-white/10 rounded-[2rem] shadow-2xl relative overflow-hidden">

                {/* Modal Header */}
                <div className="p-8 border-b border-white/5 flex justify-between items-start bg-white/[0.02]">
                    <div>
                        <h2 className="text-2xl font-serif text-white mb-2">Configure New Uplink</h2>
                        <p className="text-slate-400 text-sm">Select a data protocol to initialize the agent.</p>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Modal Content */}
                <div className="p-10 grid grid-cols-2 gap-6">
                    <button
                        onClick={onFileUpload}
                        className="group p-8 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-emerald-500/50 transition-all text-left relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ChevronRight className="text-emerald-500" />
                        </div>
                        <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
                            <FileSpreadsheet className="text-emerald-500" size={28} />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-2">Local File</h3>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Analyze spreadsheets (Excel, CSV) or Documents (PDF). Processed in-memory.
                        </p>
                    </button>

                    <button className="group p-8 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-blue-500/50 transition-all text-left relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <ChevronRight className="text-blue-500" />
                        </div>
                        <div className="w-14 h-14 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
                            <Database className="text-blue-500" size={28} />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-2">Database Cluster</h3>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Connect read-only replica of Postgres or MySQL. Ideal for large datasets.
                        </p>
                    </button>
                </div>

                {/* Modal Footer */}
                <div className="p-6 bg-black/40 border-t border-white/5 flex items-center justify-center">
                    <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-white/5 border border-white/5">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                        </span>
                        <span className="text-[10px] font-mono text-slate-300 uppercase tracking-widest">
                            Awaiting Selection
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};