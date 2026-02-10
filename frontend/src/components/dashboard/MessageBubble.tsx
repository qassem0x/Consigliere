import React, { memo } from 'react';
import { Rose, User, Layers } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types';
import { MessageSteps, StreamingStatusIndicator } from './MessageSteps';
import { cn } from '../../lib/utils';

interface MessageBubbleProps {
    msg: Message;
    idx: number;
    showSteps?: boolean;
    isSelected?: boolean;
    onClick?: () => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = memo(({ msg, idx, showSteps = true, isSelected, onClick }) => {
    const isAssistant = msg.role === 'assistant';
    const hasSteps = msg.steps && msg.steps.length > 0;
    const isStreaming = msg.streamingStatus && msg.streamingStatus !== 'complete';

    return (
        <div
            key={idx}
            onClick={onClick}
            className={cn(
                "flex gap-4 max-w-4xl mx-auto mb-6",
                isAssistant ? "justify-start" : "justify-end",
                onClick ? "cursor-pointer group" : ""
            )}
        >
            <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0 border mt-1",
                isAssistant
                    ? isSelected
                        ? "bg-primary/10 border-primary text-primary"
                        : "bg-background border-border text-muted-foreground group-hover:border-primary/50 group-hover:text-primary transition-colors"
                    : "bg-secondary text-secondary-foreground border-transparent"
            )}>
                {isAssistant ? <Rose size={14} /> : <User size={14} />}
            </div>

            <div className={cn("flex flex-col relative max-w-[90%]", isAssistant ? "items-start" : "items-end")}>

                {/* Streaming status indicator */}
                {isAssistant && isStreaming && (
                    <StreamingStatusIndicator status={msg.streamingStatus} currentStep={msg.currentStep} />
                )}

                <div className={cn(
                    "px-4 py-3 rounded-lg text-sm shadow-sm border",
                    isAssistant
                        ? isSelected
                            ? "bg-card text-card-foreground border-primary/50 ring-1 ring-primary/20"
                            : "bg-card text-card-foreground border-border group-hover:border-primary/30 transition-colors"
                        : "bg-primary text-primary-foreground border-transparent"
                )}>
                    <div className={cn(
                        "prose prose-sm max-w-none",
                        isAssistant ? "prose-invert" : "prose-invert text-primary-foreground"
                    )}>
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>

                    {isAssistant && hasSteps && !showSteps && (
                        <div className="mt-3 pt-2 border-t flex justify-end">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onClick?.();
                                }}
                                className={cn(
                                    "flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium uppercase tracking-wide transition-colors",
                                    isSelected
                                        ? "bg-primary text-primary-foreground"
                                        : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                                )}
                            >
                                <Layers size={12} />
                                {isSelected ? 'Viewing Results' : 'View Results'}
                            </button>
                        </div>
                    )}
                </div>

                {isAssistant && hasSteps && showSteps && (
                    <div className="w-full mt-4 pl-4 animate-in fade-in slide-in-from-top-2">
                        <div className="flex items-center gap-2 mb-2 ml-2">
                            <Layers size={12} className="text-muted-foreground" />
                            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                                Analysis Feed
                            </span>
                            <div className="h-px flex-1 bg-border ml-2" />
                        </div>

                        <div className="border-l ml-2 pl-4">
                            <MessageSteps steps={msg.steps!} related_code={msg.related_code} />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
});