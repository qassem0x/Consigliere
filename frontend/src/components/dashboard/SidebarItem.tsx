import React, { useState, useRef, useEffect } from 'react';
import { ChatType } from '../../types';
import { formatTimeAgo } from '../../utils/utils';
import { FileSpreadsheet, Database, Trash2, MoreHorizontal, Shield, Settings } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SidebarItemProps {
    item: ChatType;
    isActive: boolean;
    onLoadChat: (id: string) => void;
    onDeleteChat: (id: string) => void;
    onUpdateSettings?: (chatId: string, settings: { zero_leaks_mode: boolean; max_row_limit: number }) => void;
}

export const SidebarItem: React.FC<SidebarItemProps> = ({ item, isActive, onLoadChat, onDeleteChat, onUpdateSettings }) => {
    const [showSettings, setShowSettings] = useState(false);
    const settingsRef = useRef<HTMLDivElement>(null);
    const [localSettings, setLocalSettings] = useState({
        zero_leaks_mode: item.settings?.zero_leaks_mode ?? false,
        max_row_limit: item.settings?.max_row_limit ?? 100
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
            max_row_limit: item.settings?.max_row_limit ?? 100
        });
        setShowSettings(!showSettings);
    };

    const handleSaveSettings = () => {
        if (onUpdateSettings) {
            onUpdateSettings(item.id, localSettings);
        }
        setShowSettings(false);
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
                <div className="absolute right-0 top-full mt-1 z-[100] w-64 bg-[#1a1a1e] border border-white/10 rounded-lg shadow-xl p-3">
                    <div className="flex items-center gap-2 mb-3">
                        <Shield size={14} className="text-primary" />
                        <span className="text-xs font-medium text-white">Chat Settings</span>
                    </div>
                    <div className="space-y-3">
                        <div>
                            <label className="text-[10px] text-slate-400 mb-1.5 block">Max Row Limit</label>
                            <input
                                type="number"
                                min="1"
                                max="100000"
                                value={localSettings.max_row_limit}
                                onChange={(e) => setLocalSettings({...localSettings, max_row_limit: parseInt(e.target.value) || 100})}
                                className="w-full px-2 py-1.5 bg-white/5 border border-white/10 rounded text-white text-xs focus:outline-none focus:border-primary"
                            />
                        </div>
                        <div className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/5">
                            <div className="flex items-center gap-2">
                                <Shield size={12} className="text-slate-400" />
                                <span className="text-xs text-slate-300">Zero Leaks</span>
                            </div>
                            <label className="cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={localSettings.zero_leaks_mode}
                                    onChange={(e) => setLocalSettings({...localSettings, zero_leaks_mode: e.target.checked})}
                                    className="sr-only peer"
                                />
                                <div className="relative w-8 h-4 bg-white/10 rounded-full peer peer-checked:bg-primary transition-colors">
                                    <div className="absolute left-0.5 top-0.5 w-3 h-3 bg-white rounded-full transition-transform peer-checked:translate-x-4"></div>
                                </div>
                            </label>
                        </div>
                        <div className="flex gap-2 pt-2 border-t border-white/5">
                            <button
                                onClick={() => setShowSettings(false)}
                                className="flex-1 px-2 py-1.5 rounded text-xs border border-white/10 text-slate-300 hover:bg-white/5"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveSettings}
                                className="flex-1 px-2 py-1.5 rounded text-xs bg-primary text-white hover:bg-primary/90"
                            >
                                Save
                            </button>
                        </div>
                    </div>
                </div>
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
