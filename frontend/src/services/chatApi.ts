import {
  ApiResponseWrapper,
  ChatApiRequestPayload,
  ChatResponseData,
  ConversationMessageReadData,
  ConversationReadData,
  VoiceSynthesisResponseData
} from '../types/chat';
import { CustomerUser, CustomerAuthData } from '../types/auth';

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1';
export const HEALTH_URL = process.env.NEXT_PUBLIC_HEALTH_URL || 'http://localhost:8000/health';

const TOKEN_STORAGE_KEY = 'aura_access_token';
const USER_STORAGE_KEY = 'aura_customer_user';

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

export function getStoredAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage errors
  }
}

export function clearStoredAuthToken(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
}

export function getStoredUser(): CustomerUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user: CustomerUser): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Ignore storage errors
  }
}

export function clearStoredUser(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
}

export function clearStoredAuth(): void {
  clearStoredAuthToken();
  clearStoredUser();
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem('aura_chat_conversation_id');
      localStorage.removeItem('aura_chat_messages_cache');
    } catch {
      // Ignore
    }
  }
}

/**
 * Register a new customer and store token & profile immediately.
 */
export async function customerRegister(
  name: string,
  email: string,
  password: string
): Promise<CustomerAuthData> {
  const res = await fetch(`${API_BASE}/auth/customer-register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password })
  });

  const payload = (await res.json().catch(() => null)) as ApiResponseWrapper<CustomerAuthData> | null;

  if (!res.ok || !payload?.success || !payload.data) {
    const reason = payload?.reason || 'Registration failed. Please check your details.';
    throw new ChatApiError(reason, res.status, reason);
  }

  setStoredAuthToken(payload.data.access_token);
  setStoredUser({
    customer_id: payload.data.customer_id,
    name: payload.data.name,
    email: payload.data.email,
    is_verified: payload.data.is_verified
  });

  return payload.data;
}

/**
 * Login customer with email and password and store token & profile.
 */
export async function customerLogin(
  email: string,
  password: string
): Promise<CustomerAuthData> {
  const res = await fetch(`${API_BASE}/auth/customer-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const payload = (await res.json().catch(() => null)) as ApiResponseWrapper<CustomerAuthData> | null;

  if (!res.ok || !payload?.success || !payload.data) {
    const reason = payload?.reason || 'Invalid email or password.';
    throw new ChatApiError(reason, res.status, reason);
  }

  setStoredAuthToken(payload.data.access_token);
  setStoredUser({
    customer_id: payload.data.customer_id,
    name: payload.data.name,
    email: payload.data.email,
    is_verified: payload.data.is_verified
  });

  return payload.data;
}

/**
 * Validate token and fetch current customer profile.
 */
export async function fetchCurrentProfile(): Promise<CustomerUser | null> {
  const token = getStoredAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!res.ok) {
      if (res.status === 401) {
        clearStoredAuth();
      }
      return null;
    }

    const payload = (await res.json().catch(() => null)) as ApiResponseWrapper<CustomerAuthData> | null;
    if (payload?.success && payload.data) {
      const user: CustomerUser = {
        customer_id: payload.data.customer_id,
        name: payload.data.name,
        email: payload.data.email,
        is_verified: payload.data.is_verified
      };
      setStoredUser(user);
      return user;
    }
  } catch {
    return getStoredUser();
  }

  return null;
}


/**
 * Retrieves a valid customer JWT session token from local storage or creates one via backend auth.
 */
export async function getOrFetchSessionToken(forceRefresh = false): Promise<string> {
  if (!forceRefresh) {
    const existing = getStoredAuthToken();
    if (existing) return existing;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/customer-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json().catch(() => null);
    if (res.ok && data?.data?.access_token) {
      setStoredAuthToken(data.data.access_token);
      return data.data.access_token;
    }
  } catch {
    // Ignore and fallback to existing
  }

  return getStoredAuthToken() || '';
}

/**
 * Performs an authenticated fetch request with auto-retry and token refresh on 401
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let token = await getOrFetchSessionToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    clearStoredAuthToken();
    token = await getOrFetchSessionToken(true);
    if (token) {
      const retryHeaders = new Headers(options.headers || {});
      retryHeaders.set('Authorization', `Bearer ${token}`);
      res = await fetch(url, { ...options, headers: retryHeaders });
    }
  }
  return res;
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
    const res = await authFetch(`${API_BASE}/chat`, {
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
    const res = await authFetch(`${API_BASE}/chat/conversations/${conversationId}/messages`);
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
    const res = await authFetch(`${API_BASE}/chat/conversations/new?channel=${encodeURIComponent(channel)}`, {
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
 * Generates provider-backed voice audio for the agent response when Sarvam or ElevenLabs is configured.
 */
export async function synthesizeVoice(
  text: string,
  languageCode = 'auto'
): Promise<VoiceSynthesisResponseData> {
  try {
    const res = await authFetch(`${API_BASE}/voice/synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text,
        language_code: languageCode
      })
    });
    const data: ApiResponseWrapper<VoiceSynthesisResponseData> = await res.json().catch(() => ({
      success: false,
      status: 'failure',
      reason: `HTTP ${res.status}`,
      data: {
        provider: 'browser',
        language_code: languageCode,
        audio_base64: null,
        audio_mime_type: 'audio/wav',
        fallback_to_browser: true,
        reason: `HTTP ${res.status}`
      }
    }));

    if (!res.ok || !data.success) {
      throw new ChatApiError(
        data.reason || `Failed to synthesize voice (${res.status})`,
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
    throw new ChatApiError(`Voice synthesis unavailable: ${message}`, 0, message);
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
