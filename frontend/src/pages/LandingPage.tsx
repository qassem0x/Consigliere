import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Rose,
    FileSpreadsheet,
    Database,
    Braces,
    FileText,
    Zap,
    ArrowRight,
    BarChart3,
    Terminal,
    Container,
    Cpu,
    LogOut,
    User as UserIcon
} from 'lucide-react';
import { BackgroundDecor, FeatureCard, Step } from '../components';
import { useTranslation } from '../contexts/TranslationContext';
import { useAuth } from '../contexts/AuthContext';

export const LandingPage: React.FC = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const { user, logout } = useAuth();

    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
        return () => observer.disconnect();
    }, []);

    return (
        <div className="min-h-screen relative">
            <BackgroundDecor />

            {/* Navigation */}
            <div className="fixed top-8 left-0 w-full z-50 px-4">
                <nav className="mx-auto w-full md:w-[95%] lg:w-[90%] xl:w-[85%] px-8 py-4 flex items-center justify-between backdrop-blur-2xl border border-white/10 bg-black/60 rounded-[2rem] shadow-[0_20px_50px_rgba(0,0,0,0.5)] transition-all">
                    <div
                        className="flex items-center gap-4 group cursor-pointer flex-shrink-0"
                        onClick={() => window.scrollTo(0, 0)}
                    >
                        <div className="w-10 h-10 rounded-xl bg-rose-500 flex items-center justify-center group-hover:rotate-12 transition-transform shadow-[0_0_20px_rgba(244,63,94,0.3)]">
                            <Rose className="w-6 h-6 text-black" />
                        </div>
                        <span className="font-serif text-2xl tracking-tighter text-rose-500 hidden sm:block">
                            {t.title}
                        </span>
                    </div>
                    
                    <div className="hidden lg:flex items-center gap-8 text-[10px] font-mono font-medium uppercase tracking-[0.2em] text-slate-400">
                        <a href="#features" className="hover:text-rose-500 transition-colors">
                            {t.nav.features}
                        </a>
                        <a href="#how-it-works" className="hover:text-rose-500 transition-colors">
                            {t.nav.process}
                        </a>
                        <a href="#enterprise" className="hover:text-rose-500 transition-colors">
                            {t.nav.enterprise}
                        </a>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* 2. LOGIC FIX: Check if User exists */}
                        {user ? (
                            // LOGGED IN VIEW
                            <div className="flex items-center gap-4">
                                <div className="hidden md:flex flex-col items-end mr-2">
                                    <span className="text-[10px] font-mono font-bold text-rose-500 uppercase tracking-widest">
                                        {user.full_name}
                                    </span>
                                    <span className="text-[8px] font-mono text-slate-500 uppercase tracking-widest">
                                        Active Session
                                    </span>
                                </div>
                                
                                <button
                                    onClick={logout}
                                    className="p-2.5 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-all"
                                    title="Logout"
                                >
                                    <LogOut size={18} />
                                </button>
                                
                                <button
                                    onClick={() => navigate('/dashboard')}
                                    className="hidden sm:flex items-center gap-2 px-6 py-2.5 bg-rose-500 text-black rounded-xl hover:bg-rose-400 transition-all active:scale-95 shadow-[0_0_20px_rgba(244,63,94,0.3)] text-[10px] font-mono font-black tracking-[0.1em]"
                                >
                                    <span>DASHBOARD</span>
                                    <ArrowRight size={14} />
                                </button>
                            </div>
                        ) : (
                            // LOGGED OUT VIEW
                            <>
                                <button
                                    onClick={() => navigate('/login')}
                                    className="px-6 py-2.5 text-[10px] font-mono font-bold text-slate-400 hover:text-white uppercase tracking-widest transition-colors"
                                >
                                    {t.nav.login}
                                </button>
                                <button
                                    onClick={() => navigate('/register')}
                                    className="px-6 py-2.5 bg-white/5 border border-white/10 hover:bg-white/10 text-[10px] font-mono font-bold text-white uppercase tracking-widest rounded-xl transition-all"
                                >
                                    {t.nav.register}
                                </button>
                                <button
                                    onClick={() => navigate('/dashboard')}
                                    className="hidden sm:block px-8 py-2.5 bg-rose-500 text-black rounded-xl hover:bg-rose-400 transition-all active:scale-95 shadow-[0_0_20px_rgba(244,63,94,0.3)] text-[10px] font-mono font-black tracking-[0.1em]"
                                >
                                    {t.nav.start}
                                </button>
                            </>
                        )}
                    </div>
                </nav>
            </div>

            {/* ... Rest of your component (Hero, Ticker, Features, etc) ... */}
            <section className="relative pt-40 md:pt-30 pb-16 px-8 flex flex-col items-center text-center overflow-hidden">
                <div className="absolute inset-0 -z-10 overflow-hidden pointer-events-none opacity-20">
                    <img
                        src="https://images.unsplash.com/photo-1551288049-bbda38257531?q=80&w=2048&auto=format&fit=crop"
                        alt="Hero Background"
                        className="w-full h-full object-cover grayscale mix-blend-overlay scale-110 blur-[3px]"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0b]/0 via-[#0a0a0b]/60 to-[#0a0a0b]"></div>
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#0a0a0b_100%)]"></div>
                </div>

                <div className="max-w-5xl relative z-10 w-full">
                    <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-full border border-rose-500/20 bg-rose-500/10 text-rose-500 text-[10px] font-mono font-medium mb-8 animate-fade-in backdrop-blur-xl tracking-[0.25em] uppercase">
                        <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></div>
                        {t.hero.status}
                    </div>
                    <div className="mb-6 reveal">
                        <p className="text-rose-500/90 font-mono text-xs md:text-sm font-light uppercase tracking-[0.5em] italic drop-shadow-[0_0_10px_rgba(244,63,94,0.2)]">
                            {t.hero.tagline}
                        </p>
                    </div>
                    <h1 className="text-5xl md:text-7xl lg:text-8xl font-serif leading-[1.1] mb-8 tracking-tight text-white reveal">
                        {t.hero.headline} <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-rose-600 to-rose-400 inline-block pb-2 drop-shadow-sm">
                            {t.hero.headlineSpan}
                        </span>
                    </h1>
                    <p className="text-lg md:text-xl text-slate-400 mb-10 max-w-3xl mx-auto leading-relaxed reveal font-light">
                        {t.hero.subheadline}
                    </p>

                    {/* Tech Nodes Row */}
                    <div className="flex flex-wrap justify-center gap-4 mb-14 reveal">
                        <div className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-all group">
                            <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                            <span className="text-[10px] font-mono font-bold text-slate-300 group-hover:text-emerald-400 tracking-[0.2em] uppercase">
                                {t.hero.nodes.excel}
                            </span>
                        </div>
                        <div className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:border-blue-500/30 hover:bg-blue-500/5 transition-all group">
                            <Database className="w-4 h-4 text-blue-500" />
                            <span className="text-[10px] font-mono font-bold text-slate-300 group-hover:text-blue-400 tracking-[0.2em] uppercase">
                                {t.hero.nodes.db}
                            </span>
                        </div>
                        <div className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:border-amber-500/30 hover:bg-amber-500/5 transition-all group">
                            <Braces className="w-4 h-4 text-amber-500" />
                            <span className="text-[10px] font-mono font-bold text-slate-300 group-hover:text-amber-400 tracking-[0.2em] uppercase">
                                {t.hero.nodes.json}
                            </span>
                        </div>
                        <div className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group">
                            <FileText className="w-4 h-4 text-indigo-500" />
                            <span className="text-[10px] font-mono font-bold text-slate-300 group-hover:text-indigo-400 tracking-[0.2em] uppercase">
                                {t.hero.nodes.docs}
                            </span>
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center reveal mb-16">
                        <button
                            onClick={() => navigate(user ? '/dashboard' : '/register')}
                            className="px-10 py-4 bg-rose-500 text-black text-lg font-mono font-black rounded-[1.25rem] hover:bg-rose-400 hover:shadow-[0_0_40px_rgba(244,63,94,0.35)] transition-all flex items-center justify-center gap-3 group uppercase tracking-widest w-full sm:w-auto"
                        >
                            {t.hero.ctaPrimary}
                            <Zap className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        </button>
                        <button className="px-10 py-4 bg-white/5 border border-white/10 text-white text-lg font-bold rounded-[1.25rem] hover:bg-white/10 transition-all backdrop-blur-sm flex items-center gap-3 w-full sm:w-auto">
                            {t.hero.ctaSecondary}
                            <ArrowRight className="w-5 h-5 opacity-40" />
                        </button>
                    </div>
                </div>
            </section>

            {/* Ticker */}
            <div className="w-full bg-rose-500/5 border-y border-white/5 py-4 overflow-hidden whitespace-nowrap">
                <div className="flex gap-24 animate-drift-horizontal text-[11px] font-mono font-medium tracking-[0.3em] text-rose-500/70 uppercase">
                    <span>{t.ticker.insights}</span>
                    <span>{t.ticker.active}</span>
                    <span>{t.ticker.uptime}</span>
                    <span>{t.ticker.latency}</span>
                    <span>{t.ticker.encrypted}</span>
                    <span>{t.ticker.insights}</span>
                </div>
            </div>

            {/* Features Section */}
            <section id="features" className="py-32 px-8 relative">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-20 reveal">
                        <h2 className="text-4xl md:text-6xl font-serif mb-8 text-white tracking-tight">
                            {t.features.headline}
                        </h2>
                        <p className="text-slate-400 max-w-4xl mx-auto text-xl font-light leading-relaxed">
                            {t.features.subheadline}
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 reveal">
                        <FeatureCard icon={Container} title={t.features.f1.t} desc={t.features.f1.d} />
                        <FeatureCard icon={Terminal} title={t.features.f2.t} desc={t.features.f2.d} />
                        <FeatureCard icon={Container} title={t.features.f3.t} desc={t.features.f3.d} />
                        <FeatureCard icon={BarChart3} title={t.features.f4.t} desc={t.features.f4.d} />
                        <FeatureCard icon={Cpu} title={t.features.f5.t} desc={t.features.f5.d} />
                        <FeatureCard icon={Rose} title={t.features.f6.t} desc={t.features.f6.d} />
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section id="how-it-works" className="py-32 px-8 relative overflow-hidden bg-black/40">
                <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-24">
                    <div className="flex-1 reveal">
                        <h2 className="text-4xl md:text-6xl font-serif mb-12 text-white leading-[1.1] tracking-tight text-left">
                            {t.howItWorks.headline}
                        </h2>
                        <div className="space-y-16">
                            <Step number="01" title={t.howItWorks.s1.t} desc={t.howItWorks.s1.d} />
                            <Step number="02" title={t.howItWorks.s2.t} desc={t.howItWorks.s2.d} />
                            <Step number="03" title={t.howItWorks.s3.t} desc={t.howItWorks.s3.d} />
                        </div>
                    </div>
                    <div
                        className="flex-1 bg-gradient-to-br from-rose-500/10 via-black to-black p-12 rounded-[4rem] border border-white/10 reveal relative shadow-2xl"
                    >
                        <div className="absolute inset-0 bg-grid opacity-20 rounded-[4rem]"></div>
                        <div className="space-y-10 relative z-10 text-left">
                            <div className="p-6 rounded-[2rem] bg-white/5 border border-white/10 animate-pulse">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-10 h-10 rounded-full bg-slate-700"></div>
                                    <div className="h-5 w-40 bg-slate-700 rounded-full"></div>
                                </div>
                                <div className="h-3.5 w-full bg-slate-800 rounded-full mb-3"></div>
                                <div className="h-3.5 w-3/4 bg-slate-800 rounded-full"></div>
                            </div>
                            <div className="p-8 rounded-[2rem] bg-rose-500/10 border border-rose-500/30 shadow-[0_0_60px_rgba(244,63,94,0.12)] ml-12">
                                <div className="flex items-center gap-4 mb-4">
                                    <Rose className="w-8 h-8 text-rose-500" />
                                    <span className="text-[10px] font-mono font-bold text-rose-500 tracking-[0.3em] uppercase">
                                        SECURE_AGENT
                                    </span>
                                </div>
                                <p className="text-base text-slate-100 leading-relaxed italic font-light">
                                    "Dossier analysis complete. Your local rows show a 15% inventory leakage in the Southern warehouse. No data was sent to the cloud for this calculation."
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-20 px-8 border-t border-white/5 bg-black/70 backdrop-blur-3xl">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-16 text-slate-500 text-sm mb-16">
                        <div className="flex items-center gap-5">
                            <div className="w-12 h-12 rounded-2xl bg-rose-500/20 flex items-center justify-center">
                                <Rose className="w-8 h-8 text-rose-500" />
                            </div>
                            <span className="font-serif text-3xl tracking-tight text-rose-500">{t.title}</span>
                        </div>
                        <div className="flex flex-wrap justify-center gap-16 font-mono font-medium uppercase tracking-[0.3em] text-[11px]">
                            <a href="#" className="hover:text-white transition-colors">
                                Architecture
                            </a>
                            <a href="#" className="hover:text-white transition-colors">
                                Privacy
                            </a>
                            <a href="#" className="hover:text-white transition-colors">
                                Docker
                            </a>
                        </div>
                        <div className="flex items-center gap-5 bg-white/5 px-8 py-3 rounded-full border border-white/5">
                            <span className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_20px_rgba(16,185,129,0.7)]"></span>
                            <span className="text-[11px] font-mono uppercase tracking-[0.4em] font-medium">
                                Local Node: Sovereign
                            </span>
                        </div>
                    </div>
                    <div className="text-center text-slate-700 text-xs font-mono uppercase tracking-[0.6em]">
                        © 2024 Strategic Intelligence Labs. Absolute Privacy. Absolute Clarity.
                    </div>
                </div>
            </footer>
        </div>
    );
};