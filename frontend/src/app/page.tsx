'use client';

import React, { useState, useEffect, useCallback, useRef, useSyncExternalStore } from 'react';
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
import { ActionConfirmModal } from '../components/chat/ActionConfirmModal';
import { AuthScreen } from '../components/auth/AuthScreen';
import { CustomerUser } from '../types/auth';
import {
  getStoredUser,
  getStoredAuthToken,
  fetchCurrentProfile,
  clearStoredAuth
} from '../services/chatApi';

const emptySubscribe = () => () => {};

function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

function getInitialUser(): CustomerUser | null {
  if (typeof window === 'undefined') return null;
  const user = getStoredUser();
  const token = getStoredAuthToken();
  return user && token ? user : null;
}

export default function CustomerSupportPage() {
  const isMounted = useMounted();
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

  const [currentUser, setCurrentUser] = useState<CustomerUser | null>(getInitialUser);
  const [isSessionDrawerOpen, setIsSessionDrawerOpen] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isReasoningDrawerOpen, setIsReasoningDrawerOpen] = useState(false);
  const [isVerificationModalOpen, setIsVerificationModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pendingCancellation, setPendingCancellation] = useState<string | null>(null);
  const [humanEscalationMessage, setHumanEscalationMessage] = useState<string | null>(null);
  const shownEscalationMessageId = useRef<string | null>(null);

  // Validate stored auth token in background on initial load
  useEffect(() => {
    const token = getStoredAuthToken();
    if (token) {
      void fetchCurrentProfile()
        .then((profile) => {
          if (profile) {
            setCurrentUser(profile);
          }
        })
        .catch(() => {
          // Keep cached user if offline
        });
    }
  }, []);

  const handleAuthSuccess = useCallback((user: CustomerUser) => {
    setCurrentUser(user);
    void startNewConversation();
  }, [startNewConversation]);

  const handleLogout = useCallback(() => {
    clearStoredAuth();
    setCurrentUser(null);
    clearLocalHistory();
  }, [clearLocalHistory]);
  const handleSupportMessage = (text: string) => {
    setSearchQuery('');
    if (/\b(cancel|cancellation|canceling|cancelling)\b/i.test(text)) {
      setPendingCancellation(text);
      return;
    }
    void sendMessage(text);
  };

  useEffect(() => {
    const latestAgentMessage = [...messages].reverse().find(message => message.sender === 'agent' && message.status === 'sent');
    if (
      latestAgentMessage &&
      latestAgentMessage.id !== shownEscalationMessageId.current &&
      /human approval|awaiting human|support ticket #\d+/i.test(latestAgentMessage.text)
    ) {
      shownEscalationMessageId.current = latestAgentMessage.id;
      setHumanEscalationMessage(latestAgentMessage.text);
    }
  }, [messages]);
  const handleNewConversation = () => {
    setSearchQuery('');
    void startNewConversation();
  };
  const handleSelectSession = (id: number) => {
    setSearchQuery('');
    void loadSessionHistory(id);
  };

  if (!isMounted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0d0b18] text-[#f5f2ff]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
          <p className="text-xs text-[#9d97b0]">Loading Aura Support...</p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <AuthScreen
        onAuthSuccess={handleAuthSuccess}
        backendOnline={backendOnline}
        onRefreshHealth={checkHealth}
      />
    );
  }

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
          currentUser={currentUser}
          onLogout={handleLogout}
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
      <ActionConfirmModal
        isOpen={pendingCancellation !== null}
        title="Confirm order cancellation"
        message="This cancellation will be sent to Aura Support for processing. Do you want to continue?"
        confirmLabel="Yes, cancel order"
        onClose={() => setPendingCancellation(null)}
        onConfirm={() => {
          const message = pendingCancellation;
          setPendingCancellation(null);
          if (message) void sendMessage(message);
        }}
      />
      <ActionConfirmModal
        isOpen={humanEscalationMessage !== null}
        title="Human approval required"
        message={`${humanEscalationMessage ?? ''} A human specialist will review it. The refund will be processed only after approval.`}
        confirmLabel="Send to human"
        tone="info"
        onClose={() => setHumanEscalationMessage(null)}
        onConfirm={() => setHumanEscalationMessage(null)}
      />
    </div>
  );
}
