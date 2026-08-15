'use client';

import React from 'react';

interface SessionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentConversationId: number | null;
  savedSessionIds: number[];
  onSelectSession: (id: number) => void;
  onNewChat: () => void;
  onClearHistory: () => void;
}

export const SessionDrawer: React.FC<SessionDrawerProps> = ({
  isOpen,
  onClose,
  currentConversationId,
  savedSessionIds,
  onSelectSession,
  onNewChat,
  onClearHistory
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-fade-in">
      {/* Backdrop click to close */}
      <div className="flex-1" onClick={onClose} />

      {/* Drawer content */}
      <div className="w-full max-w-sm bg-slate-900 border-l border-slate-800 p-6 flex flex-col justify-between shadow-2xl h-full overflow-y-auto">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-base font-bold text-white">Support Sessions</h2>
              <p className="text-xs text-slate-400">Conversations saved in PostgreSQL</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Current Session Info */}
          <div className="mt-5 p-4 rounded-xl bg-slate-950 border border-slate-800/80">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
              Active Session
            </span>
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold text-blue-400">
                {currentConversationId ? `Session #${currentConversationId}` : 'Unassigned (Starts on send)'}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900">
                Active
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              Messages in this session are automatically persisted to the backend database tables.
            </p>
          </div>

          {/* Past Sessions List */}
          <div className="mt-6">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
              Recent Sessions
            </h3>
            {savedSessionIds.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-3 text-center">
                No previous sessions recorded yet.
              </p>
            ) : (
              <div className="space-y-2">
                {savedSessionIds.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      onSelectSession(id);
                      onClose();
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                      id === currentConversationId
                        ? 'bg-blue-950/60 border-blue-800/80 text-blue-200'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white'
                    }`}
                  >
                    <div>
                      <span className="font-mono font-medium text-xs">
                        Conversation #{id}
                      </span>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        Click to restore history
                      </span>
                    </div>
                    {id === currentConversationId && (
                      <span className="text-blue-400 text-xs font-bold">✓ Active</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-6 border-t border-slate-800 space-y-2.5">
          <button
            type="button"
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-md transition-colors cursor-pointer"
          >
            + Start Fresh Conversation
          </button>
          <button
            type="button"
            onClick={() => {
              onClearHistory();
              onClose();
            }}
            className="w-full py-2 px-4 rounded-xl bg-slate-800/80 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-700/60 hover:border-rose-900 transition-colors text-xs font-medium cursor-pointer"
          >
            Clear Local Cache
          </button>
        </div>
      </div>
    </div>
  );
};
