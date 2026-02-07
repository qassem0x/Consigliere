import React, { useState } from 'react';
import { Rose, User, Terminal, Code2, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types';
import { MessageTable } from './ChatView';

interface MessageBubbleProps {
    msg: Message;
    idx: number;
}

const TacticalCodeBlock: React.FC<{ code: string; type: string }> = ({ code, type }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="mt-4 group/code">
            {/* Compact Toggle - Only icon + text on same line */}
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 hover:text-rose-400 transition-colors mb-2"
            >
                <Code2 size={13} className="opacity-60" />
                <span className="uppercase tracking-wide">View {type} Code</span>
                <span className="text-slate-600 ml-1">({code.split('\n').length} lines)</span>
            </button>

            {/* Collapsible Code Block */}
            {isOpen && (
                <div className="rounded-lg border border-white/10 bg-[#0a0a0b] overflow-hidden">
                    {/* Header with copy button */}
                    <div className="flex items-center justify-between px-3 py-1.5 bg-white/[0.03] border-b border-white/5">
                        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider">
                            Generated Code
                        </span>
                        <button 
                            onClick={handleCopy}
                            className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-white transition-all"
                            title="Copy to Clipboard"
                        >
                            {copied ? (
                                <Check size={12} className="text-green-400" />
                            ) : (
                                <Copy size={12} />
                            )}
                        </button>
                    </div>

                    {/* Code Content */}
                    <div className="overflow-x-auto p-3 custom-scrollbar max-h-[300px] overflow-y-auto">
                        <pre className="text-[11px] font-mono leading-relaxed text-slate-300">
                            <code>{code}</code>
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({ msg, idx }) => {
    const isAssistant = msg.role === 'assistant';
    console.log(msg)
    return (
        <div key={idx} className={`flex gap-4 max-w-4xl mx-auto ${isAssistant ? 'justify-start' : 'justify-end'}`}>
            {/* Assistant Avatar */}
            {isAssistant && (
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center flex-shrink-0 mt-1 shadow-[0_0_15px_-3px_rgba(244,63,94,0.2)]">
                    <Rose size={16} className="text-rose-500" />
                </div>
            )}

            {/* Bubble */}
            <div className={`
                px-6 py-4 rounded-2xl text-sm leading-7 shadow-2xl backdrop-blur-sm max-w-[85%] border transition-all duration-300
                ${isAssistant
                    ? 'bg-[#0a0a0b]/90 border-white/10 text-slate-300 rounded-tl-none hover:border-white/20'
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-50 font-medium rounded-tr-none hover:bg-rose-500/15'}
            `}>
                {/* Text Content */}
                <div className={`prose prose-sm max-w-none ${isAssistant 
                    ? 'prose-invert prose-p:text-slate-300 prose-headings:text-white prose-strong:text-rose-400 prose-code:text-rose-300 prose-code:bg-rose-500/10 prose-code:px-1 prose-code:rounded' 
                    : 'prose-invert prose-p:text-rose-50/90'}`}>
                    <ReactMarkdown>
                        {msg.content}
                    </ReactMarkdown>
                </div>

                {/* --- VISUALIZATION LAYER --- */}
                
                {isAssistant && msg.imageData && (
                    <div className="mt-4 rounded-xl overflow-hidden border border-white/10 bg-black/50 p-1 relative group">
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none rounded-lg" />
                        <img 
                            src={`http://localhost:8000${msg.imageData}`} 
                            alt="Analysis Plot"
                            className="w-full h-auto rounded-lg shadow-lg"
                            onError={(e) => (e.currentTarget.style.display = 'none')}
                        />
                        <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/60 backdrop-blur-md rounded border border-white/10 text-[10px] font-mono text-rose-400 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
                            Figure Generated
                        </div>
                    </div>
                )}

                {isAssistant && msg.tableData && (
                    <MessageTable data={msg.tableData} />
                )}

                {/* Code Block - Now subtle and compact */}
                {isAssistant && msg.related_code && (
                    <TacticalCodeBlock 
                        code={msg.related_code.code} 
                        type={msg.related_code.type} 
                    />
                )}
            </div>

            {/* User Avatar */}
            {!isAssistant && (
                <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={16} className="text-slate-400" />
                </div>
            )}
        </div>
    );
};