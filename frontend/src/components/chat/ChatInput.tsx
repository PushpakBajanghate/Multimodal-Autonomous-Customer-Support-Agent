'use client';

import React, { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  onOpenVoiceMode?: () => void;
  disabled?: boolean;
  isTyping?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onOpenVoiceMode,
  disabled = false,
  isTyping = false,
  placeholder = 'Message Aura Support about your order...'
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height to fit content up to max-h
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || disabled || isTyping) return;

    onSendMessage(text.trim());
    setText('');

    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="aura-composer relative border-t border-[#f0eef5] bg-white px-4 pb-3 pt-3 sm:px-8 sm:pb-4 sm:pt-4"
    >
      <div className="aura-composer-box relative flex items-end gap-2 rounded-[17px] border border-[#e9e6f0] bg-[#fbfaff] p-2 shadow-[0_3px_12px_rgba(46,38,86,.035)] transition-all focus-within:border-[#c8bffa] focus-within:ring-4 focus-within:ring-[#7a68df]/[.08]">
        <button
          type="button"
          onClick={onOpenVoiceMode}
          disabled={disabled || isTyping}
          className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[#e9e5f6] bg-white text-[#7461d7] shadow-[0_1px_3px_rgba(36,29,67,.05)] transition hover:border-[#d8d0fa] hover:bg-[#f6f3ff] disabled:cursor-not-allowed disabled:opacity-40"
          title="Open Aura Support Voice Mode"
          aria-label="Open Aura Support Voice Mode"
        >
          <svg className="h-[17px] w-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 12a7 7 0 0 0 14 0m-7 7v3m-4 0h8" /></svg>
        </button>
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={isTyping ? 'Aura Support is generating a reply...' : placeholder}
          maxLength={2000}
          className="max-h-[140px] w-full resize-none bg-transparent px-2 py-2 text-[13px] leading-relaxed text-[#39364b] placeholder-[#aaa6b6] focus:outline-none disabled:opacity-50"
        />

        {/* Action buttons (Send & Char counter) */}
        <div className="flex items-center gap-2 pb-0.5 pr-0.5">
          {text.length > 300 && (
            <span className="select-none text-[10px] font-mono text-[#9d99aa]">
              {text.length}/2000
            </span>
          )}

          <button
            type="submit"
            disabled={!text.trim() || disabled || isTyping}
            className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-xl bg-[#6654d9] text-white shadow-[0_4px_10px_rgba(102,84,217,.2)] transition-all hover:bg-[#5946cf] active:scale-95 disabled:pointer-events-none disabled:bg-[#e8e5ef] disabled:text-[#aaa6b6]"
            title="Send message (Enter)"
            aria-label="Send message"
          >
            {isTyping ? (
              <svg className="h-4 w-4 animate-spin text-violet-200" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div className="mt-2 flex select-none items-center justify-between px-1 text-[10px] text-[#aaa6b6]">
        <span>Enter to send <span className="px-1 text-[#d0cdda]">·</span> Shift + Enter for a new line</span>
        <span className="hidden sm:inline">Aura Support can make mistakes. Check important details.</span>
      </div>
    </form>
  );
};
