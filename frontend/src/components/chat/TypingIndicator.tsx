'use client';

import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-end gap-2.5 max-w-[85%] self-start animate-fade-in my-1">
      {/* Bot Mini Avatar */}
      <div className="w-7 h-7 rounded-full bg-indigo-950 border border-indigo-700/60 flex items-center justify-center text-xs shrink-0 mb-0.5 shadow-sm">
        ✨
      </div>

      <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-slate-800 border border-slate-700/50 shadow-sm flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 rounded-full bg-sky-400 animate-bounce" />
        <span className="text-[11px] text-slate-400 font-medium ml-1.5 select-none">
          Aura is typing...
        </span>
      </div>
    </div>
  );
};
