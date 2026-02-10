import React, { useState, memo } from 'react';
import {
    Check, Copy, BarChart3, Table2, AlertCircle, TrendingUp, Activity, Terminal, Loader2, Zap
} from 'lucide-react';
import { StepResult } from '../../types';
import { MessageTable } from './ChatView';
import { ImageModal } from './ImageModal';
import { cn } from '../../lib/utils';

export const StreamingStatusIndicator: React.FC<{ status?: string; currentStep?: number }> = memo(({ status, currentStep }) => {
    return (
        <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-muted/50 border rounded-md text-xs">
            {status === 'planning' && (
                <>
                    <Loader2 size={14} className="text-primary animate-spin" />
                    <span className="font-medium text-foreground">Planning...</span>
                </>
            )}
            {status === 'executing' && (
                <>
                    <Zap size={14} className="text-amber-500 animate-pulse" />
                    <span className="font-medium text-foreground">Executing Step {currentStep}</span>
                </>
            )}
            {status === 'error' && (
                <>
                    <AlertCircle size={14} className="text-destructive" />
                    <span className="font-medium text-destructive">Error</span>
                </>
            )}
        </div>
    );
});

export const TacticalCodeBlock: React.FC<{ code: string; type: string }> = memo(({ code, type }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="mt-2 group/code border rounded-md overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 w-full px-3 py-2 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
            >
                <Terminal size={12} className="text-muted-foreground" />
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground flex-1">
                    {type} Protocol
                </span>
                <span className="text-[10px] text-muted-foreground group-hover/code:text-primary transition-colors">
                    {isOpen ? 'Fold' : 'Unfold'}
                </span>
            </button>

            {isOpen && (
                <div className="bg-[#0a0a0b] border-t relative group/block">
                    <div className="absolute right-2 top-2 opacity-0 group-hover/block:opacity-100 transition-opacity">
                        <button onClick={handleCopy} className="p-1 rounded bg-muted/20 hover:bg-muted/40 text-muted-foreground hover:text-foreground transition-colors">
                            {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                        </button>
                    </div>
                    <div className="overflow-x-auto p-3 max-h-[300px] scrollbar-thin">
                        <pre className="text-[11px] font-mono leading-relaxed text-slate-300">
                            <code>{code}</code>
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
});

export const TimelineStep: React.FC<{ step: StepResult; isLast: boolean; onImageClick?: (url: string) => void }> = memo(({ step, isLast, onImageClick }) => {
    const getIcon = () => {
        switch (step.step_type) {
            case 'chart': return <BarChart3 size={12} />;
            case 'table': return <Table2 size={12} />;
            case 'metric': return <TrendingUp size={12} />;
            default: return <Activity size={12} />;
        }
    };

    return (
        <div className="relative pl-6 pb-6 last:pb-0 group">
            {!isLast && (
                <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border max-h-full" />
            )}

            <div className={cn(
                "absolute left-0 top-1 w-[22px] h-[22px] rounded-full border flex items-center justify-center z-10 bg-background transition-colors",
                step.type === 'error'
                    ? "border-destructive text-destructive"
                    : "border-border text-muted-foreground group-hover:border-primary group-hover:text-primary"
            )}>
                {step.type === 'error' ? <AlertCircle size={12} /> : getIcon()}
            </div>

            <div className="flex flex-col gap-2">
                <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Step {step.step_number}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground/60">
                        {step.step_type}
                    </span>
                </div>

                <div className="text-xs text-foreground font-medium">
                    {step.step_description}
                </div>

                <div className="mt-1 border rounded-md overflow-hidden bg-card shadow-sm">
                    {step.type === 'image' && (
                        <div className="p-1 bg-muted/20">
                            <img
                                src={`http://localhost:8000${step.data}`}
                                alt="Analysis Result"
                                className="w-full rounded border cursor-zoom-in hover:brightness-95 transition-all"
                                onClick={() => onImageClick?.(`http://localhost:8000${step.data}`)}
                            />
                        </div>
                    )}

                    {step.type === 'table' && (
                        <div className="overflow-x-auto">
                            <MessageTable data={step.data} compact />
                        </div>
                    )}

                    {step.type === 'text' && (
                        <div className="p-3 text-xs text-muted-foreground font-mono whitespace-pre-wrap leading-relaxed bg-muted/30">
                            {step.data}
                        </div>
                    )}

                    {step.type === 'error' && (
                        <div className="p-3 text-xs text-destructive bg-destructive/5 font-mono border-t border-destructive/10">
                            Error: {step.data}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});

export const ImageGridStep: React.FC<{ steps: StepResult[]; isLast: boolean; onImageClick?: (url: string) => void }> = memo(({ steps, isLast, onImageClick }) => {
    return (
        <div className="relative pl-6 pb-6 last:pb-0 group">
            {!isLast && (
                <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border" />
            )}

            <div className="absolute left-0 top-1 w-[22px] h-[22px] rounded-full border bg-background flex items-center justify-center z-10 text-muted-foreground group-hover:border-primary group-hover:text-primary transition-colors">
                <BarChart3 size={12} />
            </div>

            <div className="flex flex-col gap-2">
                <div className="flex items-baseline justify-between">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Steps {steps[0].step_number} - {steps[steps.length - 1].step_number}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground/60">
                        Visual Analysis
                    </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                    {steps.map((step, i) => (
                        <div key={i} className="flex flex-col gap-1">
                            <div className="border rounded-md overflow-hidden bg-muted/20 hover:border-primary/50 transition-colors h-full">
                                <div className="p-1 h-full">
                                    <img
                                        src={`http://localhost:8000${step.data}`}
                                        alt={`Step ${step.step_number}`}
                                        className="w-full h-full object-cover rounded border cursor-zoom-in hover:brightness-95 transition-all"
                                        onClick={() => onImageClick?.(`http://localhost:8000${step.data}`)}
                                    />
                                </div>
                            </div>
                            <span className="text-[9px] text-muted-foreground font-mono pl-1 truncate">
                                Fig {step.step_number}: {step.step_description}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
});

interface MessageStepsProps {
    steps: StepResult[];
    related_code?: { type: string; code: string } | null;
}

export const MessageSteps: React.FC<MessageStepsProps> = memo(({ steps, related_code }) => {
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    const handleImageClick = (url: string) => {
        setSelectedImage(url);
    };
    const renderSteps = () => {
        if (!steps) return null;

        const rendered = [];
        let i = 0;

        while (i < steps.length) {
            const current = steps[i];
            const isLast = i === steps.length - 1;

            if (current.type === 'image') {
                const group = [current];
                let j = i + 1;
                while (j < steps.length && steps[j].type === 'image') {
                    group.push(steps[j]);
                    j++;
                }

                if (group.length > 1) {
                    const isGroupLast = j === steps.length;
                    rendered.push(
                        <ImageGridStep
                            key={`group-${i}`}
                            steps={group}
                            isLast={isGroupLast}
                            onImageClick={handleImageClick}
                        />
                    );
                    i = j;
                    continue;
                }
            }

            rendered.push(
                <TimelineStep
                    key={`step-${i}`}
                    step={current}
                    isLast={isLast}
                    onImageClick={handleImageClick}
                />
            );
            i++;
        }

        return rendered;
    };

    return (
        <div className="w-full">
            <div className="space-y-0">
                {renderSteps()}
            </div>

            {related_code && (
                <div className="mt-4 border-t pt-4">
                    <TacticalCodeBlock code={related_code.code} type={related_code.type} />
                </div>
            )}

            <ImageModal
                isOpen={!!selectedImage}
                imageUrl={selectedImage || ''}
                onClose={() => setSelectedImage(null)}
            />
        </div>
    );
});
