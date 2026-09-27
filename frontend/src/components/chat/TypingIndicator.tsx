'use client';

import React from 'react';
import { AuraBrandMark } from './AuraBrandMark';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="my-1 flex max-w-[85%] animate-fade-in items-end gap-2.5 self-start">
      <AuraBrandMark className="aura-message-mark mb-0.5 shrink-0" />

      <div className="flex items-center gap-1.5 rounded-[18px] rounded-bl-[5px] border border-[#eeecf3] bg-[#faf9fc] px-4 py-3 shadow-sm">
        <span className="h-2 w-2 animate-bounce rounded-full bg-[#8a78e5] [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[#a394ee] [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[#c0b5fb]" />
        <span className="ml-1.5 select-none text-[11px] font-medium text-[#9692a5]">
          Aura Support is typing...
        </span>
      </div>
    </div>
  );
};
