import React from 'react';
import { ChatType } from '../../types';
import { formatTimeAgo } from '../../utils/utils';
import { FileSpreadsheet, Database, Trash2, MoreHorizontal } from 'lucide-react';
import { cn } from '../../lib/utils';

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
            className={cn(
                "w-full group flex items-center justify-between p-2 rounded-md transition-all duration-200 border border-transparent",
                isActive
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            )}
        >
            <div className="flex items-center gap-2 overflow-hidden">
                {item.type === 'excel' ? (
                    <FileSpreadsheet size={14} className={cn("shrink-0", isActive ? "text-emerald-500" : "text-muted-foreground")} />
                ) : (
                    <Database size={14} className={cn("shrink-0", isActive ? "text-blue-500" : "text-muted-foreground")} />
                )}
                <span className="text-xs font-medium truncate">
                    {item.title || "Untitled Operation"}
                </span>
            </div>

            <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                <div
                    onClick={handleDelete}
                    className="p-1 rounded-sm hover:bg-destructive/10 hover:text-destructive transition-colors"
                >
                    <Trash2 size={12} />
                </div>
            </div>
        </button>
    );
};

interface SidebarCollapsedItemProps {
    item: ChatType;
    isActive: boolean;
    onLoadChat: (id: string) => void;
}

export const SidebarCollapsedItem: React.FC<SidebarCollapsedItemProps> = ({ item, isActive, onLoadChat }) => {
    return (
        <div
            onClick={() => onLoadChat(item.id)}
            className={cn(
                "w-9 h-9 mx-auto mb-2 rounded-md flex items-center justify-center cursor-pointer transition-colors",
                isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            )}
            title={item.title}
        >
            {item.type === 'excel' ? <FileSpreadsheet size={16} /> : <Database size={16} />}
        </div>
    );
};