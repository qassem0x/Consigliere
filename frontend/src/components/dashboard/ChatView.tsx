import React, { useState, memo, useEffect } from 'react';
import { Rose, Send, Command, ChevronDown, ChevronUp, Download, Layers } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { DossierView } from '../DossierView';
import { Message } from '../../types';
import { MessageBubble } from './MessageBubble';
import { MessageSteps } from './MessageSteps';
import { cn } from '../../lib/utils';

interface ChatViewProps {
    messages: Message[];
    isLoading: boolean;
    input: string;
    loadingChatHistory: boolean;
    currentDossier: any;
    sourceName?: string;
    scrollRef: React.RefObject<HTMLDivElement>;
    onInputChange: (value: string) => void;
    onSendMessage: () => void;
    onActionClick: (action: string) => void;
}

export const MessageTable: React.FC<{ data: any[]; compact?: boolean }> = memo(({ data, compact }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!data || data.length === 0) return null;

    const headers = Object.keys(data[0]);
    const ROW_LIMIT = compact ? 5 : 10;
    const hasMore = data.length > ROW_LIMIT;

    const displayedData = isExpanded ? data : data.slice(0, ROW_LIMIT);

    const downloadCSV = () => {
        const csvContent = [
            headers.join(','),
            ...data.map(row =>
                headers.map(header => {
                    const value = row[header];
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
        <div className="mt-4 rounded-md border bg-card text-card-foreground shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Query Results ({data.length} rows)
                    </span>
                </div>
                <button
                    onClick={downloadCSV}
                    className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                    title="Download as CSV"
                >
                    <Download size={14} />
                </button>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="bg-muted/50 text-muted-foreground font-medium text-xs uppercase">
                        <tr>
                            {headers.map(h => (
                                <th key={h} className="px-4 py-2 border-b whitespace-nowrap font-semibold">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {displayedData.map((row, i) => (
                            <tr key={i} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                                {headers.map(h => (
                                    <td key={h} className="px-4 py-2 whitespace-nowrap">
                                        {row[h]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {hasMore && (
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full py-2 flex items-center justify-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 border-t transition-colors"
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp size={12} />
                            Collapse
                        </>
                    ) : (
                        <>
                            <ChevronDown size={12} />
                            Show {data.length - ROW_LIMIT} More
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
    sourceName,
    scrollRef,
    onInputChange,
    onSendMessage,
    onActionClick
}) => {
    const [selectedMessageId, setSelectedMessageId] = useState<string | null>(
        messages[messages.length - 1]?.id || null
    );

    useEffect(() => {
        if (isLoading) {
            const lastMsg = messages[messages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
                setSelectedMessageId(lastMsg.id || null);
            }
        } else {
            if (!selectedMessageId && messages.length > 0) {
                const lastStepMsg = [...messages].reverse().find(m => m.role === 'assistant' && (m.steps?.length || 0) > 0);
                if (lastStepMsg) {
                    setSelectedMessageId(lastStepMsg.id || null);
                }
            }
        }
    }, [messages, isLoading, selectedMessageId]);

    const selectedMessage = messages.find(m => m.id === selectedMessageId);

    return (
        <div className="absolute inset-0 flex bg-background overflow-hidden">
            {/* Left Panel: Chat Stream */}
            <div className="w-[45%] flex flex-col border-r bg-background/50 relative z-10">
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
                    {loadingChatHistory ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center space-y-2">
                                <div className="animate-spin text-primary">
                                    <Rose size={24} />
                                </div>
                                <p className="text-muted-foreground text-xs">Restoring session...</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            {currentDossier && (
                                <DossierView
                                    dossier={currentDossier}
                                    title={sourceName}
                                    onActionClick={onActionClick}
                                />
                            )}
                            {messages.map((msg, idx) => (
                                <MessageBubble
                                    key={msg.id || idx}
                                    msg={msg}
                                    idx={idx}
                                    showSteps={false}
                                    isSelected={msg.id === selectedMessageId}
                                    onClick={() => setSelectedMessageId(msg.id || null)}
                                />
                            ))}
                        </>
                    )}
                </div>

                {/* Input Area */}
                {!loadingChatHistory && (
                    <div className="p-4 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                        <div className="relative flex items-center gap-2">
                            <div className="relative flex-1 group">
                                <div className="absolute inset-0 bg-primary/20 opacity-0 group-focus-within:opacity-100 rounded-lg blur transition-opacity" />
                                <div className="relative flex items-center bg-muted/50 border border-input rounded-lg px-3 shadow-sm group-focus-within:ring-1 group-focus-within:ring-ring">
                                    <Command size={16} className="text-muted-foreground shrink-0" />
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={(e) => onInputChange(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && onSendMessage()}
                                        placeholder="Type your instruction..."
                                        className="flex-1 bg-transparent text-sm px-3 py-3 focus:outline-none placeholder:text-muted-foreground"
                                        disabled={isLoading}
                                        autoFocus
                                    />
                                </div>
                            </div>
                            <button
                                onClick={onSendMessage}
                                disabled={!input.trim() || isLoading}
                                className={cn(
                                    "p-3 rounded-lg transition-all",
                                    input.trim() && !isLoading
                                        ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                                        : "bg-muted text-muted-foreground opacity-50 cursor-not-allowed"
                                )}
                            >
                                <Send size={16} />
                            </button>
                        </div>
                        <div className="px-1 py-1">
                            <span className="text-[10px] text-muted-foreground">
                                AI Analyst can make mistakes. Verify important information.
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Right Panel: Results & Steps */}
            <div className="flex-1 bg-muted/10 relative overflow-hidden flex flex-col">
                <div className="h-14 border-b flex items-center px-6 bg-background/50 backdrop-blur">
                    <Layers size={14} className="text-primary mr-2" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Analysis Protocol
                    </span>
                    {selectedMessageId && (
                        <span className="ml-auto text-[10px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                            ID: {selectedMessageId.substring(0, 8)}
                        </span>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
                    {selectedMessage ? (
                        selectedMessage.steps && selectedMessage.steps.length > 0 ? (
                            <div className="max-w-3xl mx-auto">
                                <MessageSteps
                                    steps={selectedMessage.steps}
                                    related_code={selectedMessage.related_code}
                                />
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-muted-foreground opacity-60">
                                <Command size={32} className="mb-4 text-muted-foreground/50" />
                                <p className="text-sm text-center max-w-xs">
                                    No tactical steps available for this message entry.
                                </p>
                            </div>
                        )
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground opacity-60">
                            <Layers size={48} className="mb-6 text-muted-foreground/40" />
                            <p className="text-sm uppercase tracking-widest">
                                Select a mission log to view details
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});