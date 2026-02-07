import React, { useState, memo } from 'react';
import { Rose, User, Send, Command, ChevronDown, ChevronUp, Download } from 'lucide-react';
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
    onActionClick: (action: string) => void;
}

export const MessageTable: React.FC<{ data: any[] }> = memo(({ data }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    
    if (!data || data.length === 0) return null;
    
    const headers = Object.keys(data[0]);
    const ROW_LIMIT = 10;
    const hasMore = data.length > ROW_LIMIT;
    
    const displayedData = isExpanded ? data : data.slice(0, ROW_LIMIT);

    const downloadCSV = () => {
        const csvContent = [
            headers.join(','),
            ...data.map(row => 
                headers.map(header => {
                    const value = row[header];
                    // Handle values that contain commas or quotes by wrapping in quotes
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        return `"${value.replace(/"/g, '""')}"`;
                    }
                    return value;
                }).join(',')
            )
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `query_results_${Date.now()}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="mt-4 rounded-lg border border-white/10 bg-black/20 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-white/[0.03] border-b border-white/5">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                        Query Results ({data.length} rows)
                    </span>
                </div>
                <button
                    onClick={downloadCSV}
                    className="p-1.5 text-slate-600 hover:text-rose-400 hover:bg-rose-500/5 rounded transition-all"
                    title="Download as CSV"
                >
                    <Download size={14} />
                </button>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="bg-white/5 text-rose-500 font-mono text-[10px] uppercase">
                        <tr>
                            {headers.map(h => (
                                <th key={h} className="px-4 py-2.5 border-b border-white/10 whitespace-nowrap">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="text-slate-300">
                        {displayedData.map((row, i) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                                {headers.map(h => (
                                    <td key={h} className="px-4 py-2 whitespace-nowrap text-xs">
                                        {row[h]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Expansion Toggle */}
            {hasMore && (
                <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full py-2 flex items-center justify-center gap-2 text-[10px] font-mono uppercase tracking-widest text-rose-500/80 hover:text-rose-400 hover:bg-rose-500/10 border-t border-white/5 transition-all"
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp size={12} />
                            Collapse View
                        </>
                    ) : (
                        <>
                            <ChevronDown size={12} />
                            View {data.length - ROW_LIMIT} More Rows
                        </>
                    )}
                </button>
            )}
        </div>
    );
});

export const ChatView: React.FC<ChatViewProps> = memo(({
    messages,
    isLoading,
    input,
    loadingChatHistory,
    currentDossier,
    scrollRef,
    onInputChange,
    onSendMessage,
    onActionClick
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
                            <DossierView dossier={currentDossier} onActionClick={onActionClick} />
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
});