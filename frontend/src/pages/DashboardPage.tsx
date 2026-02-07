import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
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
    const { logout } = useAuth();

    // UI State
    const [view, setView] = useState<'home' | 'chat' | 'wizard'>('home');
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const [activeChatId, setActiveChatId] = useState<string | null>(null);
    const [userChats, setUserChats] = useState<ChatType[]>([]);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentDossier, setCurrentDossier] = useState<Dossier | null>(null);
    const [uploadProgress, setUploadProgress] = useState<{
        phase: 'uploading' | 'analyzing' | null;
        fileName?: string;
    }>({ phase: null });
    const [loadingChatHistory, setLoadingChatHistory] = useState(false);

    const [searchParams, setSearchParams] = useSearchParams();

    const scrollRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- SCROLL FIX START ---
    // Intelligent Auto-scroll
    useEffect(() => {
        if (!scrollRef.current) return;

        // 1. If we have messages (Chat History), scroll to BOTTOM to see the latest
        if (messages.length > 0) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        } 
        // 2. If NO messages (Just uploaded a file / Reading Dossier), scroll to TOP
        else {
            scrollRef.current.scrollTop = 0;
        }
    }, [messages]);
    // --- SCROLL FIX END ---

    // Load Chats Sidebar
    const loadUserChats = useCallback(async () => {
        try {
            const chats: ChatType[] = await chatService.loadUserChats();
            setUserChats(chats);
        } catch (error: any) {
            console.error("Failed to load user chats:", error);
        }
    }, []);

    useEffect(() => {
        loadUserChats();
    }, [loadUserChats]);

    const handleNewChat = useCallback(() => setView('wizard'), []);

    const fetchChatData = useCallback(async (id: string) => {
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
                let tableData = null;
                let imageData = null;

                if (m.role === 'assistant') {
                    try {
                        const parsed = JSON.parse(m.content);
                        if (parsed && typeof parsed === 'object' && parsed.text) {
                            content = parsed.text;
                            if (parsed.result?.type === 'table') {
                                tableData = parsed.result.data;
                            } else if (parsed.result?.type === 'image') {
                                imageData = parsed.result.data;
                            }
                        }
                    } catch (_) {}
                }

                return {
                    id: m.id,
                    role: m.role,
                    content,
                    created_at: m.created_at,
                    tableData,
                    imageData,
                    related_code: m.related_code
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

    // 2. Interaction Handler: Passed to Sidebar. ONLY updates URL.
    const handleChatSelect = useCallback((id: string) => {
        setSearchParams({ chatId: id });
    }, [setSearchParams]);

    // 3. The "Brain": Watches URL changes and triggers the fetch
    useEffect(() => {
        const chatIdFromUrl = searchParams.get('chatId');
        if (chatIdFromUrl && chatIdFromUrl !== activeChatId) {
            fetchChatData(chatIdFromUrl);
        }
    }, [searchParams, activeChatId, fetchChatData]);


    const processMessage = useCallback(async (text: string) => {
        if (!text.trim() || !activeChatId) return;

        const userMsg: Message = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const res = await chatService.sendMessage(activeChatId, text);

            if (res.error) {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: '**Error:** Failed to process command.'
                }]);
                return;
            }

            const content_obj = JSON.parse(res.content);

            const assistantMsg: Message = {
                ...res, 
                content: content_obj.text, 
                tableData: content_obj.result?.type === 'table' ? content_obj.result.data : null,
                imageData: content_obj.result?.type === 'image' ? content_obj.result.data : null
            };

            setMessages(prev => [...prev, assistantMsg]);
        } catch (error) {
            console.error("Message processing failed:", error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '**Critical Error:** System failed to parse response.'
            }]);
        } finally {
            setIsLoading(false);
        }
    }, [activeChatId]);

    const handleSendMessage = useCallback(() => {
        processMessage(input);
        setInput('');
    }, [input, processMessage]);
    
    const handleRecommendedAction = useCallback((actionText: string) => {
        processMessage(actionText);
    }, [processMessage]);

    const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setView('chat');
        setMessages([]);

        try {
            setUploadProgress({ phase: 'uploading', fileName: file.name });
            const uploadData = await fileService.uploadFileOnly(file);

            setUploadProgress({ phase: 'analyzing', fileName: file.name });
            const analysisData = await fileService.createDossier(uploadData.file_id);

            // Update URL and let the Effect handle the loading
            setSearchParams({ chatId: analysisData.chat_id });
            
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
    }, [loadUserChats, setSearchParams]);

    const handleFileUploadClick = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);

    return (
        <div className="flex h-screen bg-[#050505] text-slate-200 overflow-hidden font-sans selection:bg-rose-500/30">
            <div className="fixed inset-0 bg-grid-pattern opacity-[0.03] pointer-events-none"></div>
            <div className="fixed inset-0 bg-gradient-to-b from-black via-transparent to-rose-950/5 pointer-events-none"></div>

            <UploadProgressOverlay uploadProgress={uploadProgress} />

            <Sidebar
                isSidebarOpen={isSidebarOpen}
                userChats={userChats}
                activeChatId={activeChatId}
                onNewChat={handleNewChat}
                onLoadChat={handleChatSelect} 
                onLogout={logout}
            />

            <main className="flex-1 flex flex-col relative min-w-0 bg-[#050505]">
                <Header
                    isSidebarOpen={isSidebarOpen}
                    view={view}
                    onToggleSidebar={toggleSidebar}
                />

                <div className="flex-1 relative overflow-hidden">
                    {view === 'home' && <HomeView onNewChat={handleNewChat} />}

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
                            onActionClick={handleRecommendedAction}
                        />
                    )}

                    {view === 'wizard' && (
                        <WizardModal
                            onClose={() => setView('home')}
                            onFileUpload={handleFileUploadClick}
                        />
                    )}
                </div>
            </main>

            <input type="file" hidden ref={fileInputRef} onChange={handleFileUpload} />
        </div>
    );
};