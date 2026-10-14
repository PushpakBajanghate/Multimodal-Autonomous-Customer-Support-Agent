'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ConversationProvider, useConversation } from '@elevenlabs/react';
import { ChatApiError, getElevenLabsSessionUrl } from '../../services/chatApi';
import { AuraBrandMark } from './AuraBrandMark';

interface VoiceSimulationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type LanguagePreference = 'auto' | 'English' | 'Hindi' | 'Hinglish';

export const VoiceSimulationModal: React.FC<VoiceSimulationModalProps> = ({ isOpen, onClose }) =>
  isOpen ? <ConversationProvider><VoiceSupportDialog onClose={onClose} /></ConversationProvider> : null;

function VoiceSupportDialog({ onClose }: Pick<VoiceSimulationModalProps, 'onClose'>) {
  const {
    status, isSpeaking, isListening, isMuted, setMuted, startSession, endSession,
    sendUserMessage, message
  } = useConversation();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [question, setQuestion] = useState('');
  const [language, setLanguage] = useState<LanguagePreference>('auto');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [starting, setStarting] = useState(false);
  const startupAbortRef = useRef<AbortController | null>(null);

  const stopSession = useCallback(() => {
    startupAbortRef.current?.abort();
    startupAbortRef.current = null;
    endSession();
    setStarting(false);
  }, [endSession]);

  useEffect(() => () => endSession(), [endSession]);

  const startConversation = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanQuestion = question.trim();
    if (cleanName.length < 2 || cleanName.length > 100 || cleanQuestion.length < 3 || cleanQuestion.length > 1000) {
      setError('Enter your name and a question (3–1,000 characters).');
      return;
    }
    if (phone && !/^\+?[\d\s().-]{7,20}$/.test(phone.trim())) {
      setError('Enter a valid phone number, or leave it blank.');
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access is not supported by this browser. You can still use text support.');
      return;
    }

    setError('');
    setNotice('');
    setStarting(true);
    const controller = new AbortController();
    startupAbortRef.current = controller;
    let permissionStream: MediaStream | undefined;
    try {
      // Request permission from the user gesture and close the preflight stream immediately.
      permissionStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      permissionStream.getTracks().forEach(track => track.stop());
      if (controller.signal.aborted) return;
      const signedUrl = await getElevenLabsSessionUrl(controller.signal);
      if (controller.signal.aborted) return;
      await startSession({
        signedUrl,
        connectionType: 'websocket',
        dynamicVariables: {
          customer_name: cleanName,
          customer_phone: phone.trim(),
          customer_question: cleanQuestion,
          preferred_language: language
        },
        onConnect: () => {
          setStarting(false);
          // This is the customer's real first utterance in the live agent session.
          sendUserMessage(cleanQuestion);
        },
        onDisconnect: () => setStarting(false),
        onInterruption: () => setNotice('Aura was interrupted. Go ahead; it is listening.'),
        onError: msg => {
          setStarting(false);
          setError(`Voice session error: ${msg}`);
        }
      });
    } catch (cause) {
      permissionStream?.getTracks().forEach(track => track.stop());
      if (controller.signal.aborted) return;
      startupAbortRef.current = null;
      setStarting(false);
      const err = cause as DOMException;
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        setError('Microphone permission was denied. Allow microphone access in your browser settings, then try again.');
      } else if (cause instanceof ChatApiError) {
        setError(cause.message);
      } else {
        setError(cause instanceof Error ? cause.message : 'Could not start the voice session. Please try again.');
      }
      stopSession();
    }
  };

  const close = () => {
    stopSession();
    onClose();
  };

  const connected = status === 'connected';
  const statusText = starting || status === 'connecting'
    ? 'Connecting to your support agent…'
    : connected
      ? isSpeaking ? 'Aura is speaking' : isListening ? 'Listening — speak naturally' : 'Connected'
      : 'Ready for a live voice conversation';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#211c38]/45 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="voice-title">
      <div className="relative max-h-[95vh] w-full max-w-lg overflow-y-auto rounded-3xl border border-[#ebe8f3] bg-white p-6 text-[#302d43] shadow-2xl sm:p-8">
        <button type="button" onClick={close} className="absolute right-4 top-4 rounded-lg p-2 text-[#777388] hover:bg-[#f5f3fa]" aria-label="Close voice support">✕</button>
        <div className="mb-4 flex items-center gap-3">
          <AuraBrandMark />
          <div><h2 id="voice-title" className="text-xl font-bold">Talk to Aura</h2><p className="text-sm text-[#858194]">Live browser voice support</p></div>
        </div>

        <div className="mb-5 rounded-2xl bg-[#f8f6ff] p-4" aria-live="polite">
          <div className="flex items-center gap-3">
            <span className={`h-3 w-3 rounded-full ${connected ? 'bg-emerald-500' : starting || status === 'connecting' ? 'animate-pulse bg-amber-500' : 'bg-slate-300'}`} />
            <p className="text-sm font-medium">{statusText}</p>
          </div>
          {connected && <p className="mt-2 text-xs text-[#858194]">Interrupt Aura at any time by speaking. The agent handles interruptions automatically.</p>}
        </div>

        {message && connected && <div className="mb-4 max-h-32 overflow-auto rounded-xl border border-[#eeebf4] p-3 text-sm" aria-live="polite">{message}</div>}
        {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert"><p>{error}</p><button type="button" onClick={close} className="mt-2 font-semibold underline">Continue with text support</button></div>}
        {notice && <p className="mb-4 text-sm text-violet-700" role="status">{notice}</p>}

        {!connected && !starting && (
          <form onSubmit={startConversation} className="space-y-4">
            <label className="block text-sm font-medium">Your name
              <input required minLength={2} maxLength={100} autoComplete="name" value={name} onChange={e => setName(e.target.value)} className="mt-1 w-full rounded-xl border border-[#e9e6f0] px-3 py-2.5 outline-none focus:border-violet-500" />
            </label>
            <label className="block text-sm font-medium">Phone number <span className="font-normal text-[#858194]">(optional)</span>
              <input type="tel" autoComplete="tel" maxLength={20} value={phone} onChange={e => setPhone(e.target.value)} placeholder="Only if you want a callback" className="mt-1 w-full rounded-xl border border-[#e9e6f0] px-3 py-2.5 outline-none focus:border-violet-500" />
            </label>
            <label className="block text-sm font-medium">How can we help?
              <textarea required minLength={3} maxLength={1000} rows={3} value={question} onChange={e => setQuestion(e.target.value)} className="mt-1 w-full resize-y rounded-xl border border-[#e9e6f0] px-3 py-2.5 outline-none focus:border-violet-500" />
            </label>
            <label className="block text-sm font-medium">Language preference
              <select value={language} onChange={e => setLanguage(e.target.value as LanguagePreference)} className="mt-1 w-full rounded-xl border border-[#e9e6f0] bg-white px-3 py-2.5">
                <option value="auto">Let Aura choose</option><option value="English">English</option><option value="Hindi">Hindi</option><option value="Hinglish">Hinglish</option>
              </select>
            </label>
            <p className="text-xs leading-relaxed text-[#858194]">Your browser will ask for microphone access. Your name, optional phone, question, and language are shared with the configured support agent for this session.</p>
            <button type="submit" disabled={starting} className="w-full rounded-xl bg-[#6654d9] px-4 py-3 font-semibold text-white transition hover:bg-[#5946cf] disabled:cursor-wait disabled:opacity-60">
              {starting ? 'Connecting…' : 'Talk to AI Agent'}
            </button>
          </form>
        )}

        {connected && <div className="mt-5 flex gap-3">
          <button type="button" onClick={() => setMuted(!isMuted)} className="flex-1 rounded-xl border border-[#e9e6f0] px-4 py-3 font-medium">{isMuted ? 'Unmute microphone' : 'Mute microphone'}</button>
          <button type="button" onClick={close} className="flex-1 rounded-xl bg-rose-600 px-4 py-3 font-semibold text-white">End conversation</button>
        </div>}

        {(starting || status === 'connecting') && <button type="button" onClick={close} className="mt-4 w-full rounded-xl border border-[#e9e6f0] px-4 py-2.5">Cancel connection</button>}
      </div>
    </div>
  );
}
