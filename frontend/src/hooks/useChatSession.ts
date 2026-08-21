'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  ChatMessage,
  ConversationMessageReadData
} from '../types/chat';
import {
  sendChatMessage,
  getConversationMessages,
  createNewConversation,
  checkBackendHealth,
  ChatApiError
} from '../services/chatApi';

const STORAGE_CONV_ID = 'aura_chat_conversation_id';
const STORAGE_MESSAGES = 'aura_chat_messages_cache';
const STORAGE_SAVED_SESSIONS = 'aura_saved_sessions';

const INITIAL_GREETING: ChatMessage = {
  id: 'msg-welcome',
  sender: 'agent',
  text: 'Hello! I am Aura, your autonomous customer support assistant.\n\nI can help you with order tracking, return requests, order cancellations, and shipping address changes. How may I assist you today?',
  timestamp: '',
  status: 'sent'
};

function getInitialConversationId(): number | null {
  // Always start a brand new session on application open
  return null;
}

function getInitialMessages(): ChatMessage[] {
  // Always start with the clean welcome greeting on application open
  return [INITIAL_GREETING];
}


function getInitialSavedSessions(): number[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_SAVED_SESSIONS);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export interface UseChatSessionReturn {
  conversationId: number | null;
  messages: ChatMessage[];
  isTyping: boolean;
  streamingMessageId: string | null;
  error: string | null;
  backendOnline: boolean | null;
  sendMessage: (text: string) => Promise<void>;
  retryMessage: (messageId: string) => Promise<void>;
  startNewConversation: () => Promise<void>;
  loadSessionHistory: (convId: number) => Promise<void>;
  clearLocalHistory: () => void;
  dismissError: () => void;
  savedSessionIds: number[];
  checkHealth: () => Promise<void>;
}

