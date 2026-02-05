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
    <div className="fixed inset-0 -z-20 overflow-hidden pointer-events-none">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0f0f10] to-[#0a0a0b]"></div>
      <div 
        className="absolute w-[800px] h-[800px] rounded-full opacity-10 bg-rose-500/20 blur-[120px] transition-transform duration-300 ease-out"
        style={{ 
          transform: `translate(${mousePos.x - 400}px, ${mousePos.y - 400}px)`,
        }}
      />
      <div className="absolute inset-0 bg-grid opacity-[0.12]"></div>
      <div className="absolute -top-[20%] -left-[10%] w-[60%] h-[60%] bg-rose-500/10 blur-[150px] rounded-full animate-drift"></div>
      <div className="absolute top-[40%] -right-[10%] w-[50%] h-[50%] bg-blue-500/5 blur-[120px] rounded-full animate-drift" style={{ animationDirection: 'reverse', animationDuration: '35s' }}></div>
      <div className="absolute -bottom-[10%] left-[20%] w-[40%] h-[40%] bg-rose-500/5 blur-[100px] rounded-full animate-pulse-glow"></div>
    </div>
  );
};
