import React from 'react';
import { PanelLeftClose, PanelLeft, Zap, Shield, Brain } from 'lucide-react';

interface HeaderProps {
    isSidebarOpen: boolean;
    view: 'home' | 'chat' | 'wizard';
    onToggleSidebar: () => void;
    modelName?: string;
    chatTokenStats?: {
        total: number;
        prompt: number;
        completion: number;
        messages: number;
    };
    zeroLeaksMode?: boolean;
    onOpenMemory?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ isSidebarOpen, view, onToggleSidebar, modelName, chatTokenStats, zeroLeaksMode, onOpenMemory }) => {
    return (
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[#050505]/80 backdrop-blur-md z-20">
            <div className="flex items-center gap-4">
                <button
                    onClick={onToggleSidebar}
                    className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-all"
                >
                    {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
                </button>

                {/* Breadcrumbs / Status */}
                <div className="h-6 w-[1px] bg-white/10"></div>
                <div className="flex items-center gap-2">
                    {view === 'home' ? (
                        <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">Command Center</span>
                    ) : (
                        <>
                            <span className={`w-2 h-2 rounded-full ${zeroLeaksMode 
                                ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)]' 
                                : 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.6)]'} animate-pulse`}></span>
                            <span className={`text-xs font-mono uppercase tracking-widest font-bold ${zeroLeaksMode ? 'text-emerald-500' : 'text-amber-500'}`}>
                                {zeroLeaksMode ? 'Zero Leaks' : 'Standard'}
                            </span>
                        </>
                    )}
                </div>
            </div>
            
            <div className="flex items-center gap-4">
                {view === 'chat' && (
                    <button
                        onClick={onOpenMemory}
                        className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono text-slate-600 hover:text-slate-400 transition-colors"
                    >
                        <Brain size={12} />
                        <span>memory</span>
                    </button>
                )}
                {chatTokenStats && chatTokenStats.messages > 0 && (
                    <div className="flex items-center gap-2 text-xs font-mono">
                        <Zap size={12} className="text-amber-500" />
                        <span className="text-slate-500">Chat:</span>
                        <span className="text-slate-300 font-medium">{chatTokenStats.total.toLocaleString()}</span>
                        <span className="text-slate-600">tokens</span>
                        <span className="text-slate-700">|</span>
                        <span className="text-slate-500">{chatTokenStats.messages} reqs</span>
                    </div>
                )}
                {modelName && (
                    <div className="text-xs font-mono text-slate-500">
                        Model: <span className="text-slate-400">{modelName}</span>
                    </div>
                )}
            </div>
        </header>
    );
};