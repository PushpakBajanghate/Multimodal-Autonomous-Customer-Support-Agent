'use client';

import React, { useState } from 'react';
import { AuraBrandMark } from '../chat/AuraBrandMark';
import { customerLogin, customerRegister, ChatApiError } from '../../services/chatApi';
import { CustomerUser } from '../../types/auth';

interface AuthScreenProps {
  onAuthSuccess: (user: CustomerUser) => void;
  backendOnline: boolean | null;
  onRefreshHealth: () => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({
  onAuthSuccess,
  backendOnline,
  onRefreshHealth
}) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    if (mode === 'register' && !name.trim()) {
      setErrorMessage('Please enter your full name.');
      return;
    }

    if (mode === 'register' && password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    setIsLoading(true);
    try {
      if (mode === 'register') {
        const authData = await customerRegister(name.trim(), email.trim(), password);
        onAuthSuccess(authData);
      } else {
        const authData = await customerLogin(email.trim(), password);
        onAuthSuccess(authData);
      }
    } catch (err: unknown) {
      if (err instanceof ChatApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to authentication service. Please ensure backend is running.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-[#0d0b18] px-4 py-8 text-[#f5f2ff] selection:bg-violet-500/30">
      {/* Decorative background glow */}
      <div className="pointer-events-none fixed inset-0 flex items-center justify-center">
        <div className="h-[480px] w-[480px] rounded-full bg-violet-600/15 blur-[120px]" />
        <div className="h-[320px] w-[320px] rounded-full bg-indigo-500/15 blur-[100px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Brand Header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-600/10 shadow-[0_0_24px_rgba(124,58,237,0.25)]">
            <AuraBrandMark />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Aura Support</h1>
          <p className="mt-1 text-xs text-[#9d97b0] sm:text-sm">
            Autonomous AI Customer Support & Order Management
          </p>

          {/* Connection status pill */}
          <button
            type="button"
            onClick={onRefreshHealth}
            className={`mt-3 flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium transition ${
              backendOnline === true
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                : backendOnline === false
                  ? 'border-rose-500/20 bg-rose-500/10 text-rose-300'
                  : 'border-amber-500/20 bg-amber-500/10 text-amber-200'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                backendOnline === true
                  ? 'bg-emerald-400'
                  : backendOnline === false
                    ? 'bg-rose-400'
                    : 'bg-amber-300'
              }`}
            />
            <span>
              {backendOnline === true
                ? 'Backend Online'
                : backendOnline === false
                  ? 'Backend Offline (Click to retry)'
                  : 'Checking Service...'}
            </span>
          </button>
        </div>

        {/* Auth Card */}
        <div className="rounded-2xl border border-white/10 bg-[#16122b]/80 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
          {/* Tabs */}
          <div className="mb-6 flex rounded-xl border border-white/10 bg-black/20 p-1">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setErrorMessage(null);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                mode === 'login'
                  ? 'bg-violet-600 text-white shadow'
                  : 'text-[#9d97b0] hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setErrorMessage(null);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                mode === 'register'
                  ? 'bg-violet-600 text-white shadow'
                  : 'text-[#9d97b0] hover:text-white'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
              <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="mb-1 block text-xs font-medium text-[#c5c0d8]">
                  Full Name
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Pushpak Bajanghate"
                    required
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 pl-10 text-xs text-white placeholder:text-[#6e6884] focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                  />
                  <svg className="absolute left-3 top-3 h-4 w-4 text-[#7b7592]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
              </div>
            )}

            <div>
              <label className="mb-1 block text-xs font-medium text-[#c5c0d8]">
                Email Address
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 pl-10 text-xs text-white placeholder:text-[#6e6884] focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
                <svg className="absolute left-3 top-3 h-4 w-4 text-[#7b7592]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-[#c5c0d8]">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? 'At least 6 characters' : 'Enter your password'}
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 pl-10 pr-10 text-xs text-white placeholder:text-[#6e6884] focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
                <svg className="absolute left-3 top-3 h-4 w-4 text-[#7b7592]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-[#7b7592] hover:text-white"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-2.5 text-xs font-semibold text-white shadow-[0_4px_16px_rgba(124,58,237,0.3)] transition hover:bg-violet-500 active:scale-[0.99] disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>{mode === 'register' ? 'Creating Account...' : 'Signing In...'}</span>
                </>
              ) : (
                <span>{mode === 'register' ? 'Create Account & Enter Chat' : 'Sign In to Aura'}</span>
              )}
            </button>
          </form>
        </div>

        {/* Footer info */}
        <p className="mt-6 text-center text-[11px] text-[#6e6884]">
          Aura Multimodal Autonomous Customer Support &bull; Safe & Isolated Access
        </p>
      </div>
    </div>
  );
};
