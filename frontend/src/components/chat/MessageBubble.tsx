'use client';

import React, { useState } from 'react';
import { ChatMessage } from '../../types/chat';
import { AuraBrandMark } from './AuraBrandMark';

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
  onRetry?: (messageId: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  onRetry
}) => {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isUser = message.sender === 'user';
  const isError = message.status === 'error';
  const isSending = message.status === 'sending';

  const handleCopy = () => {
    if (!message.text) return;
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window) || !message.text) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const cleanText = message.text.replace(/[•*#_`]/g, ' ');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div
      className={`group flex max-w-[92%] flex-col transition-all sm:max-w-[78%] ${
        isUser ? 'ml-auto items-end' : 'mr-auto items-start'
      }`}
    >
      <div className="flex items-end gap-2">
        {/* Agent Avatar */}
        {!isUser && (
          <AuraBrandMark className="aura-message-mark mb-1 shrink-0" />
        )}

        <div className="flex flex-col">
          {/* Message Card Bubble */}
          <div
            className={`relative rounded-[18px] px-4 py-3 text-[13px] leading-[1.75] shadow-[0_3px_10px_rgba(41,35,78,.045)] transition-all duration-200 sm:px-5 ${
              isUser
                ? isError
                  ? 'aura-bubble-error rounded-br-[5px] border border-rose-200 bg-rose-50 text-rose-800'
                  : 'aura-bubble-user rounded-br-[5px] bg-gradient-to-br from-[#7663e5] to-[#5e4bc8] text-white shadow-[0_7px_18px_rgba(95,75,200,.17)]'
                : 'aura-bubble-agent rounded-bl-[5px] border border-[#eeecf3] bg-[#faf9fc] text-[#454157]'
            }`}
          >
            {/* Message Body Content */}
            <div className="whitespace-pre-wrap break-words">
              {message.text || (isStreaming ? '' : '...')}
            </div>

            {/* Error Message Reason */}
            {isError && message.errorReason && (
              <div className="mt-2 pt-2 border-t border-rose-800/80 text-xs text-rose-200 flex items-start gap-1.5">
                <svg className="w-3.5 h-3.5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{message.errorReason}</span>
              </div>
            )}
          </div>

          {/* Metadata Footer: Timestamp, Status, Action Buttons */}
          <div
            className={`mt-1 flex select-none items-center gap-2 px-1 text-[10px] text-[#a29eae] ${
              isUser ? 'justify-end' : 'justify-start'
            }`}
          >
            <span suppressHydrationWarning>{message.timestamp}</span>

            {/* Delivery / Error Status for User Messages */}
            {isUser && (
              <span className="flex items-center">
                {isSending && (
                  <svg className="h-3 w-3 animate-spin text-[#a29eae]" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {message.status === 'sent' && (
                  <svg className="h-3.5 w-3.5 text-[#7865d9]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {isError && (
                  <span className="font-medium text-rose-500">Failed</span>
                )}
              </span>
            )}

            {/* Retry Button on Error */}
            {isError && onRetry && (
              <button
                type="button"
                onClick={() => onRetry(message.id)}
                className="ml-1 cursor-pointer text-xs font-medium text-rose-500 underline hover:text-rose-700"
              >
                Retry
              </button>
            )}

            {/* Text to Speech Button for Agent Messages */}
            {!isUser && message.text && (
              <button
                type="button"
                onClick={handleSpeak}
                className={`transition-colors cursor-pointer ml-1 p-0.5 rounded ${
                  isSpeaking ? 'font-bold text-[#6e5bd2]' : 'text-[#9d99aa] opacity-0 transition-opacity hover:text-[#6e5bd2] group-hover:opacity-100'
                }`}
                title={isSpeaking ? 'Stop audio' : 'Listen to response'}
              >
                {isSpeaking ? (
                  <span className="flex items-center gap-1 text-[10px] text-[#6e5bd2]">
                    <span aria-hidden="true">◖</span> Speaking...
                  </span>
                ) : (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                )}
              </button>
            )}

            {/* Copy Button (visible on hover) */}
            <button
              type="button"
              onClick={handleCopy}
              className="ml-1 cursor-pointer text-[#9d99aa] opacity-0 transition-opacity hover:text-[#6e5bd2] group-hover:opacity-100"
              title="Copy text"
            >
              {copied ? (
                <span className="font-sans text-[10px] text-emerald-600">Copied!</span>
              ) : (
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
