'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

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

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const speakText = useCallback((text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const clean = text.replace(/[•*#_`]/g, ' ');
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  const handleVoiceSubmit = useCallback(async (spokenText: string) => {
    if (!spokenText.trim()) return;
    setIsProcessing(true);
    setTranscript(spokenText);

    try {
      const response = await onSendVoiceTranscript(spokenText);
      if (response && typeof response === 'string') {
        setAgentSpokenResponse(response);
        speakText(response);
      }
    } finally {
      setIsProcessing(false);
    }
  }, [onSendVoiceTranscript, speakText]);

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
      recognition.lang = 'en-US';

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
  }, [isCalling, isMuted, handleVoiceSubmit]);

  const startCall = () => {
    setCallDuration(0);
    setIsCalling(true);
    setTranscript('');
    setAgentSpokenResponse('Connected to Aura Voice Gateway. Speak your inquiry into the microphone...');
    speakText('Hello, you are connected to Aura Voice Support. How can I help you with your order today?');

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md transition-all">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative overflow-hidden flex flex-col items-center text-center">
        {/* Background ambient glow */}
        <div className={`absolute top-0 inset-x-0 h-32 bg-gradient-to-b ${isCalling ? 'from-blue-600/20' : 'from-slate-800/20'} to-transparent -z-10`} />

        {/* Close Button */}
        <button
          type="button"
          onClick={endCall}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Agent Avatar & Waveform Animation */}
        <div className="relative my-4 flex items-center justify-center">
          <div className={`w-24 h-24 rounded-full flex items-center justify-center text-3xl shadow-xl transition-all duration-500 ${
            isCalling
              ? 'bg-gradient-to-tr from-blue-600 to-indigo-500 ring-8 ring-blue-500/20 animate-pulse'
              : 'bg-slate-800 border border-slate-700'
          }`}>
            🎙️
          </div>
          {isCalling && (
            <div className="absolute -inset-3 rounded-full border border-blue-400/30 animate-ping pointer-events-none" />
          )}
        </div>

        <h3 className="text-lg font-bold text-white">Aura Voice Channel</h3>
        <p className="text-xs text-slate-400 mt-1">
          {isCalling ? `Active Call • ${formatDuration(callDuration)} (Session #${conversationId || 'New'})` : 'Omnichannel Voice Telephony Simulation'}
        </p>

        {/* Live Audio Waveform Simulation */}
        {isCalling && (
          <div className="flex items-center justify-center gap-1.5 my-4 h-8">
            {[40, 70, 90, 60, 100, 50, 80, 45, 95, 30].map((h, i) => (
              <div
                key={i}
                className="w-1 bg-blue-400 rounded-full transition-all duration-300 animate-pulse"
                style={{
                  height: `${isProcessing ? h : 16}px`,
                  animationDelay: `${i * 100}ms`
                }}
              />
            ))}
          </div>
        )}

        {/* Spoken Text Transcripts */}
        <div className="w-full bg-slate-950/70 border border-slate-800 rounded-xl p-3 my-3 text-left min-h-[90px] max-h-[120px] overflow-y-auto">
          {transcript ? (
            <div className="text-xs text-slate-200">
              <span className="text-blue-400 font-semibold">You said: </span>
              {transcript}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic text-center pt-3">
              {isCalling ? 'Listening to speech input...' : 'Click &quot;Start Voice Call&quot; to begin speaking with Aura.'}
            </p>
          )}

          {agentSpokenResponse && (
            <div className="text-xs text-slate-300 mt-2 pt-2 border-t border-slate-800">
              <span className="text-emerald-400 font-semibold">Aura: </span>
              {agentSpokenResponse}
            </div>
          )}
        </div>

        {/* Preset Voice Prompt Shortcuts */}
        {isCalling && (
          <div className="w-full my-2">
            <p className="text-[11px] text-slate-400 mb-1 text-left">Quick Voice Test Queries:</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                "Where is my order #1?",
                "Refund order #2 broken item",
                "Cancel my active order #1"
              ].map((query, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleVoiceSubmit(query)}
                  disabled={isProcessing}
                  className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300 border border-slate-700 transition-colors cursor-pointer"
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
              className="flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
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
                    ? 'bg-amber-900/40 text-amber-200 border-amber-700'
                    : 'bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700'
                }`}
                title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
              >
                {isMuted ? '🔇 Muted' : '🎤 Mute'}
              </button>

              <button
                type="button"
                onClick={endCall}
                className="flex-1 py-3 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
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