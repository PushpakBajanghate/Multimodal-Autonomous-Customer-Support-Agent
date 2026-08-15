export type MessageSender = 'user' | 'agent' | 'system';

export type MessageStatus = 'sending' | 'sent' | 'error';

export interface ChatMessage {
  id: string;
  sender: MessageSender;
  text: string;
  timestamp: string;
  status: MessageStatus;
  conversationId?: number;
  errorReason?: string;
  backendMessageId?: number;
}

export interface ChatApiRequestPayload {
  message: string;
  conversation_id?: number | null;
  channel?: string;
}

export interface ChatResponseData {
  conversation_id: number;
  user_message_id: number;
  agent_message_id: number;
  reply: string;
  created_at: string;
}

export interface ConversationMessageReadData {
  id: number;
  conversation_id: number;
  sender: string;
  message_text: string;
  created_at: string;
}

export interface ConversationReadData {
  id: number;
  customer_id?: number | null;
  channel: string;
  status: string;
  started_at: string;
  messages: ConversationMessageReadData[];
}

export interface ApiResponseWrapper<T> {
  success: boolean;
  status: string;
  reason?: string | null;
  data: T;
}

export interface LocalChatSession {
  conversationId: number | null;
  updatedAt: string;
  title: string;
  messageCount: number;
}
