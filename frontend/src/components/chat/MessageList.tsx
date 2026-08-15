'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ChatMessage } from '../../types/chat';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

interface MessageListProps {
  messages: ChatMessage[];
  isTyping: boolean;
  streamingMessageId: string | null;
  onRetryMessage?: (messageId: string) => void;
  onSelectStarter?: (text: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isTyping,
  streamingMessageId,
  onRetryMessage,
  onSelectStarter
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Auto-scroll on messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Track scroll position to show jump-to-bottom button
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceToBottom = scrollHeight - scrollTop - clientHeight;
    setShowScrollBottom(distanceToBottom > 150);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="relative flex-1 flex flex-col min-h-0 bg-slate-950/60">
      {/* Scrollable Message Container */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4"
      >
        {/* Support Greeting Card */}
        <div className="mx-auto max-w-md my-4 p-5 rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-900/40 border border-slate-800/80 text-center shadow-xl backdrop-blur-xs">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white text-xl flex items-center justify-center mx-auto mb-3 shadow-lg ring-4 ring-blue-500/10">
            ✨
          </div>
          <h2 className="text-base font-bold text-white tracking-tight">
            How can Aura help you today?
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto leading-relaxed">
            I am your automated concierge for instant order updates, refund processing, address changes, and cancellations.
          </p>

          {/* Feature Badges */}
          <div className="grid grid-cols-2 gap-2 mt-4 text-[11px] text-slate-300">
            <button
              type="button"
              onClick={() => onSelectStarter?.('Track order #9')}
              className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-750 border border-slate-750 text-left transition-colors cursor-pointer"
            >
              <span className="font-semibold block text-slate-200">📦 Order Tracking</span>
              <span className="text-[10px] text-slate-400">Status & ETA</span>
            </button>
            <button
              type="button"
              onClick={() => onSelectStarter?.('Request refund for order #9')}
              className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-750 border border-slate-750 text-left transition-colors cursor-pointer"
            >
              <span className="font-semibold block text-slate-200">💰 Fast Returns</span>
              <span className="text-[10px] text-slate-400">Refund processing</span>
            </button>
          </div>
        </div>

        {/* Message Stream */}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={msg.id === streamingMessageId}
            onRetry={onRetryMessage}
          />
        ))}

        {/* Typing indicator when agent is processing and no streaming placeholder is present */}
        {isTyping && !streamingMessageId && <TypingIndicator />}

        {/* Bottom Anchor */}
        <div ref={bottomRef} className="h-1" />
      </div>

      {/* Floating Scroll-to-Bottom Button */}
      {showScrollBottom && (
        <button
          type="button"
          onClick={scrollToBottom}
          className="absolute bottom-4 right-4 z-10 p-2.5 rounded-full bg-slate-800/90 hover:bg-slate-750 text-slate-200 border border-slate-700 shadow-xl backdrop-blur-md transition-all cursor-pointer animate-fade-in"
          aria-label="Scroll to bottom"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>
      )}
    </div>
  );
};
