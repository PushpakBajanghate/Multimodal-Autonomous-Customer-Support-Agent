'use client';

import React from 'react';

interface ChatHeaderProps {
  conversationId: number | null;
  backendOnline: boolean | null;
  onNewChat: () => void;
  onOpenSessionDrawer: () => void;
  onRefreshHealth: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  conversationId,
  backendOnline,
  onNewChat,
  onOpenSessionDrawer,
  onRefreshHealth
}) => {
  return (
    <header className="px-5 py-3.5 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 flex items-center justify-between gap-4 sticky top-0 z-20">
      {/* Agent Identity & Status */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-semibold text-sm shadow-md ring-2 ring-slate-800">
            ✨
          </div>
          <span
            className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full ring-2 ring-slate-900 ${
              backendOnline === false
                ? 'bg-rose-500'
                : 'bg-emerald-500 animate-pulse'
            }`}
            title={backendOnline === false ? 'Backend Offline' : 'Aura Active'}
          />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-semibold text-sm text-slate-100 leading-tight">
              Aura Support Assistant
            </h1>
            <span className="text-[10px] uppercase font-mono tracking-wider font-semibold px-1.5 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/80">
              AI Care
            </span>
          </div>
          <p className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Always online • Instant replies
          </p>
        </div>
      </div>

      {/* Actions & Session Metadata */}
      <div className="flex items-center gap-2">
        {/* Session ID Badge / Drawer Toggle */}
        <button
          type="button"
          onClick={onOpenSessionDrawer}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 text-xs font-mono transition-all hover:border-slate-600 cursor-pointer"
          title="Click to manage conversation sessions"
        >
          <span className="text-[10px] text-slate-400 font-sans">Session</span>
          <span className="font-semibold text-blue-400">
            {conversationId ? `#${conversationId}` : 'New'}
          </span>
          <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Backend Status indicator */}
        <button
          type="button"
          onClick={onRefreshHealth}
          className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium border transition-colors cursor-pointer ${
            backendOnline === true
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50 hover:bg-emerald-900/40'
              : backendOnline === false
              ? 'bg-rose-950/50 text-rose-300 border-rose-800 hover:bg-rose-900/50'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}
          title="Click to check backend status"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              backendOnline === true
                ? 'bg-emerald-400'
                : backendOnline === false
                ? 'bg-rose-400'
                : 'bg-amber-400'
            }`}
          />
          <span className="hidden sm:inline">
            {backendOnline === true ? 'Connected' : backendOnline === false ? 'Disconnected' : 'Checking'}
          </span>
        </button>

        {/* New Chat Button */}
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 active:scale-95 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
          title="Start a new support conversation"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span className="hidden sm:inline">New Chat</span>
        </button>
      </div>
    </header>
  );
};
