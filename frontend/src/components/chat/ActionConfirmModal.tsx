'use client';

import React from 'react';

interface ActionConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onClose: () => void;
  tone?: 'warning' | 'info';
}

export const ActionConfirmModal: React.FC<ActionConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel,
  onConfirm,
  onClose,
  tone = 'warning'
}) => {
  if (!isOpen) return null;
  const iconClass = tone === 'warning' ? 'bg-amber-500/15' : 'bg-violet-500/15';
  const buttonClass = tone === 'warning' ? 'bg-amber-600 hover:bg-amber-500' : 'bg-violet-600 hover:bg-violet-500';

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 text-white shadow-2xl">
        <div className="mb-4 flex items-start gap-3">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg ${iconClass}`}>
            {tone === 'warning' ? '⚠️' : '👤'}
          </div>
          <div>
            <h2 className="text-base font-bold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">{message}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button type="button" onClick={onClose} className="flex-1 rounded-lg bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-slate-700">
            Keep order
          </button>
          <button type="button" onClick={onConfirm} className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-semibold text-white ${buttonClass}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
