'use client';

import React, { useState } from 'react';
import { useChatSession } from '../hooks/useChatSession';
import { ChatHeader } from '../components/chat/ChatHeader';
import { MessageList } from '../components/chat/MessageList';
import { QuickPrompts } from '../components/chat/QuickPrompts';
import { ChatInput } from '../components/chat/ChatInput';
import { ErrorBanner } from '../components/chat/ErrorBanner';
import { SessionDrawer } from '../components/chat/SessionDrawer';
import { VoiceSimulationModal } from '../components/chat/VoiceSimulationModal';
import { ReasoningDrawer } from '../components/chat/ReasoningDrawer';
import { VerificationModal } from '../components/chat/VerificationModal';

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
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isReasoningDrawerOpen, setIsReasoningDrawerOpen] = useState(false);
  const [isVerificationModalOpen, setIsVerificationModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleVoiceSend = async (spokenText: string) => sendMessage(spokenText);
  const handleSupportMessage = (text: string) => {
    setSearchQuery('');
    void sendMessage(text);
  };
  const handleNewConversation = () => {
    setSearchQuery('');
    void startNewConversation();
  };
  const handleSelectSession = (id: number) => {
    setSearchQuery('');
    void loadSessionHistory(id);
  };

  return (
    <div className="aura-app flex min-h-screen overflow-hidden text-[#25223a] selection:bg-violet-200 selection:text-violet-950 md:h-screen md:min-h-0">
      <main className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          conversationId={conversationId}
          backendOnline={backendOnline}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onNewChat={handleNewConversation}
          onOpenSessionDrawer={() => setIsSessionDrawerOpen(true)}
          onRefreshHealth={checkHealth}
          onOpenVoiceModal={() => setIsVoiceModalOpen(true)}
          onOpenReasoningDrawer={() => setIsReasoningDrawerOpen(true)}
          onOpenVerificationModal={() => setIsVerificationModalOpen(true)}
        />

        <div className="aura-content flex min-h-0 flex-1">
          <section className="aura-chat flex min-w-0 flex-1 flex-col bg-white">
            <ErrorBanner error={error} onDismiss={dismissError} onRetry={checkHealth} />
            <MessageList
              messages={messages}
              isTyping={isTyping}
              streamingMessageId={streamingMessageId}
              searchQuery={searchQuery}
              onRetryMessage={retryMessage}
              onSelectStarter={handleSupportMessage}
            />
            <QuickPrompts onSelectPrompt={handleSupportMessage} disabled={isTyping} />
            <ChatInput
              onSendMessage={handleSupportMessage}
              onOpenVoiceMode={() => setIsVoiceModalOpen(true)}
              isTyping={isTyping}
              disabled={backendOnline === false && error !== null}
            />
          </section>
        </div>
      </main>

      <SessionDrawer
        isOpen={isSessionDrawerOpen}
        onClose={() => setIsSessionDrawerOpen(false)}
        currentConversationId={conversationId}
        savedSessionIds={savedSessionIds}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewConversation}
        onClearHistory={clearLocalHistory}
      />
      <VoiceSimulationModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onSendVoiceTranscript={handleVoiceSend}
        conversationId={conversationId}
      />
      <ReasoningDrawer
        isOpen={isReasoningDrawerOpen}
        onClose={() => setIsReasoningDrawerOpen(false)}
        conversationId={conversationId}
        isBackendOnline={backendOnline}
      />
      <VerificationModal
        isOpen={isVerificationModalOpen}
        onClose={() => setIsVerificationModalOpen(false)}
        onVerificationSuccess={msg => {
          sendMessage(msg);
        }}
      />
    </div>
  );
}
