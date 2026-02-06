import React from 'react';
import { Rose, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types';

interface MessageBubbleProps {
    msg: Message;
    idx: number;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ msg, idx }) => {
    return (
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
    );
};