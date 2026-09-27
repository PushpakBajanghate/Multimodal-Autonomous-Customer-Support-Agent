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
    <div className="fixed inset-0 z-50 flex animate-fade-in justify-end bg-[#211c38]/25 backdrop-blur-sm">
      {/* Backdrop click to close */}
      <div className="flex-1" onClick={onClose} />

      {/* Drawer content */}
      <div className="flex h-full w-full max-w-sm flex-col justify-between overflow-y-auto border-l border-[#e9e6f0] bg-white p-6 shadow-2xl">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#efedf5] pb-4">
            <div>
              <h2 className="text-base font-bold text-[#302d43]">Conversation history</h2>
              <p className="text-xs text-[#9692a5]">Pick up where you left off</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-lg p-1.5 text-[#9692a5] transition-colors hover:bg-[#f5f3fa] hover:text-[#4d4960]"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Current Session Info */}
          <div className="mt-5 rounded-xl border border-[#ebe8f3] bg-[#faf9fd] p-4">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-[#a09caf]">
              Active Session
            </span>
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold text-[#6b58d5]">
                {currentConversationId ? `Session #${currentConversationId}` : 'Unassigned (Starts on send)'}
              </span>
              <span className="rounded-full border border-[#d8f0e4] bg-[#f0faf5] px-2 py-0.5 text-[10px] text-[#35865d]">
                Active
              </span>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-[#8e8a9e]">
              Messages in this session are automatically persisted to the backend database tables.
            </p>
          </div>

          {/* Past Sessions List */}
          <div className="mt-6">
            <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-[#777388]">
              Recent Sessions
            </h3>
            {savedSessionIds.length === 0 ? (
              <p className="py-3 text-center text-xs italic text-[#a09caf]">
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
                        ? 'border-[#dcd5fb] bg-[#f5f2ff] text-[#5e4bc8]'
                        : 'border-[#efedf5] bg-white text-[#625e73] hover:border-[#dcd5fb] hover:text-[#5140bb]'
                    }`}
                  >
                    <div>
                      <span className="font-mono font-medium text-xs">
                        Conversation #{id}
                      </span>
                      <span className="mt-0.5 block text-[10px] text-[#a09caf]">
                        Click to restore history
                      </span>
                    </div>
                    {id === currentConversationId && (
                      <span className="text-xs font-bold text-[#6b58d5]">✓ Active</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="space-y-2.5 border-t border-[#efedf5] pt-6">
          <button
            type="button"
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full cursor-pointer rounded-xl bg-[#6654d9] px-4 py-2.5 text-xs font-semibold text-white shadow-md transition-colors hover:bg-[#5946cf]"
          >
            + Start Fresh Conversation
          </button>
          <button
            type="button"
            onClick={() => {
              onClearHistory();
              onClose();
            }}
            className="w-full cursor-pointer rounded-xl border border-[#ebe8f1] bg-white px-4 py-2 text-xs font-medium text-[#8c879b] transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"
          >
            Clear Local Cache
          </button>
        </div>
      </div>
    </div>
  );
};
