import React from 'react';

interface StepProps {
  number: string;
  title: string;
  desc: string;
}

export const Step: React.FC<StepProps> = ({ number, title, desc }) => (
  <div className="flex gap-8 group text-left">
    <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 font-mono text-xl font-bold group-hover:bg-rose-500 group-hover:text-black transition-all">
      {number}
    </div>
    <div className="pt-2">
      <h4 className="text-xl font-bold mb-2 text-slate-100 group-hover:text-rose-400 transition-colors">
        {title}
      </h4>
      <p className="text-slate-400 leading-relaxed font-light">{desc}</p>
    </div>
  </div>
);
