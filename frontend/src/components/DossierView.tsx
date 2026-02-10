import React from 'react';
import { Cpu, ArrowRight, Target, ShieldAlert, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Dossier } from '../types';

interface DossierViewProps {
  dossier: Dossier;
  title?: string;
  onActionClick: (action: string) => void;
}

export const DossierView: React.FC<DossierViewProps> = ({ dossier, title, onActionClick }) => {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* Main Card */}
      <div className="rounded-xl border bg-card text-card-foreground shadow-sm">

        {/* Card Header */}
        <div className="flex flex-col space-y-1.5 p-6 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-md">
                <FileText size={20} className="text-primary" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold tracking-tight text-lg">
                  {title || 'Unknown Source'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Classified Intelligence Briefing
                </p>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-2 px-2.5 py-0.5 rounded-full border bg-secondary text-secondary-foreground text-xs font-medium">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span>Analysis Complete</span>
            </div>
          </div>
        </div>

        {/* Card Content */}
        <div className="p-6 pt-6">
          <div className="text-sm">
            <ReactMarkdown
              components={{
                h1: ({ node, ...props }) => <h1 className="scroll-m-20 text-3xl font-bold tracking-tight mb-4" {...props} />,
                h2: ({ node, ...props }) => <h2 className="scroll-m-20 border-b pb-2 text-2xl font-semibold tracking-tight mt-8 mb-4 first:mt-0" {...props} />,
                h3: ({ node, ...props }) => <h3 className="scroll-m-20 text-xl font-semibold tracking-tight mt-6 mb-2" {...props} />,
                p: ({ node, ...props }) => <p className="leading-7 [&:not(:first-child)]:mt-6 text-muted-foreground" {...props} />,
                ul: ({ node, ...props }) => <ul className="my-6 ml-6 list-disc [&>li]:mt-2 text-muted-foreground" {...props} />,
                ol: ({ node, ...props }) => <ol className="my-6 ml-6 list-decimal [&>li]:mt-2 text-muted-foreground" {...props} />,
                li: ({ node, ...props }) => <li className="leading-7" {...props} />,
                blockquote: ({ node, ...props }) => <blockquote className="mt-6 border-l-2 pl-6 italic text-muted-foreground" {...props} />,
                code: ({ node, className, ...props }) => {
                  // A simpler check for inline vs block code could be used if needed, 
                  // but typically ReactMarkdown handles this via the presence of `children` usually being a string.
                  // For simplicity in this shadcn port, we apply a generic style.
                  return <code className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold" {...props} />
                },
                pre: ({ node, ...props }) => <pre className="mb-4 mt-6 overflow-x-auto rounded-lg border bg-muted p-4" {...props} />,
                a: ({ node, ...props }) => <a className="font-medium text-primary underline underline-offset-4 hover:no-underline" {...props} />,
              }}
            >
              {dossier.briefing}
            </ReactMarkdown>
          </div>

          {/* Key Entities Tags */}
          {dossier.key_entities && dossier.key_entities.length > 0 && (
            <div className="mt-8 pt-6 border-t flex flex-col gap-3">
              <span className="text-xs font-medium text-muted-foreground flex items-center gap-2 uppercase tracking-wider">
                <Target size={14} className="text-primary" /> Key Vectors
              </span>
              <div className="flex flex-wrap gap-2">
                {dossier.key_entities.map((entity, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recommended Actions */}
      {dossier.recommended_actions && dossier.recommended_actions.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2 px-1">
            <ShieldAlert size={14} className="text-primary" /> Recommended Protocols
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {dossier.recommended_actions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => onActionClick(action)}
                className="group relative flex items-center justify-between space-x-4 rounded-lg border bg-card p-4 text-card-foreground shadow-sm transition-all hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <span className="text-sm font-medium leading-none group-hover:underline-offset-4 line-clamp-2 text-left">
                  {action}
                </span>
                <ArrowRight size={16} className="text-muted-foreground group-hover:translate-x-1 transition-transform duration-200" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};