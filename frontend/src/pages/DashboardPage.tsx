import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

import { DossierView } from '../components/DossierView';

import {
    LayoutDashboard,
    Plus,
    Database,
    FileSpreadsheet,
    Rose,
    User,
    Send,
    LogOut,
    PanelLeftClose,
    PanelLeft,
    Zap,
    X,
    Cpu,
    Activity,
    HardDrive,
    GitBranch,
    ShieldCheck,
    ChevronRight,
    Command
} from 'lucide-react';

import ReactMarkdown from 'react-markdown';

import { useAuth } from '../contexts/AuthContext';

import { ChatType, Dossier, Message } from '../types';

import { chatService } from '../services/chat';

import { formatTimeAgo } from '../utils/utils';

import { fileService } from '../services/files';





export const DashboardPage: React.FC = () => {
    const { user, logout } = useAuth();

    // UI State
    const [view, setView] = useState<'home' | 'chat' | 'wizard'>('home');
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const [activeChatId, setActiveChatId] = useState<string | null>(null);
    const [userChats, setUserChats] = useState<ChatType[]>([])
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentDossier, setCurrentDossier] = useState<Dossier|null>(null);
    const [uploadProgress, setUploadProgress] = useState<{
        phase: 'uploading' | 'analyzing' | null;
        fileName?: string;
    }>({ phase: null });
    const [loadingChatHistory, setLoadingChatHistory] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    const loadUserChats = useCallback(async () => {
        try {
            const chats: ChatType[] = await chatService.loadUserChats();
            setUserChats(chats)
        } catch (error: any) {
            console.error("Failed to load user chats:", error);
        }
    }, []);

    useEffect(() => {
        loadUserChats()
    }, [loadUserChats])

    const handleNewChat = useCallback(() => setView('wizard'), []);

    const handleLoadChat = useCallback(async (id: string) => {
        setActiveChatId(id);
        setView('chat');
        setLoadingChatHistory(true);
        setMessages([]);

        try {
            const [history, dossier] = await Promise.all([
                chatService.loadChatHistory(id),
                fileService.loadDossier(id)
            ]);

            setCurrentDossier(dossier);
            const mapped: Message[] = history.map((m: any) => {
                let content = m.content;
                if (m.role === 'assistant') {
                    try {
                        const parsed = JSON.parse(m.content);
                        if (parsed && typeof parsed === 'object' && parsed.text) {
                            content = parsed.text;
                        }
                    } catch (_) {
                        // leave content as-is
                    }
                }

                return {
                    id: m.id,
                    role: m.role,
                    content,
                    created_at: m.created_at,
                } as Message;
            });

            setMessages(mapped);

        } catch (error: any) {
            console.error('Failed to load chat history:', error);
            setMessages([{ role: 'assistant', content: '**Failed to load history.**\n\nPlease try again.' }]);
        } finally {
            setLoadingChatHistory(false);
        }
    }, []);

    const handleSendMessage = useCallback(() => {
        if (!input.trim()) return;
        const newMsg: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, newMsg]);
        setInput('');
        setIsLoading(true);

        // Simulation
        setTimeout(() => {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "Analysis complete. The data suggests a **significant correlation** between the inventory turnover and the Q3 regional marketing spend.\n\nWould you like me to visualize the outliers?"
            }]);
            setIsLoading(false);
        }, 1200);
    }, [input]);

    const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setView('chat');
        setMessages([]);

        try {
            // Phase 1: Upload
            setUploadProgress({ phase: 'uploading', fileName: file.name });
            const uploadData = await fileService.uploadFileOnly(file);

            // Phase 2: Analysis
            setUploadProgress({ phase: 'analyzing', fileName: file.name });
            const analysisData = await fileService.createDossier(uploadData.file_id);

            setActiveChatId(analysisData.chat_id);
            setCurrentDossier(analysisData.dossier);
            
            // Reload chats and clear loading
            await loadUserChats();
            setUploadProgress({ phase: null });

        } catch (error) {
            console.error(error);
            setUploadProgress({ phase: null });
            setMessages([{ 
                role: 'assistant', 
                content: "**ERROR:** Uplink or Analysis failed. Please try again." 
            }]);
        }
    }, [loadUserChats]);

    const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);

    // --- SUB-COMPONENTS ---

    const SidebarItem = React.memo(({ item }: { item: ChatType }) => {
        const isActive = activeChatId === item.id;
        return (
            <button
                onClick={() => handleLoadChat(item.id)}
                className={`
                    w-full group flex flex-col gap-1.5 p-3 rounded-lg transition-all duration-200 border
                    ${isActive
                        ? 'bg-rose-500/10 border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]'
                        : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/5'}
                `}
            >
                <div className="flex items-center justify-between w-full">
                    <span className={`text-[13px] font-medium truncate tracking-tight ${isActive ? 'text-rose-100' : 'text-slate-400 group-hover:text-slate-200'}`}>
                        {item.title.substring(0, 24)}{item.title.length > 24 ? '...' : ''}
                    </span>
                    <span className="text-[9px] text-slate-600 font-mono opacity-60">{formatTimeAgo(item.created_at)}</span>
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
    });

    const MessageBubble = React.memo(({ msg, idx }: { msg: Message; idx: number }) => (
        <div key={idx} className={`flex gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {/* Assistant Avatar */}
            {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                    <Rose size={16} className="text-rose-500" />
                </div>
            )}

            {/* Bubble */}
            <div className={`
                px-6 py-4 rounded-2xl text-sm leading-7 shadow-lg backdrop-blur-sm max-w-[85%] border
                ${msg.role === 'assistant'
                    ? 'bg-[#0a0a0b] border-white/5 text-slate-300 rounded-tl-none'
                    : 'bg-zinc-100 border-white/10 text-zinc-900 font-medium rounded-tr-none'}
            `}>
                <div className={`prose prose-sm max-w-none ${msg.role === 'assistant' ? 'prose-invert prose-p:text-slate-300 prose-headings:text-white prose-strong:text-rose-400' : ''}`}>
                    <ReactMarkdown>
                        {msg.content}
                    </ReactMarkdown>
                </div>
            </div>

            {/* User Avatar */}
            {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={16} className="text-slate-300" />
                </div>
            )}
        </div>
    ));

    return (
        <div className="flex h-screen bg-[#050505] text-slate-200 overflow-hidden font-sans selection:bg-rose-500/30">

            {/* Background Texture */}
            <div className="fixed inset-0 bg-grid-pattern opacity-[0.03] pointer-events-none"></div>
            <div className="fixed inset-0 bg-gradient-to-b from-black via-transparent to-rose-950/5 pointer-events-none"></div>

            {/* --- UPLOAD PROGRESS OVERLAY --- */}
            {uploadProgress.phase && (
                <div className="fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-50 animate-in fade-in duration-300">
                    <div className="bg-[#09090b] border border-white/10 rounded-2xl p-12 max-w-md w-full shadow-2xl">
                        {/* Animated Icon */}
                        <div className="relative w-20 h-20 mx-auto mb-8">
                            <div className="absolute inset-0 border-4 border-rose-500/20 rounded-full"></div>
                            <div className="absolute inset-0 border-4 border-transparent border-t-rose-500 rounded-full animate-spin"></div>
                            <div className="absolute inset-3 flex items-center justify-center">
                                {uploadProgress.phase === 'uploading' ? (
                                    <FileSpreadsheet className="text-rose-500" size={28} />
                                ) : (
                                    <Cpu className="text-rose-500 animate-pulse" size={28} />
                                )}
                            </div>
                        </div>

                        {/* Status Text */}
                        <div className="text-center space-y-3">
                            <h3 className="text-white font-bold text-lg">
                                {uploadProgress.phase === 'uploading' ? 'Secure Uplink' : 'Intelligence Processing'}
                            </h3>
                            <p className="text-slate-400 text-sm">
                                {uploadProgress.phase === 'uploading' 
                                    ? `Encrypting and uploading ${uploadProgress.fileName}...`
                                    : 'Initializing Data Agent for analysis...'}
                            </p>
                            
                            {/* Progress dots */}
                            <div className="flex items-center justify-center gap-1.5 pt-4">
                                <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-2 h-2 bg-rose-500 rounded-full animate-bounce"></div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* --- SIDEBAR --- */}
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
                        onClick={handleNewChat}
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
                        isSidebarOpen ? <SidebarItem key={item.id} item={item} /> : (
                            <div 
                                key={item.id} 
                                onClick={() => handleLoadChat(item.id)}
                                className="w-9 h-9 mx-auto mb-2 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center hover:border-rose-500/50 cursor-pointer text-slate-500 hover:text-rose-500 transition-colors"
                            >
                                {item.type === 'excel' ? <FileSpreadsheet size={14} /> : <Database size={14} />}
                            </div>
                        )
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
                                <button onClick={logout} className="p-2 hover:bg-rose-500/10 hover:text-rose-500 rounded-lg transition-colors">
                                    <LogOut size={16} />
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-4 items-center">
                            <Activity size={16} className="text-emerald-500 animate-pulse" />
                            <button onClick={logout} className="hover:text-rose-500 transition-colors"><LogOut size={18} /></button>
                        </div>
                    )}
                </div>
            </aside>

            {/* --- MAIN STAGE --- */}
            <main className="flex-1 flex flex-col relative min-w-0 bg-[#050505]">

                {/* Header */}
                <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[#050505]/80 backdrop-blur-md z-20">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={toggleSidebar}
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

                {/* --- CONTENT VIEWER --- */}
                <div className="flex-1 relative overflow-hidden">

                    {/* 1. HOME VIEW */}
                    {view === 'home' && (
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
                                        onClick={handleNewChat}
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
                    )}

                    {/* 2. CHAT VIEW */}
                    {view === 'chat' && (
                        <div className="absolute inset-0 flex flex-col bg-[#050505]">
                            {/* Feed */}
                            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scrollbar-thin">
                                {loadingChatHistory ? (
                                    <div className="flex items-center justify-center h-full">
                                        <div className="text-center space-y-4">
                                            <div className="relative w-16 h-16 mx-auto">
                                                <div className="absolute inset-0 border-4 border-rose-500/20 rounded-full"></div>
                                                <div className="absolute inset-0 border-4 border-transparent border-t-rose-500 rounded-full animate-spin"></div>
                                            </div>
                                            <p className="text-slate-400 text-sm font-mono">Restoring session...</p>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        {currentDossier && (
                                            <DossierView dossier={currentDossier} onClose={() => setCurrentDossier(null)} />
                                        )}
                                        {messages.map((msg, idx) => (
                                            <MessageBubble key={msg.id || idx} msg={msg} idx={idx} />
                                        ))}

                                        {isLoading && (
                                            <div className="flex gap-4 max-w-4xl mx-auto">
                                                <div className="w-8 h-8 rounded-lg bg-rose-500/10 flex items-center justify-center mt-1 border border-rose-500/20">
                                                    <Rose size={16} className="text-rose-500" />
                                                </div>
                                                <div className="px-6 py-4 rounded-2xl bg-[#0a0a0b] border border-white/5 rounded-tl-none flex items-center gap-1.5">
                                                    <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                                    <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                                    <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-bounce"></div>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>

                            {/* Input Area */}
                            {!loadingChatHistory && (
                                <div className="p-6">
                                    <div className="max-w-4xl mx-auto relative group">
                                        <div className="absolute -inset-0.5 bg-gradient-to-r from-rose-500/20 to-indigo-500/20 rounded-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 blur"></div>
                                        <div className="relative flex items-center bg-[#0a0a0b] border border-white/10 rounded-xl p-1.5 shadow-2xl">
                                            <div className="pl-4 pr-3 text-slate-500">
                                                <Command size={18} />
                                            </div>
                                            <input
                                                type="text"
                                                value={input}
                                                onChange={(e) => setInput(e.target.value)}
                                                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                                placeholder="Enter tactical command or query..."
                                                className="flex-1 bg-transparent text-white placeholder:text-slate-600 focus:outline-none py-3 font-medium"
                                                disabled={isLoading}
                                                autoFocus
                                            />
                                            <button
                                                onClick={handleSendMessage}
                                                disabled={!input.trim() || isLoading}
                                                className="p-2.5 bg-white text-black rounded-lg hover:bg-rose-500 hover:text-white transition-all disabled:opacity-0 disabled:scale-90"
                                            >
                                                <Send size={16} strokeWidth={2.5} />
                                            </button>
                                        </div>
                                        <div className="text-center mt-3">
                                            <p className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">
                                                Secure Channel • End-to-End Encrypted • Local Processing
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* 3. WIZARD MODAL */}
                    {view === 'wizard' && (
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-xl flex items-center justify-center p-4 z-50 animate-in fade-in duration-300">
                            <div className="w-full max-w-3xl bg-[#09090b] border border-white/10 rounded-[2rem] shadow-2xl relative overflow-hidden">

                                {/* Modal Header */}
                                <div className="p-8 border-b border-white/5 flex justify-between items-start bg-white/[0.02]">
                                    <div>
                                        <h2 className="text-2xl font-serif text-white mb-2">Configure New Uplink</h2>
                                        <p className="text-slate-400 text-sm">Select a data protocol to initialize the agent.</p>
                                    </div>
                                    <button onClick={() => setView('home')} className="text-slate-500 hover:text-white transition-colors">
                                        <X size={24} />
                                    </button>
                                </div>

                                {/* Modal Content */}
                                <div className="p-10 grid grid-cols-2 gap-6">
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
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

                                <input type="file" hidden ref={fileInputRef} onChange={handleFileUpload} />
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};