export function useChatSession(): UseChatSessionReturn {
  const [conversationId, setConversationId] = useState<number | null>(getInitialConversationId);
  const [messages, setMessages] = useState<ChatMessage[]>(getInitialMessages);
  const [savedSessionIds, setSavedSessionIds] = useState<number[]>(getInitialSavedSessions);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const hasHydratedRemote = useRef<boolean>(false);

  // Health check helper
  const checkHealth = useCallback(async () => {
    const isHealthy = await checkBackendHealth();
    setBackendOnline(isHealthy);
  }, []);

  // Save session ID to history list
  const trackSessionId = useCallback((id: number) => {
    try {
      const raw = localStorage.getItem(STORAGE_SAVED_SESSIONS);
      const list: number[] = raw ? JSON.parse(raw) : [];
      if (!list.includes(id)) {
        const updated = [id, ...list].slice(0, 10);
        localStorage.setItem(STORAGE_SAVED_SESSIONS, JSON.stringify(updated));
        setSavedSessionIds(updated);
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Persist messages to LocalStorage
  const persistMessagesToLocal = useCallback((msgs: ChatMessage[]) => {
    try {
      localStorage.setItem(STORAGE_MESSAGES, JSON.stringify(msgs));
    } catch {
      // Ignore storage errors
    }
  }, []);

  // On initial mount: reset active session cache to guarantee fresh session and check health
  useEffect(() => {
    let isMounted = true;
    setMessages((currentMessages) => currentMessages.map((message) => (
      message.id === INITIAL_GREETING.id && !message.timestamp
        ? {
            ...message,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        : message
    )));
    try {
      localStorage.removeItem(STORAGE_CONV_ID);
      localStorage.removeItem(STORAGE_MESSAGES);
    } catch {
      // Ignore storage errors
    }

    checkBackendHealth()
      .then((isHealthy) => {
        if (isMounted) {
          setBackendOnline(isHealthy);
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendOnline(false);
        }
      });


    if (!hasHydratedRemote.current && conversationId !== null) {
      hasHydratedRemote.current = true;
      getConversationMessages(conversationId)
        .then((remoteMsgs: ConversationMessageReadData[]) => {
          if (isMounted && remoteMsgs && remoteMsgs.length > 0) {
            const formatted: ChatMessage[] = remoteMsgs.map((m) => ({
              id: `remote-${m.id}`,
              sender: m.sender === 'user' ? 'user' : 'agent',
              text: m.message_text,
              timestamp: new Date(m.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              }),
              status: 'sent',
              conversationId: m.conversation_id,
              backendMessageId: m.id
            }));
            setMessages(formatted);
            persistMessagesToLocal(formatted);
          }
        })
        .catch(() => {
          // Backend not reachable, rely on cached messages
        });
    }

    return () => {
      isMounted = false;
    };
  }, [conversationId, persistMessagesToLocal]);

  // Sync active conversation_id to localStorage
  useEffect(() => {
    try {
      if (conversationId !== null) {
        localStorage.setItem(STORAGE_CONV_ID, conversationId.toString());
      } else {
        localStorage.removeItem(STORAGE_CONV_ID);
      }
    } catch {
      // Ignore
    }
  }, [conversationId]);

  // Stream text animation helper
  const streamAgentReply = useCallback((fullText: string, agentMsgId: string) => {
    let currentLength = 0;
    const totalLength = fullText.length;
    const chunkSize = Math.max(2, Math.floor(totalLength / 25));
    const intervalMs = 20;

    setStreamingMessageId(agentMsgId);

    const timer = setInterval(() => {
      currentLength += chunkSize;
      if (currentLength >= totalLength) {
        clearInterval(timer);
        setStreamingMessageId(null);
        setIsTyping(false);
        setMessages((prev) => {
          const updated = prev.map((m) =>
            m.id === agentMsgId
              ? { ...m, text: fullText, status: 'sent' as const }
              : m
          );
          persistMessagesToLocal(updated);
          return updated;
        });
      } else {
        const partial = fullText.slice(0, currentLength);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentMsgId ? { ...m, text: partial } : m
          )
        );
      }
    }, intervalMs);
  }, [persistMessagesToLocal]);

  // Send message
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isTyping) return;
    setError(null);

    const userMessageId = `usr-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: 'user',
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'sending',
      conversationId: conversationId ?? undefined
    };

    // Optimistic UI update
    setMessages((prev) => {
      const updated = [...prev, userMsg];
      persistMessagesToLocal(updated);
      return updated;
    });

    setIsTyping(true);

    try {
      const response = await sendChatMessage(userMsg.text, conversationId, 'chat');
      setBackendOnline(true);

      const resolvedConvId = response.conversation_id;
      setConversationId(resolvedConvId);
      trackSessionId(resolvedConvId);

      // Mark user message as sent
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMessageId
            ? {
                ...m,
                status: 'sent',
                conversationId: resolvedConvId,
                backendMessageId: response.user_message_id
              }
            : m
        )
      );

      // Create placeholder for agent streaming response
      const agentMessageId = `agt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      const initialAgentMsg: ChatMessage = {
        id: agentMessageId,
        sender: 'agent',
        text: '',
        timestamp: new Date(response.created_at).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit'
        }),
        status: 'sending',
        conversationId: resolvedConvId,
        backendMessageId: response.agent_message_id
      };

      setMessages((prev) => [...prev, initialAgentMsg]);

      // Trigger streaming effect
      streamAgentReply(response.reply, agentMessageId);
    } catch (err: unknown) {
      setIsTyping(false);
      setStreamingMessageId(null);

      const errorMessage =
        err instanceof ChatApiError
          ? err.message
          : 'Something went wrong while communicating with the support agent. Please try again.';

      setError(errorMessage);
      setBackendOnline(false);

      // Mark user message as error
      setMessages((prev) => {
        const updated = prev.map((m) =>
          m.id === userMessageId
            ? {
                ...m,
                status: 'error' as const,
                errorReason: errorMessage
              }
            : m
        );
        persistMessagesToLocal(updated);
        return updated;
      });
    }
  }, [conversationId, isTyping, persistMessagesToLocal, streamAgentReply, trackSessionId]);

  // Retry a failed message
  const retryMessage = useCallback(async (messageId: string) => {
    const target = messages.find((m) => m.id === messageId);
    if (!target) return;

    // Remove the failed message and resend its text
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
    await sendMessage(target.text);
  }, [messages, sendMessage]);

  // Start fresh conversation
  const startNewConversation = useCallback(async () => {
    setIsTyping(false);
    setStreamingMessageId(null);
    setError(null);

    try {
      const newConv = await createNewConversation('chat');
      setConversationId(newConv.id);
      trackSessionId(newConv.id);
      setBackendOnline(true);
    } catch {
      // If backend creation fails, reset local session ID so next send triggers session creation
      setConversationId(null);
    }

    const resetMessages = [
      {
        ...INITIAL_GREETING,
        id: `msg-welcome-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];
    setMessages(resetMessages);
    persistMessagesToLocal(resetMessages);
  }, [persistMessagesToLocal, trackSessionId]);

  // Load a past session history
  const loadSessionHistory = useCallback(async (convId: number) => {
    setIsTyping(false);
    setStreamingMessageId(null);
    setError(null);

    try {
      const remoteMsgs = await getConversationMessages(convId);
      setBackendOnline(true);
      setConversationId(convId);
      trackSessionId(convId);

      const formatted: ChatMessage[] =
        remoteMsgs.length > 0
          ? remoteMsgs.map((m) => ({
              id: `remote-${m.id}`,
              sender: m.sender === 'user' ? 'user' : 'agent',
              text: m.message_text,
              timestamp: new Date(m.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              }),
              status: 'sent',
              conversationId: m.conversation_id,
              backendMessageId: m.id
            }))
          : [
              {
                ...INITIAL_GREETING,
                id: `msg-welcome-${Date.now()}`,
                conversationId: convId
              }
            ];

      setMessages(formatted);
      persistMessagesToLocal(formatted);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not retrieve past conversation.';
      setError(msg);
    }
  }, [persistMessagesToLocal, trackSessionId]);

  // Clear local history cache
  const clearLocalHistory = useCallback(() => {
    setConversationId(null);
    const reset = [INITIAL_GREETING];
    setMessages(reset);
    persistMessagesToLocal(reset);
    try {
      localStorage.removeItem(STORAGE_CONV_ID);
      localStorage.removeItem(STORAGE_MESSAGES);
    } catch {
      // Ignore
    }
  }, [persistMessagesToLocal]);

  const dismissError = useCallback(() => {
    setError(null);
  }, []);

  return {
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
  };
}
