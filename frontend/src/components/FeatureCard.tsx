import React from 'react';

interface FeatureCardProps {
  icon: any;
  title: string;
  desc: string;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({ icon: Icon, title, desc }) => (
  <div className="p-8 rounded-[2rem] bg-white/5 border border-white/10 hover:border-rose-500/50 hover:bg-white/[0.07] transition-all group backdrop-blur-sm text-left">
    <div className="w-14 h-14 rounded-2xl bg-rose-500/10 flex items-center justify-center mb-8 group-hover:scale-110 transition-transform group-hover:rotate-6">
      <Icon className="w-7 h-7 text-rose-500" />
    </div>
    <h3 className="text-xl font-bold mb-4 text-slate-100">{title}</h3>
    <p className="text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors font-light">
      {desc}
    </p>
  </div>
);
