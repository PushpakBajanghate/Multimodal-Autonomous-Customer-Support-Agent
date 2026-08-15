'use client';

import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  isError?: boolean;
}

interface NetworkLog {
  id: string;
  method: string;
  endpoint: string;
  statusCode: number;
  statusText: string;
  payloadSummary: string;
  timestamp: string;
}

let messageCounter = 1;
let logCounter = 1;

const generateId = (prefix: string) => {
  if (prefix === 'msg') {
    messageCounter += 1;
    return `msg-${messageCounter}`;
  }
  logCounter += 1;
  return `log-${logCounter}`;
};

const API_BASE = 'http://localhost:8000/api/v1';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      sender: 'agent',
      text: 'Hello! Welcome to the Customer Support Portal (Phase 2). You can ask to track orders, request refunds or cancellations, or view customer order history.',
      timestamp: '12:00 PM'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [pendingIntent, setPendingIntent] = useState<'track' | 'refund' | 'cancel' | 'customer_orders' | 'customer_info' | null>(null);
  const [networkLogs, setNetworkLogs] = useState<NetworkLog[]>([]);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  const chatEndRef = useRef<HTMLDivElement>(null);

  const addNetworkLog = (
    method: string,
    endpoint: string,
    statusCode: number,
    statusText: string,
    payloadSummary: string
  ) => {
    const log: NetworkLog = {
      id: generateId('log'),
      method,
      endpoint,
      statusCode,
      statusText,
      payloadSummary,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
    setNetworkLogs(prev => [log, ...prev]);
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check backend health on mount
  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => {
        if (res.ok) {
          setBackendStatus('online');
          addNetworkLog('GET', '/health', 200, 'OK', 'Backend health check verified');
        } else {
          setBackendStatus('offline');
          addNetworkLog('GET', '/health', res.status, 'Error', 'Backend health check failed');
        }
      })
      .catch(() => {
        setBackendStatus('offline');
        addNetworkLog('GET', '/health', 0, 'Connection Refused', 'Could not reach backend on http://localhost:8000');
      });
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userText = inputText.trim();
    const userMsg: Message = {
      id: generateId('msg'),
      sender: 'user',
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');

    // Natural query extraction
    const lower = userText.toLowerCase();
    const numbers = userText.match(/\d+/g);
    const extractedId = numbers ? parseInt(numbers[0], 10) : null;

    // Detect intent
    let intent: 'track' | 'refund' | 'cancel' | 'customer_orders' | 'customer_info' | 'unknown' = 'unknown';

    if (lower.includes('track') || lower.includes('status') || lower.includes('where is')) {
      intent = 'track';
    } else if (lower.includes('refund') || lower.includes('return') || lower.includes('money back')) {
      intent = 'refund';
    } else if (lower.includes('cancel')) {
      intent = 'cancel';
    } else if (lower.includes('order') && (lower.includes('list') || lower.includes('history') || lower.includes('my orders') || lower.includes('all'))) {
      intent = 'customer_orders';
    } else if (lower.includes('customer') || lower.includes('account') || lower.includes('profile') || lower.includes('user')) {
      intent = 'customer_info';
    } else if (pendingIntent && extractedId) {
      intent = pendingIntent;
    }

    // Process actions based on intent and extracted parameters
    if (intent === 'track') {
      if (!extractedId) {
        setPendingIntent('track');
        replyAgent('Could you please provide the Order ID you would like to track? (e.g. Order #1)');
        return;
      }
      setPendingIntent(null);
      await executeTrackOrder(extractedId);
    } else if (intent === 'refund') {
      if (!extractedId) {
        setPendingIntent('refund');
        replyAgent('Please provide the Order ID you wish to request a refund for.');
        return;
      }
      setPendingIntent(null);
      await executeRefundOrder(extractedId, userText);
    } else if (intent === 'cancel') {
      if (!extractedId) {
        setPendingIntent('cancel');
        replyAgent('Please provide the Order ID you would like to cancel.');
        return;
      }
      setPendingIntent(null);
      await executeCancelOrder(extractedId, userText);
    } else if (intent === 'customer_orders') {
      const customerId = extractedId || 1; // Default to Customer 1 for quick demo if not specified
      await executeFetchCustomerOrders(customerId);
    } else if (intent === 'customer_info') {
      const customerId = extractedId || 1;
      await executeFetchCustomerInfo(customerId);
    } else {
      if (lower.includes('hello') || lower.includes('hi')) {
        replyAgent('Hello! How can I assist you with your orders, tracking, refunds, or account today?');
      } else {
        replyAgent("I didn't recognize that request. You can ask to track an order (e.g. 'track order 5'), request a refund (e.g. 'refund order 2'), cancel an order (e.g. 'cancel order 1'), or check customer history (e.g. 'show orders for customer 1').");
      }
    }
  };

  const replyAgent = (text: string, isError = false) => {
    const agentMsg: Message = {
      id: generateId('msg'),
      sender: 'agent',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isError
    };
    setMessages(prev => [...prev, agentMsg]);
  };

  const executeTrackOrder = async (orderId: number) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/tracking`);
      const body = await res.json();
      addNetworkLog('GET', `/orders/${orderId}/tracking`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const d = body.data;
        replyAgent(`📦 Order #${d.order_id} Tracking Details:\n• Status: ${d.status.toUpperCase()}\n• Carrier: ${d.carrier} (Tracking #${d.tracking_number})\n• Expected Delivery: ${new Date(d.expected_delivery).toLocaleDateString()}\n• Estimated Days Remaining: ${d.estimated_days_remaining} day(s)`);
      } else {
        const reason = body.reason || 'Order not found';
        replyAgent(`❌ Tracking Failed: ${reason}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/orders/${orderId}/tracking`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  const executeRefundOrder = async (orderId: number, originalQuery: string) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/refund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: originalQuery })
      });
      const body = await res.json();
      addNetworkLog('POST', `/orders/${orderId}/refund`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`✅ Refund Approved for Order #${orderId} in the amount of $${body.data.amount.toFixed(2)}. (Refund ID #${body.data.id})`);
      } else {
        replyAgent(`⛔ Refund Rejected: ${body.reason || 'Order is ineligible for a refund'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/orders/${orderId}/refund`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  const executeCancelOrder = async (orderId: number, originalQuery: string) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: originalQuery })
      });
      const body = await res.json();
      addNetworkLog('POST', `/orders/${orderId}/cancel`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`✅ Order #${orderId} has been successfully CANCELLED.`);
      } else {
        replyAgent(`⛔ Cancellation Rejected: ${body.reason || 'Order cannot be cancelled'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/orders/${orderId}/cancel`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  const executeFetchCustomerOrders = async (customerId: number) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}/orders`);
      const body = await res.json();
      addNetworkLog('GET', `/customers/${customerId}/orders`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const orders = body.data;
        if (orders.length === 0) {
          replyAgent(`Customer #${customerId} has no orders.`);
          return;
        }
        const orderSummaries = orders.map((o: { id: number; status: string; total_amount: number; is_editable: boolean }) => 
          `• Order #${o.id}: ${o.status.toUpperCase()} ($${o.total_amount.toFixed(2)}) - ${o.is_editable ? 'Editable' : 'Locked'}`
        ).join('\n');
        replyAgent(`📋 Customer #${customerId} has ${orders.length} order(s):\n${orderSummaries}`);
      } else {
        replyAgent(`❌ Could not fetch orders for Customer #${customerId}: ${body.reason || 'Customer not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/customers/${customerId}/orders`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  const executeFetchCustomerInfo = async (customerId: number) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}`);
      const body = await res.json();
      addNetworkLog('GET', `/customers/${customerId}`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const c = body.data;
        replyAgent(`👤 Customer Profile:\n• ID: #${c.id}\n• Name: ${c.name}\n• Email: ${c.email}\n• Created: ${new Date(c.created_at).toLocaleDateString()}`);
      } else {
        replyAgent(`❌ Customer #${customerId} lookup failed: ${body.reason || 'Customer not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/customers/${customerId}`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Top Banner */}
      <header className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 rounded-full bg-blue-500" />
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">Customer Support Agent</h1>
            <p className="text-xs text-slate-400">Phase 2: Core REST Business APIs & Service Layer</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full">
            <span className="text-slate-400">Backend API:</span>
            {backendStatus === 'checking' && <span className="text-amber-400 animate-pulse">Checking...</span>}
            {backendStatus === 'online' && <span className="text-emerald-400 font-semibold">Online (127.0.0.1:8000)</span>}
            {backendStatus === 'offline' && <span className="text-rose-400 font-semibold">Offline</span>}
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Real REST Customer Chat (7 cols) */}
        <section className="lg:col-span-7 flex flex-col bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl h-[680px]">
          <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-200">Customer Support Portal</h2>
            <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded">Text Channel</span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col max-w-[85%] ${
                  msg.sender === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'
                }`}
              >
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line shadow-sm ${
                    msg.sender === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : msg.isError
                      ? 'bg-rose-950/80 border border-rose-900/50 text-rose-200 rounded-bl-none'
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

          {/* Form */}
          <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-800 bg-slate-900/50 flex gap-3">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask about orders, tracking, refunds, or cancellations..."
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

        {/* Right Column: Real Network Inspector & Disabled Voice Channel (5 cols) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          {/* Phase 6 Voice Channel Panel (Explicitly labeled as Not Implemented) */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-5 shadow-2xl flex flex-col relative opacity-85">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-slate-300 text-sm">VoIP / Phone Support Channel</h3>
              <span className="text-[10px] uppercase font-bold text-amber-400 bg-amber-950/80 border border-amber-900/60 px-2 py-0.5 rounded">
                Phase 6: Not Yet Implemented
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Real-time SIP / VoIP phone agent with TTS and STT audio streaming will be implemented in Phase 6. No fake phone simulation is enabled.
            </p>
            <button
              disabled
              className="bg-slate-800 text-slate-500 cursor-not-allowed px-4 py-2 rounded-lg text-xs font-semibold self-start"
            >
              Voice Channel Inactive
            </button>
          </div>

          {/* Real Backend REST API Network Inspector */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl flex-1 flex flex-col min-h-[360px]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
              <div>
                <h3 className="font-semibold text-slate-200 text-sm">REST API Network Inspector</h3>
                <p className="text-[11px] text-slate-400">Live HTTP requests dispatched to FastAPI backend</p>
              </div>
              <span className="text-[10px] text-emerald-400 bg-emerald-950 border border-emerald-900 px-2 py-0.5 rounded">
                Live Telemetry
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-xs max-h-[300px] pr-1">
              {networkLogs.length === 0 ? (
                <div className="text-slate-500 text-center py-8 text-xs italic">
                  No API requests sent yet. Type a query in the chat to see real live HTTP telemetry.
                </div>
              ) : (
                networkLogs.map((log) => (
                  <div key={log.id} className="bg-slate-900/80 border border-slate-800/80 rounded p-2.5 text-[11px]">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold px-1.5 py-0.2 rounded text-[10px] ${
                          log.method === 'POST' ? 'bg-blue-950 text-blue-400 border border-blue-900' : 'bg-emerald-950 text-emerald-400 border border-emerald-900'
                        }`}>
                          {log.method}
                        </span>
                        <span className="text-slate-300 font-semibold">{log.endpoint}</span>
                      </div>
                      <span className={`text-[10px] font-bold ${
                        log.statusCode >= 200 && log.statusCode < 300
                          ? 'text-emerald-400'
                          : log.statusCode === 409
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}>
                        {log.statusCode} {log.statusText}
                      </span>
                    </div>
                    <p className="text-slate-400 text-[10px] truncate max-w-[320px]">{log.payloadSummary}</p>
                    <span className="text-[9px] text-slate-600 block mt-1">{log.timestamp}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-3 mt-auto text-center text-xs text-slate-500">
        Phase 2 Verification Portal — All chat interactions are backed by live PostgreSQL & FastAPI endpoints.
      </footer>
    </div>
  );
}
