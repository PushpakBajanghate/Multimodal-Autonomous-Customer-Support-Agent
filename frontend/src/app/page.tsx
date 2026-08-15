'use client';

import React, { useState } from 'react';
import { useChatSession } from '../hooks/useChatSession';
import { ChatHeader } from '../components/chat/ChatHeader';
import { MessageList } from '../components/chat/MessageList';
import { QuickPrompts } from '../components/chat/QuickPrompts';
import { ChatInput } from '../components/chat/ChatInput';
import { ErrorBanner } from '../components/chat/ErrorBanner';
import { SessionDrawer } from '../components/chat/SessionDrawer';

export default function CustomerSupportPage() {
  const {
    conversationId,
    messages,
    isTyping,
    streamingMessageId,
    error,
    backendOnline,
    sendMessage,
    retryMessage,
    startNewConversation,
    loadSessionHistory,
    clearLocalHistory,
    dismissError,
    savedSessionIds,
    checkHealth
  } = useChatSession();

  const [isSessionDrawerOpen, setIsSessionDrawerOpen] = useState(false);

  const handleSelectStarter = (promptText: string) => {
    sendMessage(promptText);
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 selection:bg-blue-600/30 selection:text-blue-200">
      {/* Background Subtle Gradient Accents */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-sky-600/10 rounded-full blur-3xl" />
      </div>

      {/* Top Header Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md px-4 sm:px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-sm shadow-md ring-2 ring-blue-500/20">
            A
          </div>
          <div>
            <span className="font-bold text-sm text-white tracking-tight flex items-center gap-1.5">
              Aura Customer Portal
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                v2.0
              </span>
            </span>
            <p className="text-[11px] text-slate-400">Autonomous Multimodal Support Hub</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <button
            type="button"
            onClick={() => setIsSessionDrawerOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition-all flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            <span>Sessions History</span>
          </button>
        </div>
      </header>

      {/* Main Support Widget Frame */}
      <main className="flex-1 flex flex-col max-w-4xl w-full mx-auto p-2 sm:p-6 sm:py-6">
        <div className="flex-1 flex flex-col bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-md relative h-[calc(100vh-120px)] sm:h-[780px]">
          {/* Chat Header */}
          <ChatHeader
            conversationId={conversationId}
            backendOnline={backendOnline}
            onNewChat={startNewConversation}
            onOpenSessionDrawer={() => setIsSessionDrawerOpen(true)}
            onRefreshHealth={checkHealth}
          />

          {/* Connection Error Banner */}
          <ErrorBanner
            error={error}
            onDismiss={dismissError}
            onRetry={checkHealth}
          />

          {/* Scrollable Message List */}
          <MessageList
            messages={messages}
            isTyping={isTyping}
            streamingMessageId={streamingMessageId}
            onRetryMessage={retryMessage}
            onSelectStarter={handleSelectStarter}
          />

          {/* Quick Inquiry Suggestions */}
          <QuickPrompts
            onSelectPrompt={handleSelectStarter}
            disabled={isTyping}
          />

          {/* Composer Input Box */}
          <ChatInput
            onSendMessage={sendMessage}
            isTyping={isTyping}
            disabled={backendOnline === false && error !== null}
          />
        </div>
      </main>

      {/* Sessions & History Drawer */}
      <SessionDrawer
        isOpen={isSessionDrawerOpen}
        onClose={() => setIsSessionDrawerOpen(false)}
        currentConversationId={conversationId}
        savedSessionIds={savedSessionIds}
        onSelectSession={loadSessionHistory}
        onNewChat={startNewConversation}
        onClearHistory={clearLocalHistory}
      />
    </div>
  );
}
