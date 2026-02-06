import React from 'react';
import { Rose, User, Send, Command } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { DossierView } from '../DossierView';
import { Message } from '../../types';
import { MessageBubble } from './MessageBubble';

interface ChatViewProps {
    messages: Message[];
    isLoading: boolean;
    input: string;
    loadingChatHistory: boolean;
    currentDossier: any;
    scrollRef: React.RefObject<HTMLDivElement>;
    onInputChange: (value: string) => void;
    onSendMessage: () => void;
    onCloseDossier: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
    messages,
    isLoading,
    input,
    loadingChatHistory,
    currentDossier,
    scrollRef,
    onInputChange,
    onSendMessage,
    onCloseDossier
}) => {
    return (
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
                            <DossierView dossier={currentDossier} onClose={onCloseDossier} />
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
                                onChange={(e) => onInputChange(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && onSendMessage()}
                                placeholder="Enter tactical command or query..."
                                className="flex-1 bg-transparent text-white placeholder:text-slate-600 focus:outline-none py-3 font-medium"
                                disabled={isLoading}
                                autoFocus
                            />
                            <button
                                onClick={onSendMessage}
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
    );
};