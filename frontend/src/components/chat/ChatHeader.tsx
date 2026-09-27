'use client';

import React from 'react';
import { AuraBrandMark } from './AuraBrandMark';

interface ChatHeaderProps {
  conversationId: number | null;
  backendOnline: boolean | null;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  onNewChat: () => void;
  onOpenSessionDrawer: () => void;
  onRefreshHealth: () => void;
  onOpenVoiceModal?: () => void;
  onOpenReasoningDrawer?: () => void;
  onOpenVerificationModal?: () => void;
}

function HeaderIcon({ name }: { name: 'history' | 'voice' | 'brain' | 'verify' }) {
  const paths = {
    history: <><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8" /><path d="M3 3v5h5m4-1v5l3 2" /></>,
    voice: <><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 12a7 7 0 0 0 14 0m-7 7v3m-4 0h8" /></>,
    brain: <><path d="M12 4a3 3 0 0 0-5.8 1.1A3.5 3.5 0 0 0 5 11a3.5 3.5 0 0 0 1 6.8A3 3 0 0 0 12 19V4Zm0 0a3 3 0 0 1 5.8 1.1A3.5 3.5 0 0 1 19 11a3.5 3.5 0 0 1-1 6.8A3 3 0 0 1 12 19V4Z" /></>,
    verify: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>
  };

  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  conversationId,
  backendOnline,
  searchQuery,
  onSearchQueryChange,
  onNewChat,
  onOpenSessionDrawer,
  onRefreshHealth,
  onOpenVoiceModal,
  onOpenReasoningDrawer,
  onOpenVerificationModal
}) => (
  <header className="aura-topbar z-20 px-3 py-3 sm:px-5 lg:px-7">
    <div className="aura-topbar-pill mx-auto flex min-h-[62px] max-w-[1540px] items-center justify-between gap-4 rounded-[20px] border px-4 py-2.5 sm:px-5">
      <div className="aura-topbar-brand flex shrink-0 items-center gap-2.5">
        <AuraBrandMark />
        <span className="text-[14px] font-semibold tracking-[-0.02em] text-[#f5f2ff] sm:text-[15px]">Aura Support</span>
      </div>

      <div className="aura-topbar-tools flex min-w-0 flex-1 items-center justify-center gap-3">
        <nav className="aura-topbar-nav flex min-w-0 items-center justify-center gap-1" aria-label="Main navigation">
        <button type="button" onClick={onOpenSessionDrawer} className="aura-topbar-link" title="Open conversations">
          <HeaderIcon name="history" />
          <span>Conversations</span>
        </button>
        <button type="button" onClick={onOpenVoiceModal} className="aura-topbar-link" title="Open Voice Mode">
          <HeaderIcon name="voice" />
          <span>Voice mode</span>
        </button>
        <button type="button" onClick={onOpenReasoningDrawer} className="aura-topbar-link" title="Open Brain Trace">
          <HeaderIcon name="brain" />
          <span>Brain Trace</span>
        </button>
        <button type="button" onClick={onOpenVerificationModal} className="aura-topbar-link" title="Verify customer session">
          <HeaderIcon name="verify" />
          <span>Verify session</span>
        </button>
        </nav>
        <label className="aura-message-search flex h-9 w-[190px] shrink-0 items-center gap-2 rounded-xl border px-3">
          <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
          <input
            type="search"
            value={searchQuery}
            onChange={event => onSearchQueryChange(event.target.value)}
            placeholder="Search this chat"
            aria-label="Search messages in this chat"
            className="min-w-0 flex-1 bg-transparent text-[11px] outline-none placeholder:text-[#817b91]"
          />
          {searchQuery && <button type="button" onClick={() => onSearchQueryChange('')} className="text-[10px] text-[#a49fb2] hover:text-white" aria-label="Clear chat search">×</button>}
        </label>
      </div>

      <div className="aura-topbar-actions flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onRefreshHealth}
          className={`aura-connection-pill flex h-9 items-center gap-1.5 rounded-xl border px-2.5 text-[10px] font-semibold transition ${
            backendOnline === true
              ? 'border-emerald-300/15 bg-emerald-400/[.08] text-emerald-200'
              : backendOnline === false
                ? 'border-rose-300/15 bg-rose-400/[.08] text-rose-200'
                : 'border-amber-300/15 bg-amber-400/[.08] text-amber-100'
          }`}
          title="Click to check Aura Support connection"
          aria-label={`Support connection: ${backendOnline === true ? 'Connected' : backendOnline === false ? 'Offline' : 'Checking'}. Click to check status`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${backendOnline === true ? 'bg-emerald-400' : backendOnline === false ? 'bg-rose-400' : 'bg-amber-300'}`} />
          <span className="aura-connection-label">{backendOnline === true ? 'Connected' : backendOnline === false ? 'Offline' : 'Checking'}</span>
        </button>
        <button
          type="button"
          onClick={onOpenSessionDrawer}
          className="aura-session-pill rounded-xl border px-2.5 py-2 text-[11px] font-mono font-medium transition"
          title="Current conversation"
        >
          {conversationId ? `#${conversationId}` : 'New'}
          <svg className="ml-1 inline h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m7 10 5 5 5-5" /></svg>
        </button>
        <button
          type="button"
          onClick={onNewChat}
          className="aura-topbar-new-chat flex h-9 items-center gap-1.5 rounded-xl px-3 text-[11px] font-semibold text-white shadow-[0_4px_12px_rgba(102,84,217,.18)] transition hover:bg-[#5946cf] active:scale-[.98] sm:px-3.5 sm:text-xs"
          title="Start a new support conversation"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m-7-7h14" /></svg>
          <span>New chat</span>
        </button>
      </div>
    </div>
  </header>
);
