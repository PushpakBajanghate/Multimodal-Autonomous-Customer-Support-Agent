'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ChatMessage } from '../../types/chat';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { AuraBrandMark } from './AuraBrandMark';

interface MessageListProps {
  messages: ChatMessage[];
  isTyping: boolean;
  streamingMessageId: string | null;
  searchQuery?: string;
  onRetryMessage?: (messageId: string) => void;
  onSelectStarter?: (text: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isTyping,
  streamingMessageId,
  searchQuery = '',
  onRetryMessage,
  onSelectStarter
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const normalizedSearch = searchQuery.trim().toLocaleLowerCase();
  const visibleMessages = normalizedSearch
    ? messages.filter(message => message.text.toLocaleLowerCase().includes(normalizedSearch))
    : messages;

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
    <div className="aura-message-list relative flex-1 flex min-h-0 flex-col bg-white">
      {/* Scrollable Message Container */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-8 sm:py-7 xl:px-12"
      >
        {!normalizedSearch && messages.length === 1 && messages[0].id.startsWith('msg-welcome') && (
          <div className="aura-welcome mx-auto my-5 max-w-[680px] overflow-hidden rounded-[24px] border border-[#e9e5f6] bg-gradient-to-br from-[#fbfaff] via-white to-[#f5f2ff] shadow-[0_12px_36px_rgba(52,43,96,.055)] sm:my-8">
            <div className="relative px-5 pb-5 pt-6 sm:px-8 sm:pb-7 sm:pt-8">
              <div className="absolute -right-10 -top-16 h-52 w-52 rounded-full bg-[#e8e1ff]/70 blur-3xl" />
              <div className="relative flex items-start gap-4">
                <AuraBrandMark className="aura-welcome-mark shrink-0" />
                <div className="relative min-w-0">
                  <div className="aura-welcome-label mb-1 text-[10px] font-bold uppercase tracking-[.16em] text-[#7868cb]">Your personal support assistant</div>
                  <h2 className="aura-welcome-title text-[21px] font-semibold leading-tight tracking-[-.045em] text-[#29263e] sm:text-[25px]">How can I make things easier?</h2>
                  <p className="aura-welcome-description mt-2 max-w-lg text-[13px] leading-relaxed text-[#858197]">
                    I’m Aura Support. I can help with order updates, returns, cancellations, and delivery changes.
                  </p>
                </div>
              </div>
              <div className="relative mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => onSelectStarter?.('Track order #9')}
                  className="aura-welcome-tile group flex items-center gap-3 rounded-[14px] border border-[#ece9f4] bg-white/90 p-3 text-left shadow-[0_2px_7px_rgba(39,33,71,.025)] transition hover:-translate-y-0.5 hover:border-[#d9d2fa] hover:shadow-[0_7px_16px_rgba(58,45,116,.07)]"
                >
                  <span className="aura-welcome-icon flex h-9 w-9 items-center justify-center rounded-xl bg-[#f0edff] text-[#7160d4]">
                    <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7h18l-2 12H5L3 7Z" /><path d="M3 7 5 3h14l2 4M9 11v4m6-4v4" /></svg>
                  </span>
                  <span className="aura-welcome-tile-label"><span className="block text-xs font-semibold text-[#454158]">Track an order</span><span className="mt-0.5 block text-[10px] text-[#a09caf]">Get a delivery update</span></span>
                  <svg className="ml-auto h-4 w-4 text-[#bbb6cb] transition group-hover:translate-x-0.5 group-hover:text-[#715fce]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m9 18 6-6-6-6" /></svg>
                </button>
                <button
                  type="button"
                  onClick={() => onSelectStarter?.('Request refund for order #9')}
                  className="aura-welcome-tile group flex items-center gap-3 rounded-[14px] border border-[#ece9f4] bg-white/90 p-3 text-left shadow-[0_2px_7px_rgba(39,33,71,.025)] transition hover:-translate-y-0.5 hover:border-[#d9d2fa] hover:shadow-[0_7px_16px_rgba(58,45,116,.07)]"
                >
                  <span className="aura-welcome-icon flex h-9 w-9 items-center justify-center rounded-xl bg-[#f0edff] text-[#7160d4]">
                    <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M20 7v5h-5M4 17v-5h5" /><path d="M5.6 9a7 7 0 0 1 11.8-2L20 12M4 12l2.6 5a7 7 0 0 0 11.8-2" /></svg>
                  </span>
                  <span className="aura-welcome-tile-label"><span className="block text-xs font-semibold text-[#454158]">Start a return</span><span className="mt-0.5 block text-[10px] text-[#a09caf]">Explore refund options</span></span>
                  <svg className="ml-auto h-4 w-4 text-[#bbb6cb] transition group-hover:translate-x-0.5 group-hover:text-[#715fce]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m9 18 6-6-6-6" /></svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Message Stream */}
        {visibleMessages
          .filter(msg => !(messages.length === 1 && msg.id.startsWith('msg-welcome') && !normalizedSearch))
          .map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={msg.id === streamingMessageId}
            onRetry={onRetryMessage}
          />
        ))}

        {normalizedSearch && visibleMessages.length === 0 && (
          <p className="mx-auto mt-12 max-w-md text-center text-sm text-[#a49fb2]">
            No messages match &ldquo;{searchQuery.trim()}&rdquo;.
          </p>
        )}

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
          className="absolute bottom-4 right-4 z-10 rounded-full border border-[#e6e2ef] bg-white p-2.5 text-[#6d5bd0] shadow-lg backdrop-blur-md transition-all hover:bg-[#f8f6ff] animate-fade-in"
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
