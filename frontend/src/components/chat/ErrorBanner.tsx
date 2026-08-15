'use client';

import React from 'react';

interface ErrorBannerProps {
  error: string | null;
  onDismiss: () => void;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onDismiss,
  onRetry
}) => {
  if (!error) return null;

  return (
    <div className="mx-4 my-2 px-4 py-2.5 rounded-xl bg-rose-950/90 border border-rose-800/80 text-rose-200 text-xs flex items-center justify-between gap-3 shadow-lg animate-fade-in">
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="w-5 h-5 rounded-full bg-rose-900 flex items-center justify-center text-rose-300 shrink-0 font-bold">
          !
        </span>
        <div className="truncate">
          <span className="font-semibold text-rose-100 mr-1.5">Connection Error:</span>
          <span>{error}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-2.5 py-1 rounded bg-rose-800 hover:bg-rose-700 text-white font-medium text-xs transition-colors cursor-pointer"
          >
            Retry
          </button>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 text-rose-400 hover:text-rose-100 transition-colors cursor-pointer"
          aria-label="Dismiss error"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};
