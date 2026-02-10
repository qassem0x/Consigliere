import React, { memo } from 'react';
import { Rose, Plus, Cpu, ShieldCheck, LogOut, Activity, Settings } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { ChatType } from '../../types';
import { SidebarItem, SidebarCollapsedItem } from './SidebarItem';
import { cn } from '../../lib/utils';

interface SidebarProps {
    isSidebarOpen: boolean;
    userChats: ChatType[];
    activeChatId: string | null;
    onNewChat: () => void;
    onLoadChat: (id: string) => void;
    onDeleteChat: (id: string) => void;
    onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = memo(({
    isSidebarOpen,
    userChats,
    activeChatId,
    onNewChat,
    onLoadChat,
    onDeleteChat,
    onLogout
}) => {
    const { user } = useAuth();

    return (
        <aside className={cn(
            "relative z-30 bg-card border-r flex flex-col transition-all duration-300",
            isSidebarOpen ? "w-[240px]" : "w-[60px]"
        )}>
            {/* Header */}
            <div className="h-14 flex items-center justify-center border-b px-2">
                <div className={cn("flex items-center gap-2", isSidebarOpen ? "w-full px-2" : "justify-center")}>
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                        <Rose className="text-primary" size={16} strokeWidth={2.5} />
                    </div>
                    {isSidebarOpen && (
                        <span className="font-semibold text-sm tracking-tight text-foreground">Consigliere</span>
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col p-2 gap-2 overflow-hidden">
                {/* New Chat Button */}
                <button
                    onClick={onNewChat}
                    className={cn(
                        "flex items-center gap-2 rounded-md transition-all border",
                        isSidebarOpen
                            ? "px-3 py-2 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                            : "w-9 h-9 justify-center bg-primary text-primary-foreground hover:bg-primary/90"
                    )}
                >
                    <Plus size={16} />
                    {isSidebarOpen && <span className="text-xs font-semibold">New Operation</span>}
                </button>

                {/* Navigation List */}
                <div className="flex-1 overflow-y-auto mt-2 space-y-1 scrollbar-none">
                    {isSidebarOpen && (
                        <div className="px-2 pb-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                            Dossiers
                        </div>
                    )}

                    {userChats.length === 0 && (
                        <div className="flex flex-col items-center gap-2 mt-8 text-muted-foreground">
                            <Activity size={16} />
                            {isSidebarOpen && <span className="text-xs">No active operations</span>}
                        </div>
                    )}

                    {userChats.map(item => (
                        isSidebarOpen ? (
                            <SidebarItem
                                key={item.id}
                                item={item}
                                isActive={activeChatId === item.id}
                                onLoadChat={onLoadChat}
                                onDeleteChat={onDeleteChat}
                            />
                        ) : (
                            <SidebarCollapsedItem
                                key={item.id}
                                item={item}
                                isActive={activeChatId === item.id}
                                onLoadChat={onLoadChat}
                            />
                        )
                    ))}
                </div>
            </div>

            {/* Footer */}
            <div className="p-2 border-t bg-muted/20">
                {isSidebarOpen ? (
                    <div className="space-y-3 p-2">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-xs font-medium text-secondary-foreground border">
                                {user?.full_name?.[0] || 'U'}
                            </div>
                            <div className="flex flex-col overflow-hidden">
                                <span className="text-xs font-medium truncate text-foreground">{user?.full_name}</span>
                                <span className="text-[10px] text-muted-foreground truncate">Admin</span>
                            </div>
                        </div>
                        <div className="flex items-center justify-between">
                            <button className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-accent">
                                <Settings size={14} />
                            </button>
                            <button onClick={onLogout} className="text-muted-foreground hover:text-destructive transition-colors p-1 rounded-md hover:bg-destructive/10">
                                <LogOut size={14} />
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2 items-center py-2">
                        <button onClick={onLogout} className="text-muted-foreground hover:text-destructive transition-colors p-1.5"><LogOut size={16} /></button>
                    </div>
                )}
            </div>
        </aside>
    );
});