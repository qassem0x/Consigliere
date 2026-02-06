import React from 'react';
import { Rose, Plus, Cpu, ShieldCheck, LogOut, Activity, FileSpreadsheet, Database } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { ChatType } from '../../types';
import { SidebarItem, SidebarCollapsedItem } from './SidebarItem';

interface SidebarProps {
    isSidebarOpen: boolean;
    userChats: ChatType[];
    activeChatId: string | null;
    onNewChat: () => void;
    onLoadChat: (id: string) => void;
    onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
    isSidebarOpen,
    userChats,
    activeChatId,
    onNewChat,
    onLoadChat,
    onLogout
}) => {
    const { user } = useAuth();

    return (
        <aside className={`
            relative z-30 bg-[#08080a] border-r border-white/5 flex flex-col transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)]
            ${isSidebarOpen ? 'w-[280px]' : 'w-[70px]'}
        `}>
            {/* Brand */}
            <div className="h-16 flex items-center justify-center border-b border-white/5 relative">
                <div className={`flex items-center gap-3 transition-opacity duration-300 ${isSidebarOpen ? 'opacity-100' : 'opacity-0 absolute'}`}>
                    <Rose className="text-rose-600" size={20} strokeWidth={2.5} />
                    <span className="font-serif text-lg tracking-wide text-white font-medium">Consigliere</span>
                </div>
                {!isSidebarOpen && <Rose className="text-rose-600" size={24} />}
            </div>

            {/* Primary Action */}
            <div className="p-4">
                <button
                    onClick={onNewChat}
                    className={`
                        group w-full flex items-center gap-3 bg-white/5 hover:bg-rose-600 hover:text-white border border-white/5 hover:border-rose-500 transition-all rounded-xl relative overflow-hidden
                        ${isSidebarOpen ? 'px-4 py-3' : 'p-3 justify-center'}
                    `}
                >
                    <div className="absolute inset-0 bg-gradient-to-r from-rose-600/0 via-rose-600/20 to-rose-600/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                    <Plus size={18} className="relative z-10 transition-transform group-hover:rotate-90" />
                    {isSidebarOpen && <span className="relative z-10 text-xs font-bold uppercase tracking-widest">New Operation</span>}
                </button>
            </div>

            {/* Navigation / History */}
            <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin space-y-1">
                {isSidebarOpen && (
                    <div className="flex items-center justify-between px-2 mb-2 mt-2">
                        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-bold">Dossiers</span>
                        <span className="text-[9px] bg-white/5 text-slate-500 px-1.5 py-0.5 rounded border border-white/5">{userChats.length}</span>
                    </div>
                )}
                {userChats.map(item => (
                    isSidebarOpen ? 
                        <SidebarItem key={item.id} item={item} isActive={activeChatId === item.id} onLoadChat={onLoadChat} /> : 
                        <SidebarCollapsedItem key={item.id} item={item} onLoadChat={onLoadChat} />
                ))}
            </div>

            {/* System Stats Footer */}
            <div className="p-4 bg-black/20 border-t border-white/5">
                {isSidebarOpen ? (
                    <div className="space-y-4">
                        {/* Stats */}
                        <div className="grid grid-cols-2 gap-2">
                            <div className="bg-white/5 rounded p-2 border border-white/5">
                                <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
                                    <Cpu size={10} /> LATENCY
                                </div>
                                <div className="text-xs font-mono text-emerald-400">12ms</div>
                            </div>
                            <div className="bg-white/5 rounded p-2 border border-white/5">
                                <div className="flex items-center gap-1.5 text-[10px] text-slate-500 mb-1">
                                    <ShieldCheck size={10} /> SECURITY
                                </div>
                                <div className="text-xs font-mono text-rose-400">ENCRYPTED</div>
                            </div>
                        </div>
                        {/* User */}
                        <div className="flex items-center justify-between pt-2 border-t border-white/5">
                            <div className="flex items-center gap-2.5">
                                <div className="relative">
                                    <div className="w-8 h-8 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold text-white">
                                        {user?.full_name[0]}
                                    </div>
                                    <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-[#08080a] rounded-full flex items-center justify-center">
                                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                    </div>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-xs font-medium text-slate-200">{user?.full_name}</span>
                                    <span className="text-[9px] text-slate-500 font-mono">Level 1 Admin</span>
                                </div>
                            </div>
                            <button onClick={onLogout} className="p-2 hover:bg-rose-500/10 hover:text-rose-500 rounded-lg transition-colors">
                                <LogOut size={16} />
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-4 items-center">
                        <Activity size={16} className="text-emerald-500 animate-pulse" />
                        <button onClick={onLogout} className="hover:text-rose-500 transition-colors"><LogOut size={18} /></button>
                    </div>
                )}
            </div>
        </aside>
    );
};