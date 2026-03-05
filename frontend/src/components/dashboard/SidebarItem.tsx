import React, { useState, useRef, useEffect } from 'react';
import { ChatType } from '../../types';
import { formatTimeAgo } from '../../utils/utils';
import { FileSpreadsheet, Database, Trash2, MoreHorizontal, Shield, Settings } from 'lucide-react';
import { cn } from '../../lib/utils';
import { ChatSettingsModal } from './ChatSettingsModal';

interface SidebarItemProps {
    item: ChatType;
    isActive: boolean;
    onLoadChat: (id: string) => void;
    onDeleteChat: (id: string) => void;
    onUpdateSettings?: (chatId: string, settings: { zero_leaks_mode: boolean; max_row_limit: number; custom_prompt?: string }) => void;
}

export const SidebarItem: React.FC<SidebarItemProps> = ({ item, isActive, onLoadChat, onDeleteChat, onUpdateSettings }) => {
    const [showSettings, setShowSettings] = useState(false);
    const settingsRef = useRef<HTMLDivElement>(null);
    const [localSettings, setLocalSettings] = useState({
        zero_leaks_mode: item.settings?.zero_leaks_mode ?? false,
        max_row_limit: item.settings?.max_row_limit ?? 100,
        custom_prompt: item.settings?.custom_prompt ?? ''
    });

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
                setShowSettings(false);
            }
        };
        if (showSettings) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [showSettings]);

    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (window.confirm("Permanently delete this dossier?")) {
            onDeleteChat(item.id);
        }
    };

    const handleSettingsClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        setLocalSettings({
            zero_leaks_mode: item.settings?.zero_leaks_mode ?? false,
            max_row_limit: item.settings?.max_row_limit ?? 100,
            custom_prompt: item.settings?.custom_prompt ?? ''
        });
        setShowSettings(!showSettings);
    };

    return (
        <div className="relative" ref={settingsRef}>
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
                        <FileSpreadsheet size={14} className={cn("shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />
                    ) : (
                        <Database size={14} className={cn("shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />
                    )}
                    <span className="text-xs font-medium truncate">
                        {item.title || "Untitled Operation"}
                    </span>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div
                        onClick={handleSettingsClick}
                        className="p-1 rounded-sm hover:bg-white/10 hover:text-white transition-colors"
                        title="Settings"
                    >
                        <Settings size={12} />
                    </div>
                    <div
                        onClick={handleDelete}
                        className="p-1 rounded-sm hover:bg-destructive/10 hover:text-destructive transition-colors"
                    >
                        <Trash2 size={12} />
                    </div>
                </div>
            </button>

            {showSettings && (
                <ChatSettingsModal
                    isOpen={showSettings}
                    onClose={() => setShowSettings(false)}
                    settings={localSettings}
                    onSave={(newSettings) => {
                        setLocalSettings(newSettings);
                        onUpdateSettings?.(item.id, newSettings);
                    }}
                />
            )}
        </div>
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
