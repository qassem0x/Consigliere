import React, { useState, useEffect } from 'react';
import { X, Brain, MessageSquare, Loader2 } from 'lucide-react';
import { api } from '../../utils/api';

interface MemoryModalProps {
    isOpen: boolean;
    onClose: () => void;
    chatId: string | null;
}

export const MemoryModal: React.FC<MemoryModalProps> = ({ isOpen, onClose, chatId }) => {
    const [summary, setSummary] = useState<string>('');
    const [messages, setMessages] = useState<any[]>([]);
    const [messageCount, setMessageCount] = useState<number>(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && chatId) {
            loadMemory();
        }
    }, [isOpen, chatId]);

    const loadMemory = async () => {
        if (!chatId) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const res = await api.get(`/chats/${chatId}/memory`);
            setSummary(res.data.summary);
            setMessages((res.data.recent_messages || []).reverse());
            setMessageCount(res.data.message_count || 0);
        } catch (err: any) {
            console.error('Failed to load memory:', err);
            setError('Failed to load memory');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center">
            <div 
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />
            
            <div className="relative w-full max-w-2xl max-h-[80vh] bg-[#1a1a1e] border border-white/10 rounded-xl shadow-2xl animate-in fade-in zoom-in-95 duration-200 flex flex-col">
                <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                    <div className="flex items-center gap-2">
                        <Brain size={18} className="text-rose-500" />
                        <h2 className="text-base font-semibold text-white">Agent Memory</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-6">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 size={24} className="text-rose-500 animate-spin" />
                        </div>
                    ) : error ? (
                        <div className="text-red-400 text-sm text-center py-8">{error}</div>
                    ) : (
                        <>
                            <div>
                                <h3 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-2">
                                    Conversation Summary
                                </h3>
                                <div className="bg-black/30 border border-white/5 rounded-lg p-4">
                                    <p className="text-sm text-slate-300 leading-relaxed">
                                        {summary || 'No summary available yet.'}
                                    </p>
                                </div>
                            </div>

                            <div>
                                <h3 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                    <MessageSquare size={12} />
                                    Recent Messages ({messageCount} total, showing {messages.length})
                                </h3>
                                <div className="space-y-2 max-h-64 overflow-y-auto">
                                    {messages.map((msg, idx) => (
                                        <div 
                                            key={idx}
                                            className={`border-l-2 pl-3 py-2 ${
                                                msg.role === 'user' 
                                                    ? 'border-rose-500/50' 
                                                    : 'border-emerald-500/50'
                                            }`}
                                        >
                                            <div className="text-xs font-mono text-slate-500 mb-1">
                                                {msg.role === 'user' ? 'You' : 'Agent'}
                                            </div>
                                            <p className="text-sm text-slate-300">
                                                {msg.content}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <div className="px-5 py-4 border-t border-white/10">
                    <button
                        onClick={onClose}
                        className="w-full py-2.5 bg-white/10 text-white text-sm font-medium rounded-lg hover:bg-white/20 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};
