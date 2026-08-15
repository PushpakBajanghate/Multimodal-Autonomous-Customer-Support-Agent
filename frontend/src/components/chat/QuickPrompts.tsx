'use client';

import React from 'react';

interface QuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPTS = [
  { label: '📦 Track Order #9', text: 'Please track the status of my order #9' },
  { label: '💰 Refund Order #9', text: 'I would like to request a refund for order #9' },
  { label: '❌ Cancel Order #34', text: 'Can you please cancel my order #34?' },
  { label: '📍 Change Address', text: 'I need to update my shipping address to 742 Evergreen Terrace' },
  { label: '📋 My Order History', text: 'Show all my past and active orders' }
];

export const QuickPrompts: React.FC<QuickPromptsProps> = ({
  onSelectPrompt,
  disabled = false
}) => {
  return (
    <div className="px-4 py-2 bg-slate-900/60 border-t border-slate-800/80 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
      <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-500 shrink-0 select-none mr-1">
        Quick Inquiries:
      </span>
      <div className="flex items-center gap-1.5">
        {PROMPTS.map((p, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(p.text)}
            className="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/90 hover:bg-slate-700 active:bg-slate-600 text-slate-300 hover:text-white border border-slate-700/50 hover:border-slate-600 transition-all disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
};
