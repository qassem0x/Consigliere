import React from 'react';
import { PanelLeftClose, PanelLeft } from 'lucide-react';

interface HeaderProps {
    isSidebarOpen: boolean;
    view: 'home' | 'chat' | 'wizard';
    onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ isSidebarOpen, view, onToggleSidebar }) => {
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
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse shadow-[0_0_10px_rgba(244,63,94,0.5)]"></span>
                            <span className="text-xs font-mono text-rose-500 uppercase tracking-widest font-bold">Active Uplink</span>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
};