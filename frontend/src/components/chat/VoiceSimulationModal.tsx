'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { synthesizeVoice } from '../../services/chatApi';
import { AuraBrandMark } from './AuraBrandMark';

interface VoiceSimulationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendVoiceTranscript: (transcript: string) => Promise<string | void>;
  conversationId: number | null;
}

export const VoiceSimulationModal: React.FC<VoiceSimulationModalProps> = ({
  isOpen,
  onClose,
  onSendVoiceTranscript,
  conversationId
}) => {
  const [isCalling, setIsCalling] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [agentSpokenResponse, setAgentSpokenResponse] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [languageMode, setLanguageMode] = useState<'auto' | 'hi-IN' | 'en-IN'>('auto');
  const [voiceProvider, setVoiceProvider] = useState('browser');
  const [voiceNotice, setVoiceNotice] = useState('');

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const detectLanguage = useCallback((text: string) => {
    if (languageMode !== 'auto') return languageMode;
    if (/[\u0900-\u097F]/.test(text) || /\b(namaste|namaskar|mera|meri|mere|mujhe|haan|nahi|kya|hai|karna|karo|paisa|paise|kab|kahan|madad|sawal|jawab|bhejo|batao|chahiye|wapas)\b/i.test(text)) {
      return 'hi-IN';
    }
    return 'en-IN';
  }, [languageMode]);

  const speakText = useCallback(async (text: string, spokenLanguage = 'auto') => {
    const resolvedLanguage = detectLanguage(spokenLanguage === 'auto' ? text : spokenLanguage);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    try {
      const generated = await synthesizeVoice(text, resolvedLanguage);
      setVoiceProvider(generated.provider);
      setVoiceNotice(generated.reason || '');
      if (generated.audio_base64 && generated.audio_mime_type) {
        const audio = new Audio(`data:${generated.audio_mime_type};base64,${generated.audio_base64}`);
        audioRef.current = audio;
        await audio.play();
        return;
      }
    } catch (err) {
      setVoiceProvider('browser');
      setVoiceNotice(err instanceof Error ? err.message : 'Using browser voice fallback.');
    }

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const clean = text.replace(/[•*#_`]/g, ' ');
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.lang = resolvedLanguage;
      utterance.rate = resolvedLanguage.startsWith('hi') ? 0.92 : 0.98;
      utterance.pitch = 0.96;
      const voices = window.speechSynthesis.getVoices();
      const matchingVoice = voices.find(voice => voice.lang === resolvedLanguage) || voices.find(voice => voice.lang.startsWith(resolvedLanguage.slice(0, 2)));
      if (matchingVoice) utterance.voice = matchingVoice;
      window.speechSynthesis.speak(utterance);
    }
  }, [detectLanguage]);

  const handleVoiceSubmit = useCallback(async (spokenText: string) => {
    if (!spokenText.trim()) return;
    setIsProcessing(true);
    setTranscript(spokenText);

    try {
      const response = await onSendVoiceTranscript(spokenText);
      if (response && typeof response === 'string') {
        setAgentSpokenResponse(response);
        await speakText(response, detectLanguage(spokenText));
      }
    } finally {
      setIsProcessing(false);
    }
  }, [detectLanguage, onSendVoiceTranscript, speakText]);

  // Timer for call duration
  useEffect(() => {
    if (!isCalling) return;
    const interval = setInterval(() => {
      setCallDuration(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isCalling]);

  // Speech Recognition Setup
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = languageMode === 'auto' ? 'hi-IN' : languageMode;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        const text = event.results[0][0].transcript;
        setTranscript(text);
        handleVoiceSubmit(text);
      };

      recognition.onerror = () => {
        setIsProcessing(false);
      };

      recognition.onend = () => {
        if (isCalling && !isMuted) {
          try {
            recognition.start();
          } catch {
            // Ignore if already active
          }
        }
      };

      recognitionRef.current = recognition;
    }
  }, [isCalling, isMuted, handleVoiceSubmit, languageMode]);

  const startCall = () => {
    setCallDuration(0);
    setIsCalling(true);
    setTranscript('');
    setAgentSpokenResponse('Connected to Aura Support. Speak your inquiry into the microphone...');
    speakText(
      languageMode === 'hi-IN'
        ? 'Namaste, aap Aura Support se connected hain. Main aapki kaise madad kar sakti hoon?'
        : 'Hello, you are connected to Aura Support. How can I help you with your order today?',
      languageMode
    );

    if (recognitionRef.current && !isMuted) {
      try {
        recognitionRef.current.start();
      } catch {
        // Ignore
      }
    }
  };

  const endCall = () => {
    setIsCalling(false);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore
      }
    }
    onClose();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#211c38]/30 p-4 backdrop-blur-sm transition-all">
      <div className="relative flex w-full max-w-md flex-col items-center overflow-hidden rounded-[24px] border border-[#ebe8f3] bg-white p-6 text-center shadow-[0_24px_70px_rgba(31,25,61,.2)]">
        {/* Background ambient glow */}
        <div className={`absolute inset-x-0 top-0 -z-10 h-36 bg-gradient-to-b ${isCalling ? 'from-[#8a78e5]/15' : 'from-[#f1eeff]'} to-transparent`} />

        {/* Close Button */}
        <button
          type="button"
          onClick={endCall}
          className="absolute right-4 top-4 cursor-pointer rounded-lg p-1 text-[#9692a5] transition-colors hover:bg-[#f5f3fa] hover:text-[#4d4960]"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Agent Avatar & Waveform Animation */}
        <div className="relative my-4 flex items-center justify-center">
          <div className={`flex h-24 w-24 items-center justify-center rounded-full text-3xl shadow-xl transition-all duration-500 ${
            isCalling
              ? 'animate-pulse bg-gradient-to-tr from-[#8876ed] to-[#5945c7] ring-8 ring-[#8573e7]/15'
              : 'border border-[#e9e6f0] bg-[#f5f3fb]'
          }`}>
            <svg className={`h-9 w-9 ${isCalling ? 'text-white' : 'text-[#7461d7]'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 12a7 7 0 0 0 14 0m-7 7v3m-4 0h8" /></svg>
          </div>
          {isCalling && (
            <div className="pointer-events-none absolute -inset-3 animate-ping rounded-full border border-[#8573e7]/30" />
          )}
        </div>

        <div className="flex items-center gap-2">
          <AuraBrandMark />
          <h3 className="text-lg font-bold text-[#302d43]">Aura Support</h3>
        </div>
        <p className="mt-1 text-xs text-[#9692a5]">
          {isCalling ? `Active Call • ${formatDuration(callDuration)} (Session #${conversationId || 'New'})` : 'Omnichannel Voice Telephony Simulation'}
        </p>

        {!isCalling && (
          <div className="mt-4 grid w-full grid-cols-2 gap-2 text-left">
            <label className="text-[11px] text-[#8e8a9e]">
              Speech Language
              <select
                value={languageMode}
                onChange={event => setLanguageMode(event.target.value as 'auto' | 'hi-IN' | 'en-IN')}
                className="mt-1 w-full rounded-lg border border-[#e9e6f0] bg-[#fbfaff] px-2 py-2 text-xs text-[#504c63] outline-none focus:border-[#8a78e5]"
              >
                <option value="auto">Auto Hindi/English</option>
                <option value="hi-IN">Hindi / Hinglish</option>
                <option value="en-IN">English India</option>
              </select>
            </label>
            <div className="text-[11px] text-[#8e8a9e]">
              Voice Engine
              <div className="mt-1 min-h-[34px] rounded-lg border border-[#e9e6f0] bg-[#fbfaff] px-2 py-2 text-xs text-[#504c63]">
                {voiceProvider}
              </div>
            </div>
          </div>
        )}

        {/* Live Audio Waveform Simulation */}
        {isCalling && (
          <div className="flex items-center justify-center gap-1.5 my-4 h-8">
            {[40, 70, 90, 60, 100, 50, 80, 45, 95, 30].map((h, i) => (
              <div
                key={i}
                className="w-1 animate-pulse rounded-full bg-[#806de0] transition-all duration-300"
                style={{
                  height: `${isProcessing ? h : 16}px`,
                  animationDelay: `${i * 100}ms`
                }}
              />
            ))}
          </div>
        )}

        {/* Spoken Text Transcripts */}
        <div className="my-3 max-h-[120px] min-h-[90px] w-full overflow-y-auto rounded-xl border border-[#eeebf4] bg-[#faf9fd] p-3 text-left">
          {transcript ? (
            <div className="text-xs text-[#504c63]">
              <span className="font-semibold text-[#6b58d5]">You said: </span>
              {transcript}
            </div>
          ) : (
            <p className="pt-3 text-center text-xs italic text-[#a09caf]">
              {isCalling ? 'Listening to speech input...' : 'Click &quot;Start Voice Call&quot; to begin speaking with Aura.'}
            </p>
          )}

          {agentSpokenResponse && (
            <div className="mt-2 border-t border-[#ece9f2] pt-2 text-xs text-[#716d80]">
              <span className="font-semibold text-emerald-600">Aura: </span>
              {agentSpokenResponse}
            </div>
          )}
          {voiceNotice && (
            <div className="mt-2 border-t border-[#ece9f2] pt-2 text-[11px] text-amber-700">
              {voiceNotice}
            </div>
          )}
        </div>

        {/* Preset Voice Prompt Shortcuts */}
        {isCalling && (
          <div className="w-full my-2">
            <p className="mb-1 text-left text-[11px] text-[#8e8a9e]">Quick voice prompts:</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                "Where is my order #1?",
                "Mera order #1 kahan hai?",
                "Refund order #2 broken item",
                "Cancel my active order #1"
              ].map((query, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleVoiceSubmit(query)}
                  disabled={isProcessing}
                  className="cursor-pointer rounded-lg border border-[#e9e6f0] bg-white px-2 py-1 text-[11px] text-[#777388] transition-colors hover:border-[#d9d2f5] hover:bg-[#f8f6ff]"
                >
                  &quot;{query}&quot;
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center gap-3 mt-4 w-full">
          {!isCalling ? (
            <button
              type="button"
              onClick={startCall}
              className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl bg-[#6654d9] px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all hover:bg-[#5946cf] active:scale-95"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              Start Voice Call
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setIsMuted(!isMuted)}
                className={`p-3 rounded-xl border text-sm font-semibold transition-all cursor-pointer ${
                  isMuted
                    ? 'border-amber-200 bg-amber-50 text-amber-700'
                    : 'border-[#e9e6f0] bg-[#f7f6fb] text-[#716d80] hover:bg-[#eeecf4]'
                }`}
                title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
              >
                {isMuted ? 'Muted' : 'Mute mic'}
              </button>

              <button
                type="button"
                onClick={endCall}
                className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl bg-rose-500 px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all hover:bg-rose-600 active:scale-95"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
                </svg>
                End Call
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
