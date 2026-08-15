'use client';

import React, { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
  isTyping?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  isTyping = false,
  placeholder = 'Type your inquiry here... (Enter to send, Shift+Enter for newline)'
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
      className="p-3 sm:p-4 bg-slate-900/90 border-t border-slate-800 backdrop-blur-md relative"
    >
      <div className="relative flex items-end gap-2 bg-slate-950/80 border border-slate-700/70 focus-within:border-blue-500/80 focus-within:ring-2 focus-within:ring-blue-500/20 rounded-2xl p-2 transition-all shadow-inner">
        {/* Text Input Area */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={isTyping ? 'Aura is generating a reply...' : placeholder}
          maxLength={2000}
          className="w-full bg-transparent resize-none px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none max-h-[140px] leading-relaxed disabled:opacity-50"
        />

        {/* Action buttons (Send & Char counter) */}
        <div className="flex items-center gap-2 pb-0.5 pr-1">
          {text.length > 300 && (
            <span className="text-[10px] font-mono text-slate-500 select-none">
              {text.length}/2000
            </span>
          )}

          <button
            type="submit"
            disabled={!text.trim() || disabled || isTyping}
            className="w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 active:scale-95 disabled:bg-slate-800 disabled:text-slate-600 disabled:pointer-events-none text-white flex items-center justify-center transition-all shadow-md cursor-pointer shrink-0"
            title="Send message (Enter)"
            aria-label="Send message"
          >
            {isTyping ? (
              <svg className="w-4 h-4 animate-spin text-blue-300" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4 translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between mt-1.5 px-2 text-[11px] text-slate-500 select-none">
        <span>Press <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-700 rounded text-[10px] text-slate-400">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-slate-800 border border-slate-700 rounded text-[10px] text-slate-400">Shift + Enter</kbd> for line break</span>
        <span>Aura Agent Support</span>
      </div>
    </form>
  );
};
