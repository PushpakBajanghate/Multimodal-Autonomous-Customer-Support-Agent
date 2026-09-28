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
    <div className="mx-4 my-2 flex animate-fade-in items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs text-rose-800 shadow-sm">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-100 font-bold text-rose-600">
          !
        </span>
        <div className="truncate">
          <span className="mr-1.5 font-semibold text-rose-800">Connection issue:</span>
          <span>{error}</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="cursor-pointer rounded bg-rose-600 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-rose-700"
          >
            Retry
          </button>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="cursor-pointer p-1 text-rose-500 transition-colors hover:text-rose-800"
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
