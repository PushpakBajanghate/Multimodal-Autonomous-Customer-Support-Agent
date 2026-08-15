import {
  ApiResponseWrapper,
  ChatApiRequestPayload,
  ChatResponseData,
  ConversationMessageReadData,
  ConversationReadData
} from '../types/chat';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1';
export const HEALTH_URL = process.env.NEXT_PUBLIC_HEALTH_URL || 'http://localhost:8000/health';

export class ChatApiError extends Error {
  statusCode: number;
  reason: string;

  constructor(message: string, statusCode = 0, reason = '') {
    super(message);
    this.name = 'ChatApiError';
    this.statusCode = statusCode;
    this.reason = reason;
  }
}

/**
 * Sends a chat message to backend /api/v1/chat
 */
export async function sendChatMessage(
  message: string,
  conversationId?: number | null,
  channel = 'chat'
): Promise<ChatResponseData> {
  const payload: ChatApiRequestPayload = {
    message,
    conversation_id: conversationId ?? null,
    channel
  };

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data: ApiResponseWrapper<ChatResponseData> = await res.json().catch(() => ({
      success: false,
      status: 'failure',
      reason: `HTTP ${res.status} ${res.statusText}`,
      data: null as unknown as ChatResponseData
    }));

    if (!res.ok || !data.success) {
      throw new ChatApiError(
        data.reason || `Failed to send message (${res.status})`,
        res.status,
        data.reason || res.statusText
      );
    }

    return data.data;
  } catch (err: unknown) {
    if (err instanceof ChatApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error or backend unreachable';
    throw new ChatApiError(
      `Unable to reach Aura support server. Please verify the backend is running. (${message})`,
      0,
      message
    );
  }
}

/**
 * Retrieves persisted chat history for an existing conversation ID
 */
export async function getConversationMessages(
  conversationId: number
): Promise<ConversationMessageReadData[]> {
  try {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}/messages`);
    const data: ApiResponseWrapper<ConversationMessageReadData[]> = await res.json().catch(() => ({
      success: false,
      status: 'failure',
      reason: `HTTP ${res.status}`,
      data: []
    }));

    if (!res.ok || !data.success) {
      throw new ChatApiError(
        data.reason || `Failed to fetch conversation messages (${res.status})`,
        res.status,
        data.reason || res.statusText
      );
    }

    return data.data || [];
  } catch (err: unknown) {
    if (err instanceof ChatApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ChatApiError(
      `Failed to load conversation history: ${message}`,
      0,
      message
    );
  }
}

/**
 * Explicitly starts a new conversation session on backend
 */
export async function createNewConversation(
  channel = 'chat'
): Promise<ConversationReadData> {
  try {
    const res = await fetch(`${API_BASE}/chat/conversations/new?channel=${encodeURIComponent(channel)}`, {
      method: 'POST'
    });
    const data: ApiResponseWrapper<ConversationReadData> = await res.json().catch(() => ({
      success: false,
      status: 'failure',
      reason: `HTTP ${res.status}`,
      data: null as unknown as ConversationReadData
    }));

    if (!res.ok || !data.success) {
      throw new ChatApiError(
        data.reason || `Failed to create conversation (${res.status})`,
        res.status,
        data.reason || res.statusText
      );
    }

    return data.data;
  } catch (err: unknown) {
    if (err instanceof ChatApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ChatApiError(
      `Failed to start new conversation: ${message}`,
      0,
      message
    );
  }
}

/**
 * Checks backend health status
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(HEALTH_URL, { cache: 'no-store' });
    return res.ok;
  } catch {
    return false;
  }
}
