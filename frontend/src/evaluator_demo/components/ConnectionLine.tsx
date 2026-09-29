import React from 'react';

interface ConnectionLineProps {
  active: boolean; // True if data is currently flowing through this path
  completed: boolean; // True if the data flow has fully traversed
}

export default function ConnectionLine({ active, completed }: ConnectionLineProps) {
  return (
    <div className="relative w-[2px] h-6 bg-slate-800/60 mx-3.5 my-0.5 overflow-hidden rounded">
      {/* Completed line track */}
      <div 
        className={`absolute inset-0 bg-gradient-to-b from-emerald-500/40 to-sky-500/40 transition-all duration-500 ${
          completed ? 'opacity-100' : 'opacity-0'
        }`} 
      />
      
      {/* Flowing Particle */}
      {active && (
        <>
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes particleFlow {
              0% { transform: translateY(-120%); }
              100% { transform: translateY(220%); }
            }
          `}} />
          <div 
            className="absolute top-0 left-0 w-full h-[50%] bg-gradient-to-b from-sky-400 via-sky-300 to-transparent animate-[particleFlow_1s_infinite_linear]" 
          />
        </>
      )}
    </div>
  );
}
