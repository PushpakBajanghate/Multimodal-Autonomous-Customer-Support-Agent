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
    <div className="aura-prompts flex items-center gap-2 overflow-x-auto border-t border-[#f2f0f6] bg-white px-4 py-2.5 no-scrollbar sm:px-8">
      <span className="mr-1 shrink-0 select-none text-[10px] font-semibold uppercase tracking-[.12em] text-[#a19daf]">
        Quick actions
      </span>
      <div className="flex items-center gap-1.5">
        {PROMPTS.map((p, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(p.text)}
            className="shrink-0 cursor-pointer rounded-full border border-[#ece9f3] bg-[#fcfbfe] px-3 py-1.5 text-[10px] font-medium text-[#777388] transition-all hover:border-[#d9d2f5] hover:bg-[#f7f5ff] hover:text-[#5b4ac0] active:bg-[#f1efff] disabled:pointer-events-none disabled:opacity-40 sm:text-[11px]"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
};
