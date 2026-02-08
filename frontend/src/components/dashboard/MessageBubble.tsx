import React, { useState, memo } from 'react';
import { 
    Rose, User, Code2, Copy, Check, BarChart3, Table2, 
    FileText, AlertCircle, TrendingUp, Activity, Layers, Terminal
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message, StepResult } from '../../types';
import { MessageTable } from './ChatView';

interface MessageBubbleProps {
    msg: Message;
    idx: number;
}

const TacticalCodeBlock: React.FC<{ code: string; type: string }> = memo(({ code, type }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="mt-3 group/code">
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 text-[10px] font-mono text-slate-500 hover:text-rose-400 transition-colors bg-black/20 px-3 py-1.5 rounded border border-white/5 hover:border-white/10 w-full"
            >
                <Terminal size={12} className="opacity-60" />
                <span className="uppercase tracking-wide flex-1 text-left">
                    {type} Protocol
                </span>
                <span className="text-slate-600 hover:text-white transition-colors">
                    {isOpen ? 'Close Source' : 'View Source'}
                </span>
            </button>

            {isOpen && (
                <div className="mt-2 rounded border border-white/10 bg-[#0a0a0b] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="flex items-center justify-between px-3 py-1 bg-white/[0.03] border-b border-white/5">
                        <span className="text-[9px] font-mono text-slate-600 uppercase tracking-wider">Python Shell</span>
                        <button onClick={handleCopy}>
                            {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} className="text-slate-500 hover:text-white" />}
                        </button>
                    </div>
                    <div className="overflow-x-auto p-3 custom-scrollbar max-h-[300px]">
                        <pre className="text-[11px] font-mono leading-relaxed text-slate-400">
                            <code>{code}</code>
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
});

const TimelineStep: React.FC<{ step: StepResult; isLast: boolean }> = memo(({ step, isLast }) => {
    const getIcon = () => {
        switch (step.step_type) {
            case 'chart': return <BarChart3 size={12} />;
            case 'table': return <Table2 size={12} />;
            case 'metric': return <TrendingUp size={12} />;
            default: return <Activity size={12} />;
        }
    };

    return (
        <div className="relative pl-6 pb-8 last:pb-0 group">
            {!isLast && (
                <div className="absolute left-[11px] top-6 bottom-0 w-[1px] bg-white/5 group-hover:bg-rose-500/20 transition-colors duration-500" />
            )}
            
            <div className={`
                absolute left-0 top-1 w-[22px] h-[22px] rounded-full border bg-[#0a0a0b] flex items-center justify-center shadow-sm z-10 transition-colors duration-300
                ${step.type === 'error' 
                    ? 'text-red-400 border-red-500/30' 
                    : 'text-slate-500 border-white/10 group-hover:border-rose-500/30 group-hover:text-rose-500'}
            `}>
                {step.type === 'error' ? <AlertCircle size={12} /> : getIcon()}
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Step {step.step_number}
                    </span>
                    <span className="text-[10px] text-slate-600 font-mono">
                        {step.step_type}
                    </span>
                </div>
                
                <div className="text-xs text-slate-300 -mt-1 font-medium">
                    {step.step_description}
                </div>

                <div className="bg-black/20 border border-white/5 rounded-lg overflow-hidden shadow-sm hover:border-white/10 transition-colors">
                    {step.type === 'image' && (
                        <div className="p-1">
                             <img 
                                src={`http://localhost:8000${step.data}`} 
                                alt="Analysis Result"
                                className="w-full rounded border border-white/5"
                            />
                        </div>
                    )}
                    
                    {step.type === 'table' && (
                        <div className="overflow-x-auto">
                            <MessageTable data={step.data} compact />
                        </div>
                    )}
                    
                    {step.type === 'text' && (
                        <div className="p-3 text-xs text-slate-400 font-mono whitespace-pre-wrap leading-relaxed">
                            {step.data}
                        </div>
                    )}
                    
                    {step.type === 'error' && (
                        <div className="p-3 text-xs text-red-400 bg-red-500/5 font-mono border-t border-red-500/10">
                            Error: {step.data}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});

const ImageGridStep: React.FC<{ steps: StepResult[]; isLast: boolean }> = memo(({ steps, isLast }) => {
    return (
        <div className="relative pl-6 pb-8 last:pb-0 group">
            {!isLast && (
                <div className="absolute left-[11px] top-6 bottom-0 w-[1px] bg-white/5 group-hover:bg-rose-500/20 transition-colors duration-500" />
            )}
            
            <div className="absolute left-0 top-1 w-[22px] h-[22px] rounded-full border bg-[#0a0a0b] flex items-center justify-center shadow-sm z-10 transition-colors duration-300 text-slate-500 border-white/10 group-hover:border-rose-500/30 group-hover:text-rose-500">
                <BarChart3 size={12} />
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Steps {steps[0].step_number} - {steps[steps.length - 1].step_number}
                    </span>
                    <span className="text-[10px] text-slate-600 font-mono">
                        Visual Analysis
                    </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                    {steps.map((step, i) => (
                        <div key={i} className="flex flex-col gap-2">
                            <div className="bg-black/20 border border-white/5 rounded-lg overflow-hidden shadow-sm hover:border-white/10 transition-colors h-full">
                                <div className="p-1 h-full">
                                    <img 
                                        src={`http://localhost:8000${step.data}`} 
                                        alt={`Step ${step.step_number}`}
                                        className="w-full h-full object-cover rounded border border-white/5"
                                    />
                                </div>
                            </div>
                            <span className="text-[9px] text-slate-500 font-mono pl-1">
                                Fig {step.step_number}: {step.step_description}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
});

export const MessageBubble: React.FC<MessageBubbleProps> = memo(({ msg, idx }) => {
    const isAssistant = msg.role === 'assistant';
    const hasSteps = msg.steps && msg.steps.length > 0;

    const renderSteps = () => {
        if (!msg.steps) return null;
        
        const rendered = [];
        let i = 0;
        
        while (i < msg.steps.length) {
            const current = msg.steps[i];
            const isLast = i === msg.steps.length - 1;

            if (current.type === 'image') {
                const group = [current];
                let j = i + 1;
                while (j < msg.steps.length && msg.steps[j].type === 'image') {
                    group.push(msg.steps[j]);
                    j++;
                }

                if (group.length > 1) {
                    const isGroupLast = j === msg.steps.length;
                    rendered.push(
                        <ImageGridStep key={`group-${i}`} steps={group} isLast={isGroupLast} />
                    );
                    i = j;
                    continue;
                }
            }

            rendered.push(
                <TimelineStep key={`step-${i}`} step={current} isLast={isLast} />
            );
            i++;
        }

        return rendered;
    };

    return (
        <div key={idx} className={`flex gap-4 max-w-4xl mx-auto mb-8 ${isAssistant ? 'justify-start' : 'justify-end'}`}>
            <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-lg border
                ${isAssistant 
                    ? 'bg-[#0a0a0b] border-rose-500/30 text-rose-500 shadow-rose-500/10' 
                    : 'bg-white/5 border-white/10 text-slate-400'}
            `}>
                {isAssistant ? <Rose size={14} /> : <User size={14} />}
            </div>

            <div className={`flex flex-col relative max-w-[95%] ${isAssistant ? 'items-start' : 'items-end'}`}>
                
                <div className={`
                    px-5 py-4 rounded-2xl text-sm leading-6 shadow-2xl backdrop-blur-md border w-full
                    ${isAssistant
                        ? 'bg-[#0a0a0b]/90 border-white/10 text-slate-300 rounded-tl-none'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-50 font-medium rounded-tr-none'}
                `}>
                    <div className="prose prose-sm max-w-none prose-invert prose-p:leading-relaxed prose-a:text-rose-400">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                </div>

                {isAssistant && hasSteps && (
                    <div className="w-full mt-6 pl-4 animate-in fade-in slide-in-from-top-4 duration-500">
                        <div className="flex items-center gap-2 mb-6 ml-2">
                            <Layers size={12} className="text-rose-500/60" />
                            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                                Tactical Analysis Feed
                            </span>
                            <div className="h-[1px] flex-1 bg-gradient-to-r from-white/10 to-transparent ml-2" />
                        </div>

                        <div className="border-l border-white/5 ml-2 pl-2">
                            {renderSteps()}
                        </div>

                        {msg.related_code && (
                            <div className="ml-4 pl-2 border-l border-white/5 pb-2">
                                <TacticalCodeBlock code={msg.related_code.code} type={msg.related_code.type} />
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
});