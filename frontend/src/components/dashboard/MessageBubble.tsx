import React, { useState, memo } from 'react';
import { Rose, User, Code2, Copy, Check, BarChart3, Table2, FileText, AlertCircle, TrendingUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message, StepResult } from '../../types';
import { MessageTable } from './ChatView';

interface MessageBubbleProps {
    msg: Message;
    idx: number;
}

const TacticalCodeBlock: React.FC<{ code: string; type: string; stepCount?: number }> = memo(({ code, type, stepCount }) => {
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
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 hover:text-rose-400 transition-colors mb-2"
            >
                <Code2 size={13} className="opacity-60" />
                <span className="uppercase tracking-wide">
                    View {type} Code
                    {stepCount && stepCount > 1 && ` (${stepCount} steps)`}
                </span>
                <span className="text-slate-600 ml-1">({code.split('\n').length} lines)</span>
            </button>

            {isOpen && (
                <div className="rounded-lg border border-white/10 bg-[#0a0a0b] overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-1.5 bg-white/[0.03] border-b border-white/5">
                        <span className="text-[10px] font-mono text-slate-600 uppercase tracking-wider">
                            Generated Code
                        </span>
                        <button 
                            onClick={handleCopy}
                            className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-white transition-all"
                            title="Copy to Clipboard"
                        >
                            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                        </button>
                    </div>

                    <div className="overflow-x-auto p-3 custom-scrollbar max-h-[300px] overflow-y-auto">
                        <pre className="text-[11px] font-mono leading-relaxed text-slate-300">
                            <code>{code}</code>
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
});

const StepBadge: React.FC<{ stepNumber: number; stepType: string }> = ({ stepNumber, stepType }) => {
    const getIcon = () => {
        switch (stepType) {
            case 'chart': return <BarChart3 size={10} />;
            case 'table': return <Table2 size={10} />;
            case 'metric': return <TrendingUp size={10} />;
            case 'summary': return <FileText size={10} />;
            default: return <FileText size={10} />;
        }
    };

    const getColor = () => {
        switch (stepType) {
            case 'chart': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
            case 'table': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
            case 'metric': return 'bg-green-500/10 text-green-400 border-green-500/20';
            case 'summary': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
            default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
        }
    };

    return (
        <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-mono uppercase tracking-wider ${getColor()}`}>
            {getIcon()}
            <span>Step {stepNumber}</span>
            <span className="opacity-60">• {stepType}</span>
        </div>
    );
};

const StepRenderer: React.FC<{ step: StepResult; index: number }> = memo(({ step, index }) => {
    return (
        <div className="mt-6 first:mt-4">
            {/* Step Header */}
            <div className="mb-3">
                <StepBadge stepNumber={step.step_number} stepType={step.step_type} />
                <p className="text-xs text-slate-400 mt-1.5 italic">{step.step_description}</p>
            </div>

            {/* Step Content */}
            <div className="relative">
                {/* Error */}
                {step.type === 'error' && (
                    <div className="flex items-start gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                        <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <p className="text-xs font-mono text-red-400">Step Execution Error</p>
                            <p className="text-sm text-red-300/80 mt-1">{step.data}</p>
                        </div>
                    </div>
                )}

                {/* Image/Chart */}
                {step.type === 'image' && (
                    <div className="rounded-xl overflow-hidden border border-white/10 bg-black/50 p-1 relative group">
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none rounded-lg" />
                        <img 
                            src={`http://localhost:8000${step.data}`} 
                            alt={step.description || `Step ${step.step_number} visualization`}
                            className="w-full h-auto rounded-lg shadow-lg"
                            onError={(e) => (e.currentTarget.style.display = 'none')}
                        />
                        {step.description && (
                            <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/60 backdrop-blur-md rounded border border-white/10 text-[10px] font-mono text-rose-400 uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
                                {step.description}
                            </div>
                        )}
                    </div>
                )}

                {/* Table */}
                {step.type === 'table' && step.data && (
                    <MessageTable data={step.data} />
                )}

                {/* Text/Metric */}
                {step.type === 'text' && (
                    <div className="p-4 bg-white/[0.02] border border-white/10 rounded-lg">
                        <pre className="text-sm text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                            {step.data}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
});

export const MessageBubble: React.FC<MessageBubbleProps> = memo(({ msg, idx }) => {
    const isAssistant = msg.role === 'assistant';
    const hasMultiSteps = msg.steps && msg.steps.length > 0;

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

                {/* MULTI-STEP RESULTS */}
                {isAssistant && hasMultiSteps && (
                    <div className="mt-4">
                        {msg.steps!.map((step, index) => (
                            <StepRenderer key={`${msg.id}-step-${step.step_number}`} step={step} index={index} />
                        ))}
                    </div>
                )}

                {/* SINGLE-STEP RESULTS (Backward Compatible) */}
                {isAssistant && !hasMultiSteps && (
                    <>
                        {msg.imageData && (
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

                        {msg.tableData && (
                            <MessageTable data={msg.tableData} />
                        )}
                    </>
                )}

                {/* ========================================== */}
                {/* CODE BLOCK */}
                {/* ========================================== */}
                {isAssistant && msg.related_code && (
                    <TacticalCodeBlock 
                        code={msg.related_code.code} 
                        type={msg.related_code.type}
                        stepCount={msg.related_code.steps}
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
});