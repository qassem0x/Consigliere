import React from 'react';
import { ChatType } from '../../types';
import { formatTimeAgo } from '../../utils/utils';
import { FileSpreadsheet, Database, Trash2 } from 'lucide-react';

interface SidebarItemProps {
    item: ChatType;
    isActive: boolean;
    onLoadChat: (id: string) => void;
    onDeleteChat: (id: string) => void; 
}

export const SidebarItem: React.FC<SidebarItemProps> = ({ item, isActive, onLoadChat, onDeleteChat }) => {
    
    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (window.confirm("Permanently delete this dossier?")) {
            onDeleteChat(item.id);
        }
    };

    return (
        <button
            onClick={() => onLoadChat(item.id)}
            className={`
                w-full group flex flex-col gap-1.5 p-3 rounded-lg transition-all duration-200 border relative
                ${isActive
                    ? 'bg-rose-500/10 border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]'
                    : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/5'}
            `}
        >
            <div className="flex items-center justify-between w-full h-5">
                <span className={`text-[13px] font-medium truncate tracking-tight ${isActive ? 'text-rose-100' : 'text-slate-400 group-hover:text-slate-200'}`}>
                    {item.title.substring(0, 22)}{item.title.length > 22 ? '...' : ''}
                </span>
                
                <div className="flex items-center justify-end min-w-[40px]">
                    <span className="text-[9px] text-slate-600 font-mono opacity-60 group-hover:hidden transition-opacity whitespace-nowrap">
                        {formatTimeAgo(item.created_at)}
                    </span>
                    
                    <div 
                        onClick={handleDelete}
                        className="hidden group-hover:flex items-center justify-center p-1 -mr-1 rounded hover:bg-rose-500/20 text-slate-500 hover:text-rose-500 transition-colors"
                        title="Delete Dossier"
                    >
                        <Trash2 size={12} />
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <div className={`h-0.5 rounded-full flex-1 transition-all ${isActive ? 'bg-rose-500/50' : 'bg-white/5 group-hover:bg-white/10'}`}></div>
                <div className="flex gap-0.5">
                    <div className={`w-0.5 h-0.5 rounded-full ${item.type === 'excel' ? 'bg-emerald-500' : 'bg-blue-500'}`}></div>
                    <div className="w-0.5 h-0.5 bg-rose-500 rounded-full animate-pulse"></div>
                </div>
            </div>
        </button>
    );
};

interface SidebarCollapsedItemProps {
    item: ChatType;
    onLoadChat: (id: string) => void;
}

export const SidebarCollapsedItem: React.FC<SidebarCollapsedItemProps> = ({ item, onLoadChat }) => {
    return (
        <div 
            onClick={() => onLoadChat(item.id)}
            className="w-9 h-9 mx-auto mb-2 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center hover:border-rose-500/50 cursor-pointer text-slate-500 hover:text-rose-500 transition-colors"
        >
            {item.type === 'excel' ? <FileSpreadsheet size={14} /> : <Database size={14} />}
        </div>
    );
};