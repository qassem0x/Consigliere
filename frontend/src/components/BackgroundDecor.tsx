import React, { useEffect, useState } from 'react';

export const BackgroundDecor: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <>
      <style>
        {`
          @keyframes grid-scroll {
            0% { background-position: 0% 0%; }
            100% { background-position: 50px 50px; }
          }
          @keyframes float-slow {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            50% { transform: translate(20px, 30px) rotate(5deg); }
          }
          .animate-grid-scroll {
            animation: grid-scroll 20s linear infinite;
          }
        `}
      </style>

      <div className="fixed inset-0 -z-20 overflow-hidden pointer-events-none select-none bg-[#0a0a0b]">
        
        <div className="absolute inset-0 bg-gradient-to-b from-[#0f0f10] via-[#0f0f10] to-black"></div>

        <div 
          className="absolute inset-0 opacity-[0.07] animate-grid-scroll"
          style={{
            backgroundImage: `
              linear-gradient(to right, #888 1px, transparent 1px),
              linear-gradient(to bottom, #888 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
            maskImage: 'radial-gradient(ellipse 60% 60% at 50% 50%, black, transparent)',
            WebkitMaskImage: 'radial-gradient(ellipse 60% 60% at 50% 50%, black, transparent)',
          }}
        />

        <div 
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(#fff 1px, transparent 1px)`,
            backgroundSize: '20px 20px',
          }}
        />

        <div 
          className="absolute w-[800px] h-[800px] rounded-full opacity-20 bg-rose-500/30 blur-[100px] transition-transform duration-75 ease-out will-change-transform"
          style={{ 
            transform: `translate(${mousePos.x - 400}px, ${mousePos.y - 400}px)`,
          }}
        />

        <div 
          className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] bg-rose-500/10 blur-[120px] rounded-full"
          style={{ animation: 'float-slow 25s ease-in-out infinite' }}
        />
        <div 
          className="absolute top-[40%] -right-[10%] w-[40vw] h-[40vw] bg-blue-600/10 blur-[120px] rounded-full"
          style={{ animation: 'float-slow 30s ease-in-out infinite reverse' }}
        />
        
      </div>
    </>
  );
};