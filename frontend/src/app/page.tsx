'use client';

import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
}

interface Thought {
  id: string;
  stage: 'perception' | 'reasoning' | 'action';
  detail: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', sender: 'agent', text: 'Hello! I am Aura, your multimodal support assistant. How can I help you today?', timestamp: '12:00 PM' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isCalling, setIsCalling] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [thoughts, setThoughts] = useState<Thought[]>([
    { id: 't1', stage: 'perception', detail: 'Initialized agent context. Listening on Web Chat & VoIP.' }
  ]);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const callTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Call timer effect
  useEffect(() => {
    if (isCalling) {
      callTimerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
      
      // Add mock agent thought for call start
      addThought('perception', 'Incoming audio stream connected via WebRTC.');
      addThought('reasoning', 'Analyzing tone of voice and query intent... System status check: normal.');
      addThought('action', 'Synthesized audio greeting response.');
    } else {
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
      setCallDuration(0);
    }

    return () => {
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
    };
  }, [isCalling]);

  // Check backend health
  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => {
        if (res.ok) {
          setBackendStatus('online');
        } else {
          setBackendStatus('offline');
        }
      })
      .catch(() => {
        setBackendStatus('offline');
      });
  }, []);

  const addThought = (stage: 'perception' | 'reasoning' | 'action', detail: string) => {
    const id = Math.random().toString();
    setThoughts(prev => [...prev, { id, stage, detail }]);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userMsg: Message = {
      id: Math.random().toString(),
      sender: 'user',
      text: inputText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');

    // Trigger mock agent thoughts
    addThought('perception', `Received text input: "${userMsg.text}"`);
    
    setTimeout(() => {
      addThought('reasoning', 'Retrieving knowledge base embeddings & checking agent policy...');
    }, 600);

    setTimeout(() => {
      const responseText = getMockResponse(userMsg.text);
      const agentMsg: Message = {
        id: Math.random().toString(),
        sender: 'agent',
        text: responseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, agentMsg]);
      addThought('action', `Dispatched API response: "${responseText}"`);
    }, 1500);
  };

  const getMockResponse = (input: string) => {
    const query = input.toLowerCase();
    if (query.includes('hello') || query.includes('hi')) {
      return "Hi there! How can I assist you with your customer support inquiries today?";
    }
    if (query.includes('refund') || query.includes('money')) {
      return "I can help process standard refunds. Please provide your Order ID, and I will review the eligibility criteria.";
    }
    if (query.includes('track') || query.includes('order')) {
      return "To track your shipment, please share your order number. I will fetch the live courier coordinates for you.";
    }
    return "Understood. I've logged your request regarding that issue and am checking the best path forward to resolve it.";
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Top Banner / Navigation */}
      <header className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 rounded-full bg-emerald-500 animate-pulse" />
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">AURA</h1>
            <p className="text-xs text-slate-400">Multimodal Autonomous Agent Brain</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full">
            <span className="text-slate-400">Backend API:</span>
            {backendStatus === 'checking' && <span className="text-amber-400 animate-pulse">Connecting...</span>}
            {backendStatus === 'online' && <span className="text-emerald-400 font-semibold">Online</span>}
            {backendStatus === 'offline' && <span className="text-rose-400 font-semibold">Offline (Run docker-compose)</span>}
          </div>
          <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full">
            <span className="text-slate-400">Channels:</span>
            <span className="text-slate-200">Web Chat / PSTN Voice</span>
          </div>
        </div>
      </header>

      {/* Main Content Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Interactive Chat (7 cols) */}
        <section className="lg:col-span-7 flex flex-col bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl h-[650px]">
          <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-200">Web Customer Portal</h2>
            <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded">Text Channel</span>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col max-w-[80%] ${
                  msg.sender === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'
                }`}
              >
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                    msg.sender === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-slate-800 text-slate-100 rounded-bl-none'
                  }`}
                >
                  {msg.text}
                </div>
                <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Form Input */}
          <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-800 bg-slate-900/50 flex gap-3">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask a question (e.g., 'refund policy', 'track order')..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors text-slate-100 placeholder-slate-500"
            />
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-500 transition-colors px-5 py-2.5 rounded-lg text-sm font-semibold text-white shadow-lg"
            >
              Send
            </button>
          </form>
        </section>

        {/* Right Column: Voice & Agent Brain Logs (5 cols) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          {/* Voice Simulator */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-2xl flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute top-4 right-4">
              <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded">Voice Channel (VoIP)</span>
            </div>

            <h3 className="font-semibold text-slate-200 mb-2">PSTN Phone Agent Simulator</h3>
            <p className="text-xs text-slate-400 max-w-xs mb-6">
              Simulate a phone call. Aura uses WebRTC/SIP to talk to clients with real-time text-to-speech.
            </p>

            {isCalling ? (
              <div className="flex flex-col items-center gap-4 py-4 w-full">
                {/* Waveform graphic */}
                <div className="flex items-center gap-1.5 h-12 justify-center w-full">
                  <div className="w-1.5 bg-emerald-500 rounded-full animate-[pulse_1s_infinite] h-8" />
                  <div className="w-1.5 bg-emerald-400 rounded-full animate-[pulse_0.7s_infinite] h-12" />
                  <div className="w-1.5 bg-emerald-500 rounded-full animate-[pulse_1.2s_infinite] h-6" />
                  <div className="w-1.5 bg-emerald-400 rounded-full animate-[pulse_0.9s_infinite] h-10" />
                  <div className="w-1.5 bg-emerald-500 rounded-full animate-[pulse_1.1s_infinite] h-4" />
                </div>
                <div className="text-emerald-400 font-mono text-sm font-semibold tracking-wider">
                  CALL ACTIVE: {formatDuration(callDuration)}
                </div>
                <button
                  onClick={() => setIsCalling(false)}
                  className="bg-rose-600 hover:bg-rose-500 transition-colors px-6 py-2.5 rounded-full text-sm font-bold text-white shadow-lg flex items-center gap-2 mt-2"
                >
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
                  </svg>
                  End Session
                </button>
              </div>
            ) : (
              <div className="py-4">
                <button
                  onClick={() => setIsCalling(true)}
                  className="bg-emerald-600 hover:bg-emerald-500 transition-colors px-8 py-3 rounded-full text-sm font-bold text-white shadow-lg flex items-center gap-2 animate-bounce"
                >
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                    <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z" />
                  </svg>
                  Initiate Customer Voice Call
                </button>
              </div>
            )}
          </div>

          {/* Autonomous Brain Thought Logs */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-2xl flex-1 flex flex-col min-h-[300px]">
            <h3 className="font-semibold text-slate-200 mb-4 border-b border-slate-800 pb-2">Autonomous Agent Thought Log</h3>
            <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs max-h-[250px] pr-2">
              {thoughts.map((thought) => (
                <div key={thought.id} className="border-l-2 border-slate-800 pl-3 py-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                      thought.stage === 'perception' ? 'bg-indigo-950 text-indigo-400 border border-indigo-900/50' :
                      thought.stage === 'reasoning' ? 'bg-amber-950 text-amber-400 border border-amber-900/50' :
                      'bg-emerald-950 text-emerald-400 border border-emerald-900/50'
                    }`}>
                      {thought.stage}
                    </span>
                    <span className="text-[10px] text-slate-500">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  </div>
                  <p className="text-slate-300 leading-normal">{thought.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-4 mt-auto text-center text-xs text-slate-500">
        © 2026 Multimodal Autonomous Customer Support Agent Setup. All channels synchronized.
      </footer>
    </div>
  );
}
