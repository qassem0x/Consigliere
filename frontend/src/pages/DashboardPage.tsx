import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ChatType, Dossier, Message } from '../types';
import { chatService } from '../services/chat';
import { fileService } from '../services/files';
import { fetchModel, API_BASE_URL } from '../utils/api';

import { UploadProgressOverlay } from '../components/dashboard/UploadProgressOverlay';
import { Sidebar } from '../components/dashboard/Sidebar';
import { Header } from '../components/dashboard/Header';
import { HomeView } from '../components/dashboard/HomeView';
import { ChatView } from '../components/dashboard/ChatView';
import { WizardModal } from '../components/dashboard/WizardModal';

export const DashboardPage: React.FC = () => {
    const { logout } = useAuth();

    // --- STATE MANAGEMENT ---
    const [view, setView] = useState<'home' | 'chat' | 'wizard'>('home');
    const [isSidebarOpen, setSidebarOpen] = useState(true);
    const [activeChatId, setActiveChatId] = useState<string | null>(null);
    const [userChats, setUserChats] = useState<ChatType[]>([]);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentDossier, setCurrentDossier] = useState<Dossier | null>(null);

    // Tracks upload or connection progress
    const [uploadProgress, setUploadProgress] = useState<{
        phase: 'uploading' | 'analyzing' | null;
        fileName?: string;
    }>({ phase: null });

    const [loadingChatHistory, setLoadingChatHistory] = useState(false);
    const [modelName, setModelName] = useState<string | undefined>(undefined);

    const [searchParams, setSearchParams] = useSearchParams();

    const scrollRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    // --- SCROLL HANDLING ---
    useEffect(() => {
        if (!scrollRef.current) return;
        if (messages.length > 0) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        } else {
            scrollRef.current.scrollTop = 0;
        }
    }, [messages]);

    // --- DATA LOADING ---
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

    useEffect(() => {
        fetchModel()
            .then(setModelName)
            .catch(err => console.error("Failed to fetch model:", err));
    }, []);

    const handleNewChat = useCallback(() => setView('wizard'), []);

    const handleDeleteChat = useCallback(async (chatId: string) => {
        try {
            await chatService.deleteChat(chatId);
            setUserChats(prev => prev.filter(chat => chat.id !== chatId));
            if (activeChatId === chatId) {
                setSearchParams({});
            }
        } catch (error) {
            console.error("Failed to delete chat:", error);
            alert("Failed to delete dossier. Please try again.");
        }
    }, [activeChatId, setSearchParams]);

    const handleUpdateSettings = useCallback(async (chatId: string, settings: { zero_leaks_mode: boolean; max_row_limit: number }) => {
        try {
            await chatService.updateChatSettings(chatId, settings);
            setUserChats(prev => prev.map(chat =>
                chat.id === chatId ? { ...chat, settings } : chat
            ));
        } catch (error) {
            console.error("Failed to update settings:", error);
            alert("Failed to update settings. Please try again.");
        }
    }, []);

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

            // Map backend messages to frontend format
            const mapped: Message[] = history.map((m: any) => {
                let content = m.content;
                let tableData = null;
                let imageData = null;
                let steps = null;
                let plan = null;

                if (m.role === 'assistant') {
                    try {
                        const parsed = JSON.parse(m.content);

                        if (parsed && typeof parsed === 'object') {
                            content = parsed.text || m.content;

                            // Multi-step response
                            if (parsed.steps && Array.isArray(parsed.steps)) {
                                steps = parsed.steps;
                                plan = parsed.plan;
                            }
                            // Single-step response (backward compatible)
                            else if (parsed.result) {
                                if (parsed.result.type === 'table') {
                                    tableData = parsed.result.data;
                                } else if (parsed.result.type === 'image') {
                                    imageData = parsed.result.data;
                                }
                            }
                        }
                    } catch (_) { }
                }

                return {
                    id: m.id,
                    role: m.role,
                    content,
                    created_at: m.created_at,
                    tableData,
                    imageData,
                    steps,
                    plan,
                    related_code: m.related_code,
                    prompt_tokens: m.prompt_tokens,
                    completion_tokens: m.completion_tokens,
                    total_tokens: m.total_tokens
                } as Message;
            });

            setMessages(mapped);

        } catch (error: any) {
            setActiveChatId(null);
            setView('home');
            setMessages([]);
            setCurrentDossier(null);
            setSearchParams({});
        } finally {
            setLoadingChatHistory(false);
        }
    }, []);

    // --- URL SYNC ---
    const handleChatSelect = useCallback((id: string) => {
        setSearchParams({ chatId: id });
    }, [setSearchParams]);

    useEffect(() => {
        const chatIdFromUrl = searchParams.get('chatId');

        if (chatIdFromUrl) {
            if (chatIdFromUrl !== activeChatId) {
                fetchChatData(chatIdFromUrl);
            }
        } else {
            if (activeChatId) {
                setActiveChatId(null);
                setMessages([]);
                setCurrentDossier(null);
                setView('home');
            }
        }
    }, [searchParams.get('chatId'), activeChatId, fetchChatData]);

    // --- MESSAGE PROCESSING (STREAMING) ---
    const processMessage = useCallback(async (text: string) => {
        if (!text.trim() || !activeChatId) return;

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        const userMsg: Message = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        const assistantMsgId = `temp-${Date.now()}`;
        const assistantMsg: Message = {
            id: assistantMsgId,
            role: 'assistant',
            content: '',
            steps: [],
            plan: null,
            related_code: null,
            streamingStatus: 'processing'
        };
        setMessages(prev => [...prev, assistantMsg]);

        try {
            const response = await fetch(`${API_BASE_URL}/messages/${activeChatId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ content: text }),
                signal: controller.signal
            });

            if (!response.ok) throw new Error('Failed to send message');

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            if (!reader) throw new Error('No response body');

            let buffer = '';
            let receivedFinalResult = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                if (controller.signal.aborted) {
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantMsgId
                            ? { ...msg, streamingStatus: 'cancelled' as const }
                            : msg
                    ));
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const chunk = JSON.parse(line);

                        if (chunk.type === 'step_start') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantMsgId
                                    ? { ...msg, content: msg.content || `${chunk.description}...`, streamingStatus: 'planning' as const }
                                    : msg
                            ));
                        }
                        else if (chunk.type === 'step_result') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantMsgId
                                    ? { ...msg, steps: [...(msg.steps || []), chunk.data] }
                                    : msg
                            ));
                        }
                        else if (chunk.type === 'token') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantMsgId
                                    ? { ...msg, content: (msg.content || '') + chunk.data, streamingStatus: 'streaming' as const }
                                    : msg
                            ));
                        }
                        else if (chunk.type === 'final_result') {
                            receivedFinalResult = true;
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantMsgId || msg.streamingStatus === 'complete'
                                    ? {
                                        ...msg,
                                        content: chunk.data.text,
                                        steps: chunk.data.steps || [],
                                        plan: chunk.data.plan || null,
                                        related_code: chunk.data.code ? { type: 'python', code: chunk.data.code } : null,
                                        streamingStatus: 'complete' as const,
                                        total_tokens: chunk.data.token_usage?.total_tokens,
                                        prompt_tokens: chunk.data.token_usage?.prompt_tokens,
                                        completion_tokens: chunk.data.token_usage?.completion_tokens,
                                    }
                                    : msg
                            ));
                        }
                        else if (chunk.type === 'error') {
                            setMessages(prev => prev.map(msg =>
                                msg.id === assistantMsgId
                                    ? {
                                        ...msg,
                                        content: `**Error:** ${chunk.message}`,
                                        streamingStatus: chunk.error_type === 'user_cancelled' ? 'cancelled' as const : 'error' as const
                                    }
                                    : msg
                            ));
                        }
                    } catch (parseError) {
                        console.error('Failed to parse chunk:', line, parseError);
                    }
                }
            }

            if (!receivedFinalResult && !controller.signal.aborted) {
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                        ? { ...msg, content: '**Error:** Response incomplete - server terminated early.', streamingStatus: 'error' as const }
                        : msg
                ));
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                        ? { ...msg, streamingStatus: 'cancelled' as const }
                        : msg
                ));
            } else {
                console.error("Message processing failed:", error);
                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                        ? { ...msg, content: '**Critical Error:** System failed to process request.', streamingStatus: 'error' as const }
                        : msg
                ));
            }
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    }, [activeChatId]);

    const handleCancelRequest = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    const handleSendMessage = useCallback(() => {
        const messageText = input.trim();
        if (messageText) {
            processMessage(messageText);
            setInput('');
        }
    }, [input, processMessage]);

    const handleRecommendedAction = useCallback((actionText: string) => {
        processMessage(actionText);
    }, [processMessage]);

    const handleFileUpload = useCallback(async (file: File, settings: { title?: string; zero_leaks_mode: boolean; max_row_limit: number }) => {
        setView('chat');
        setMessages([]);

        try {
            setUploadProgress({ phase: 'uploading', fileName: file.name });
            const uploadData = await fileService.uploadFileOnly(file);

            setUploadProgress({ phase: 'analyzing', fileName: file.name });
            const analysisData = await fileService.createDossier(uploadData.file_id, settings);

            setSearchParams({ chatId: analysisData.chat_id });
            await loadUserChats();
            setUploadProgress({ phase: null });

        } catch (error) {
            console.error(error);
            setUploadProgress({ phase: null });
            setMessages([{ role: 'assistant', content: "**ERROR:** Uplink or Analysis failed. Please try again." }]);
        }
    }, [loadUserChats, setSearchParams]);

    // --- NEW: DATABASE CONNECTION HANDLER ---
    const handleConnectDB = useCallback(async (dbData: any) => {
        // Switch view immediately to prepare for the chat
        setView('chat');
        setMessages([]);

        try {
            // Show the user we are working on it
            setUploadProgress({ phase: 'analyzing', fileName: dbData.name });

            const response = await fetch(`${API_BASE_URL}/connections`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(dbData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Connection failed');
            }

            const data = await response.json();

            // The backend creates the Connection, Dossier, and Chat automatically.
            // It returns the 'connection_id' which maps to the 'chat' for this connection.
            // We use this ID to switch context.
            setSearchParams({ chatId: data.connection_id });

            await loadUserChats();
            setUploadProgress({ phase: null });

        } catch (error: any) {
            console.error(error);
            setUploadProgress({ phase: null });
            // Show error in the chat window if connection fails
            setMessages([{
                role: 'assistant',
                content: `**ERROR:** Database connection failed. ${error.message}`
            }]);
        }
    }, [loadUserChats, setSearchParams]);

    const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);

    return (
        <div className="flex h-screen bg-[#050505] text-slate-200 overflow-hidden font-['Inter'] selection:bg-rose-500/30">
            {/* Ambient Background Effects */}
            <div className="fixed inset-0 bg-grid-pattern opacity-[0.03] pointer-events-none"></div>
            <div className="fixed inset-0 bg-gradient-to-b from-black via-transparent to-rose-950/5 pointer-events-none"></div>

            {/* Global Overlay for long-running processes */}
            <UploadProgressOverlay uploadProgress={uploadProgress} />

            <Sidebar
                isSidebarOpen={isSidebarOpen}
                userChats={userChats}
                activeChatId={activeChatId}
                onNewChat={handleNewChat}
                onLoadChat={handleChatSelect}
                onLogout={logout}
                onDeleteChat={handleDeleteChat}
                onUpdateSettings={handleUpdateSettings}
            />

            <main className="flex-1 flex flex-col relative min-w-0 bg-[#050505]">
                <Header
                    isSidebarOpen={isSidebarOpen}
                    view={view}
                    onToggleSidebar={toggleSidebar}
                    modelName={modelName}
                    chatTokenStats={view === 'chat' ? {
                        total: messages.reduce((acc, m) => acc + (m.total_tokens || 0), 0),
                        prompt: messages.reduce((acc, m) => acc + (m.prompt_tokens || 0), 0),
                        completion: messages.reduce((acc, m) => acc + (m.completion_tokens || 0), 0),
                        messages: messages.filter(m => m.role === 'assistant' && m.total_tokens).length
                    } : undefined}
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
                            sourceName={userChats.find(c => c.id === activeChatId)?.title || userChats.find(c => c.id === activeChatId)?.file?.filename || "Unknown Source"}
                            scrollRef={scrollRef}
                            onInputChange={setInput}
                            onSendMessage={handleSendMessage}
                            onActionClick={handleRecommendedAction}
                            onCancel={handleCancelRequest}
                        />
                    )}

                    {view === 'wizard' && (
                        <WizardModal
                            onClose={() => setView('home')}
                            onFileUpload={handleFileUpload}
                            onConnectDB={handleConnectDB}
                        />
                    )}
                </div>
            </main>
        </div>
    );
};