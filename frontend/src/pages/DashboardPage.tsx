import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

import { useAuth } from '../contexts/AuthContext';
import { ChatType, Dossier, Message } from '../types';
import { chatService } from '../services/chat';
import { fileService } from '../services/files';

import { UploadProgressOverlay } from '../components/dashboard/UploadProgressOverlay';
import { Sidebar } from '../components/dashboard/Sidebar';
import { Header } from '../components/dashboard/Header';
import { HomeView } from '../components/dashboard/HomeView';
import { ChatView } from '../components/dashboard/ChatView';
import { WizardModal } from '../components/dashboard/WizardModal';





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

    const handleFileUploadClick = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);



    return (
        <div className="flex h-screen bg-[#050505] text-slate-200 overflow-hidden font-sans selection:bg-rose-500/30">
            {/* Background Texture */}
            <div className="fixed inset-0 bg-grid-pattern opacity-[0.03] pointer-events-none"></div>
            <div className="fixed inset-0 bg-gradient-to-b from-black via-transparent to-rose-950/5 pointer-events-none"></div>

            {/* Upload Progress Overlay */}
            <UploadProgressOverlay uploadProgress={uploadProgress} />

            {/* Sidebar */}
            <Sidebar
                isSidebarOpen={isSidebarOpen}
                userChats={userChats}
                activeChatId={activeChatId}
                onNewChat={handleNewChat}
                onLoadChat={handleLoadChat}
                onLogout={logout}
            />

            {/* Main Stage */}
            <main className="flex-1 flex flex-col relative min-w-0 bg-[#050505]">
                {/* Header */}
                <Header
                    isSidebarOpen={isSidebarOpen}
                    view={view}
                    onToggleSidebar={toggleSidebar}
                />

                {/* Content Viewer */}
                <div className="flex-1 relative overflow-hidden">
                    {/* Home View */}
                    {view === 'home' && <HomeView onNewChat={handleNewChat} />}

                    {/* Chat View */}
                    {view === 'chat' && (
                        <ChatView
                            messages={messages}
                            isLoading={isLoading}
                            input={input}
                            loadingChatHistory={loadingChatHistory}
                            currentDossier={currentDossier}
                            scrollRef={scrollRef}
                            onInputChange={setInput}
                            onSendMessage={handleSendMessage}
                            onCloseDossier={() => setCurrentDossier(null)}
                        />
                    )}

                    {/* Wizard Modal */}
                    {view === 'wizard' && (
                        <WizardModal
                            onClose={() => setView('home')}
                            onFileUpload={handleFileUploadClick}
                        />
                    )}
                </div>
            </main>

            {/* Hidden file input */}
            <input type="file" hidden ref={fileInputRef} onChange={handleFileUpload} />
        </div>
    );
};