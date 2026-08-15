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
  timestamp: string;
}

// Keep sequence counters outside the component to guarantee absolute render purity
let messageIdCounter = 1;
let thoughtIdCounter = 1;

const generateMessageId = () => {
  messageIdCounter += 1;
  return `msg-${messageIdCounter}`;
};

const generateThoughtId = () => {
  thoughtIdCounter += 1;
  return `thought-${thoughtIdCounter}`;
};

const API_BASE = 'http://localhost:8000/api/v1';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', sender: 'agent', text: 'Hello! I am Aura, your multimodal support assistant. How can I help you today? (Try typing: "track 1", "refund 1", "cancel 1", "customer 1")', timestamp: '12:00 PM' }
  ]);
  const [inputText, setInputText] = useState('');
  const [isCalling, setIsCalling] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [thoughts, setThoughts] = useState<Thought[]>([
    { id: 't1', stage: 'perception', detail: 'Initialized agent context. Listening on Web Chat & VoIP.', timestamp: '12:00:00 PM' }
  ]);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const callTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Helper function defined before hooks to prevent "accessed before declaration" warnings
  const addThought = (stage: 'perception' | 'reasoning' | 'action', detail: string) => {
    const id = generateThoughtId();
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setThoughts(prev => [...prev, { id, stage, detail, timestamp }]);
  };

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
    } else {
      if (callTimerRef.current) {
        clearInterval(callTimerRef.current);
      }
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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userText = inputText;
    const userMsg: Message = {
      id: generateMessageId(),
      sender: 'user',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');

    addThought('perception', `Received text input: "${userText}"`);

    const lower = userText.toLowerCase();
    const matchId = userText.match(/\d+/);
    const parsedId = matchId ? parseInt(matchId[0], 10) : 1;

    // Simulate Agent Thinking & Tool Selection
    setTimeout(async () => {
      addThought('reasoning', `Analyzing query intent. Evaluating REST tool execution for entity ID #${parsedId}...`);
      
      let agentReply = "";
      let toolExecuted = "";

      try {
        if (lower.includes("track")) {
          toolExecuted = `GET /orders/${parsedId}/tracking`;
          const res = await fetch(`${API_BASE}/orders/${parsedId}/tracking`);
          const body = await res.json();
          if (res.ok && body.success) {
            const data = body.data;
            agentReply = `📦 Order #${data.order_id} is currently ${data.status.toUpperCase()}. Carrier: ${data.carrier} (${data.tracking_number}). Expected Delivery: ${new Date(data.expected_delivery).toLocaleDateString()}.`;
          } else {
            const err = body.detail || body;
            agentReply = `❌ Unable to track order #${parsedId}: ${err.reason || 'Order not found'}`;
          }
        } else if (lower.includes("refund")) {
          toolExecuted = `POST /orders/${parsedId}/refund`;
          const res = await fetch(`${API_BASE}/orders/${parsedId}/refund`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: "Customer requested refund via web portal chat" })
          });
          const body = await res.json();
          if (res.ok && body.success) {
            agentReply = `✅ Refund of $${body.data.amount} for Order #${parsedId} has been APPROVED. Refund ID: #${body.data.id}.`;
          } else {
            const err = body.detail || body;
            agentReply = `⛔ Refund Rejected for Order #${parsedId}: ${err.reason || 'Ineligible for refund'}`;
          }
        } else if (lower.includes("cancel")) {
          toolExecuted = `POST /orders/${parsedId}/cancel`;
          const res = await fetch(`${API_BASE}/orders/${parsedId}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: "Customer requested cancellation" })
          });
          const body = await res.json();
          if (res.ok && body.success) {
            agentReply = `✅ Order #${parsedId} has been successfully CANCELLED. Status updated to cancelled.`;
          } else {
            const err = body.detail || body;
            agentReply = `⛔ Cancellation Rejected for Order #${parsedId}: ${err.reason || 'Cannot cancel order'}`;
          }
        } else if (lower.includes("customer") && lower.includes("order")) {
          toolExecuted = `GET /customers/${parsedId}/orders`;
          const res = await fetch(`${API_BASE}/customers/${parsedId}/orders`);
          const body = await res.json();
          if (res.ok && body.success) {
            agentReply = `📋 Customer #${parsedId} has ${body.data.length} orders on file. Recent order statuses: ${body.data.slice(0, 3).map((o: { id: number; status: string }) => `#${o.id} (${o.status})`).join(', ')}.`;
          } else {
            const err = body.detail || body;
            agentReply = `❌ Failed to fetch orders for customer #${parsedId}: ${err.reason || 'Not found'}`;
          }
        } else if (lower.includes("customer")) {
          toolExecuted = `GET /customers/${parsedId}`;
          const res = await fetch(`${API_BASE}/customers/${parsedId}`);
          const body = await res.json();
          if (res.ok && body.success) {
            agentReply = `👤 Customer Found: ${body.data.name} (${body.data.email}). Account active since ${new Date(body.data.created_at).toLocaleDateString()}.`;
          } else {
            const err = body.detail || body;
            agentReply = `❌ Customer #${parsedId} not found: ${err.reason || 'Invalid ID'}`;
          }
        } else {
          agentReply = getFallbackResponse(userText);
        }
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        agentReply = `⚠️ Backend REST API connection error. Please ensure FastAPI server is running. (${errMsg})`;
      }

      if (toolExecuted) {
        addThought('action', `Tool Invocation [${toolExecuted}] completed. Result payload processed.`);
      } else {
        addThought('action', `Dispatched conversational response.`);
      }

      const agentMsg: Message = {
        id: generateMessageId(),
        sender: 'agent',
        text: agentReply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, agentMsg]);
    }, 600);
  };

  const getFallbackResponse = (input: string) => {
    const query = input.toLowerCase();
    if (query.includes('hello') || query.includes('hi')) {
      return "Hi there! How can I assist you with your customer support inquiries today?";
    }
    return "Understood. You can test live REST API tools by typing commands like 'track 1', 'refund 1', 'cancel 1', or 'customer 1'.";
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startCall = () => {
    setCallDuration(0);
    setIsCalling(true);
    addThought('perception', 'Incoming audio stream connected via WebRTC.');
    addThought('reasoning', 'Analyzing tone of voice and query intent... System status check: normal.');
    addThought('action', 'Synthesized audio greeting response.');
  };

  const endCall = () => {
    setIsCalling(false);
    setCallDuration(0);
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
            {backendStatus === 'online' && <span className="text-emerald-400 font-semibold">Online (REST Tools Connected)</span>}
            {backendStatus === 'offline' && <span className="text-rose-400 font-semibold">Offline (Run uvicorn)</span>}
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
              placeholder="Type a query (e.g. 'track 1', 'refund 1', 'cancel 1', 'customer 1')..."
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
                  onClick={endCall}
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
                  onClick={startCall}
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
                    <span className="text-[10px] text-slate-500">{thought.timestamp}</span>
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
