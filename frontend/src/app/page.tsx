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

interface CustomerSession {
  customerId: number;
  email?: string;
  isVerified: boolean;
  token: string;
}

interface StaffSession {
  username: string;
  role: string;
  token: string;
  name: string;
}

interface Ticket {
  id: number;
  customer_id: number;
  channel: string;
  intent: string;
  escalation_reason: string;
  status: string;
  created_at: string;
}

interface AnalyticsData {
  staff_viewer: string;
  role: string;
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  total_orders: number;
  total_refunds: number;
  total_customers: number;
  intent_breakdown: Record<string, number>;
  escalation_rate_pct: number;
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
  // Navigation & Role View State
  const [activeTab, setActiveTab] = useState<'customer' | 'staff'>('customer');
  
  // Customer Session State
  const [customerSession, setCustomerSession] = useState<CustomerSession | null>(null);
  const [sessionInputEmail, setSessionInputEmail] = useState('john.doe@example.com');
  const [sessionInputOrderId, setSessionInputOrderId] = useState('');
  
  // Staff Auth State
  const [staffSession, setStaffSession] = useState<StaffSession | null>(null);
  const [staffUsername, setStaffUsername] = useState('agent_sarah');
  const [staffPassword, setStaffPassword] = useState('password123');
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLoadingStaffData, setIsLoadingStaffData] = useState(false);

  // Chat State
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      sender: 'agent',
      text: 'Hello! I am Aura, your autonomous customer support agent. I can help track your shipments, process returns, handle order cancellations, or assist with address updates.',
      timestamp: '12:00 PM'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [pendingIntent, setPendingIntent] = useState<'track' | 'refund' | 'cancel' | 'address' | 'password_reset' | 'customer_orders' | null>(null);
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

  // Initial Health Check & Initial Customer Session Creation
  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(res => {
        if (res.ok) {
          setBackendStatus('online');
          addNetworkLog('GET', '/health', 200, 'OK', 'Backend health verified (FastAPI)');
          // Initialize a lightweight session for demo customer
          initDefaultSession();
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

  const initDefaultSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/customer-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'john.doe@example.com' })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setCustomerSession({
          customerId: data.data.customer_id,
          email: data.data.email,
          isVerified: data.data.is_verified,
          token: data.data.access_token
        });
        addNetworkLog('POST', '/auth/customer-session', res.status, 'OK', `Initialized Session for Customer #${data.data.customer_id} (Verified: ${data.data.is_verified})`);
      }
    } catch {
      // Fallback
    }
  };

  const handleCreateCustomerSession = async (verifyWithOrder: boolean) => {
    try {
      const payload: Record<string, unknown> = { email: sessionInputEmail };
      if (verifyWithOrder && sessionInputOrderId) {
        payload.order_id = parseInt(sessionInputOrderId, 10);
      }
      const res = await fetch(`${API_BASE}/auth/customer-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const body = await res.json();
      addNetworkLog('POST', '/auth/customer-session', res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        setCustomerSession({
          customerId: body.data.customer_id,
          email: body.data.email,
          isVerified: body.data.is_verified,
          token: body.data.access_token
        });
        replyAgent(`🔑 Session Active: Logged in as Customer #${body.data.customer_id} (${body.data.email}). Status: ${body.data.is_verified ? '🛡️ VERIFIED (Full Access)' : '⚠️ UNVERIFIED (Read-Only Lookups)'}`);
      } else {
        replyAgent(`❌ Customer lookup failed: ${body.reason || 'Not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', '/auth/customer-session', 0, 'Network Error', msg);
    }
  };

  const handleVerifySession = async () => {
    if (!customerSession) return;
    try {
      const payload: Record<string, unknown> = {};
      if (sessionInputOrderId) {
        payload.order_id = parseInt(sessionInputOrderId, 10);
      } else {
        payload.verification_code = '123456';
      }

      const res = await fetch(`${API_BASE}/auth/customer-session/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${customerSession.token}`
        },
        body: JSON.stringify(payload)
      });
      const body = await res.json();
      addNetworkLog('POST', '/auth/customer-session/verify', res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        setCustomerSession(prev => prev ? {
          ...prev,
          isVerified: true,
          token: body.data.access_token
        } : null);
        replyAgent(`✅ Identity Successfully Verified! You can now perform sensitive operations (refunds, cancellations, address changes).`);
      } else {
        replyAgent(`⛔ Verification Failed: ${body.reason || 'Invalid order ID or code'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', '/auth/customer-session/verify', 0, 'Network Error', msg);
    }
  };

  const handleStaffLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsLoadingStaffData(true);
      const res = await fetch(`${API_BASE}/auth/staff-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: staffUsername, password: staffPassword })
      });
      const body = await res.json();
      addNetworkLog('POST', '/auth/staff-login', res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const staff = {
          username: body.data.username,
          role: body.data.staff_role,
          token: body.data.access_token,
          name: body.data.name || body.data.username
        };
        setStaffSession(staff);
        await loadStaffDashboard(staff.token);
      } else {
        alert(`Staff login failed: ${body.reason || 'Invalid credentials'}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', '/auth/staff-login', 0, 'Network Error', msg);
    } finally {
      setIsLoadingStaffData(false);
    }
  };

  const loadStaffDashboard = async (token: string) => {
    try {
      // 1. Fetch Tickets
      const ticketRes = await fetch(`${API_BASE}/tickets`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const ticketData = await ticketRes.json();
      addNetworkLog('GET', '/tickets', ticketRes.status, ticketRes.statusText, JSON.stringify(ticketData));
      if (ticketRes.ok && ticketData.success) {
        setTickets(ticketData.data);
      }

      // 2. Fetch Analytics
      const analyticsRes = await fetch(`${API_BASE}/analytics/dashboard`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const analyticsData = await analyticsRes.json();
      addNetworkLog('GET', '/analytics/dashboard', analyticsRes.status, analyticsRes.statusText, JSON.stringify(analyticsData));
      if (analyticsRes.ok && analyticsData.success) {
        setAnalytics(analyticsData.data);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', '/analytics/dashboard', 0, 'Network Error', msg);
    }
  };

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

    const lower = userText.toLowerCase();
    const numbers = userText.match(/\d+/g);
    const extractedId = numbers ? parseInt(numbers[0], 10) : null;

    let intent: 'track' | 'refund' | 'cancel' | 'address' | 'password_reset' | 'customer_orders' | 'customer_info' | 'unknown' = 'unknown';

    if (lower.includes('track') || lower.includes('status') || lower.includes('where is')) {
      intent = 'track';
    } else if (lower.includes('refund') || lower.includes('return') || lower.includes('money back')) {
      intent = 'refund';
    } else if (lower.includes('cancel')) {
      intent = 'cancel';
    } else if (lower.includes('address') || lower.includes('shipping location')) {
      intent = 'address';
    } else if (lower.includes('password') || lower.includes('reset pass')) {
      intent = 'password_reset';
    } else if (lower.includes('order') && (lower.includes('list') || lower.includes('history') || lower.includes('my orders') || lower.includes('all'))) {
      intent = 'customer_orders';
    } else if (lower.includes('customer') || lower.includes('account') || lower.includes('profile')) {
      intent = 'customer_info';
    } else if (pendingIntent && extractedId) {
      intent = pendingIntent;
    }

    if (intent === 'track') {
      if (!extractedId) {
        setPendingIntent('track');
        replyAgent('Please provide the Order ID you want to track (e.g. "track order 1").');
        return;
      }
      setPendingIntent(null);
      await executeTrackOrder(extractedId);
    } else if (intent === 'refund') {
      if (!extractedId) {
        setPendingIntent('refund');
        replyAgent('Please provide the Order ID you wish to request a refund for (e.g. "refund order 2").');
        return;
      }
      setPendingIntent(null);
      await executeRefundOrder(extractedId, userText);
    } else if (intent === 'cancel') {
      if (!extractedId) {
        setPendingIntent('cancel');
        replyAgent('Please provide the Order ID you would like to cancel (e.g. "cancel order 1").');
        return;
      }
      setPendingIntent(null);
      await executeCancelOrder(extractedId, userText);
    } else if (intent === 'address') {
      const custId = customerSession?.customerId || 1;
      await executeAddressChange(custId, userText);
    } else if (intent === 'password_reset') {
      const custId = customerSession?.customerId || 1;
      await executePasswordReset(custId);
    } else if (intent === 'customer_orders') {
      const customerId = extractedId || customerSession?.customerId || 1;
      await executeFetchCustomerOrders(customerId);
    } else if (intent === 'customer_info') {
      const customerId = extractedId || customerSession?.customerId || 1;
      await executeFetchCustomerInfo(customerId);
    } else {
      if (lower.includes('hello') || lower.includes('hi')) {
        replyAgent('Hello! How can I assist you with tracking, refunds, order cancellations, or address updates today?');
      } else {
        replyAgent("I can assist with: 'track order 1', 'refund order 2', 'cancel order 1', 'change address to 123 Main St', 'reset password', or 'show my orders'.");
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

  const getAuthHeader = () => {
    if (customerSession?.token) {
      return { 'Authorization': `Bearer ${customerSession.token}` };
    }
    return {};
  };

  const executeTrackOrder = async (orderId: number) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/tracking`, {
        headers: getAuthHeader()
      });
      const body = await res.json();
      addNetworkLog('GET', `/orders/${orderId}/tracking`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const d = body.data;
        replyAgent(`📦 Order #${d.order_id} Tracking Details:\n• Status: ${d.status.toUpperCase()}\n• Carrier: ${d.carrier} (Tracking #${d.tracking_number})\n• Expected Delivery: ${new Date(d.expected_delivery).toLocaleDateString()}\n• Days Remaining: ${d.estimated_days_remaining} day(s)`);
      } else {
        replyAgent(`❌ Tracking Failed: ${body.reason || 'Order not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/orders/${orderId}/tracking`, 0, 'Network Error', msg);
      replyAgent(`⚠️ Connection error contacting backend: ${msg}`, true);
    }
  };

  const executeRefundOrder = async (orderId: number, reason: string) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/refund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ reason })
      });
      const body = await res.json();
      addNetworkLog('POST', `/orders/${orderId}/refund`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`✅ Refund Approved for Order #${orderId} for $${body.data.amount.toFixed(2)}. (Refund ID #${body.data.id})`);
      } else {
        const msg = res.status === 403 && !customerSession?.isVerified
          ? `🛡️ Sensitive Action Restricted: Your session is unverified. Please verify your order number in the Session Panel to authorize refunds.`
          : `⛔ Refund Rejected: ${body.reason || 'Order is ineligible for refund'}`;
        replyAgent(msg, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/orders/${orderId}/refund`, 0, 'Network Error', msg);
    }
  };

  const executeCancelOrder = async (orderId: number, reason: string) => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ reason })
      });
      const body = await res.json();
      addNetworkLog('POST', `/orders/${orderId}/cancel`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`✅ Order #${orderId} has been successfully CANCELLED.`);
      } else {
        const msg = res.status === 403 && !customerSession?.isVerified
          ? `🛡️ Sensitive Action Restricted: Your session is unverified. Please verify your order number in the Session Panel to authorize cancellation.`
          : `⛔ Cancellation Rejected: ${body.reason || 'Order cannot be cancelled'}`;
        replyAgent(msg, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/orders/${orderId}/cancel`, 0, 'Network Error', msg);
    }
  };

  const executeAddressChange = async (customerId: number, text: string) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}/address`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({ new_address: text })
      });
      const body = await res.json();
      addNetworkLog('POST', `/customers/${customerId}/address`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`📍 Address Update Request Submitted: ${body.data.new_address} (Status: ${body.data.status})`);
      } else {
        const msg = res.status === 403 && !customerSession?.isVerified
          ? `🛡️ Sensitive Action Restricted: Address updates require a VERIFIED customer session. Please verify your identity first.`
          : `⛔ Address Update Failed: ${body.reason || 'Error'}`;
        replyAgent(msg, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/customers/${customerId}/address`, 0, 'Network Error', msg);
    }
  };

  const executePasswordReset = async (customerId: number) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}/password-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({})
      });
      const body = await res.json();
      addNetworkLog('POST', `/customers/${customerId}/password-reset`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        replyAgent(`🔐 Password Reset Initiated: A secure reset token has been generated (${body.data.token}). Status: ${body.data.status}`);
      } else {
        const msg = res.status === 403 && !customerSession?.isVerified
          ? `🛡️ Sensitive Action Restricted: Password reset requires a VERIFIED customer session.`
          : `⛔ Password Reset Failed: ${body.reason || 'Error'}`;
        replyAgent(msg, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('POST', `/customers/${customerId}/password-reset`, 0, 'Network Error', msg);
    }
  };

  const executeFetchCustomerOrders = async (customerId: number) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}/orders`, {
        headers: getAuthHeader()
      });
      const body = await res.json();
      addNetworkLog('GET', `/customers/${customerId}/orders`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const orders = body.data;
        if (orders.length === 0) {
          replyAgent(`Customer #${customerId} has no active orders.`);
          return;
        }
        const summaries = orders.map((o: { id: number; status: string; total_amount: number; is_editable: boolean }) =>
          `• Order #${o.id}: ${o.status.toUpperCase()} ($${o.total_amount.toFixed(2)}) — ${o.is_editable ? 'Editable' : 'Locked'}`
        ).join('\n');
        replyAgent(`📋 Customer #${customerId} Order History (${orders.length} orders):\n${summaries}`);
      } else {
        replyAgent(`❌ Orders lookup failed: ${body.reason || 'Customer not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/customers/${customerId}/orders`, 0, 'Network Error', msg);
    }
  };

  const executeFetchCustomerInfo = async (customerId: number) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${customerId}`, {
        headers: getAuthHeader()
      });
      const body = await res.json();
      addNetworkLog('GET', `/customers/${customerId}`, res.status, res.statusText, JSON.stringify(body));

      if (res.ok && body.success) {
        const c = body.data;
        replyAgent(`👤 Customer Profile:\n• ID: #${c.id}\n• Name: ${c.name}\n• Email: ${c.email}\n• Member Since: ${new Date(c.created_at).toLocaleDateString()}`);
      } else {
        replyAgent(`❌ Profile lookup failed: ${body.reason || 'Customer not found'}`, true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addNetworkLog('GET', `/customers/${customerId}`, 0, 'Network Error', msg);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Top Banner */}
      <header className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-3.5 w-3.5 rounded-full bg-blue-500 ring-4 ring-blue-500/20" />
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              Multimodal Autonomous Support Agent
              <span className="text-[10px] font-mono font-normal uppercase bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">
                Aura v2.0
              </span>
            </h1>
            <p className="text-xs text-slate-400">Omnichannel AI Brain • Lightweight Auth • Staff RBAC • Real-time Telemetry</p>
          </div>
        </div>
        
        {/* Navigation Switcher & Health Status */}
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-900 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setActiveTab('customer')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'customer'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              💬 Customer Portal
            </button>
            <button
              onClick={() => setActiveTab('staff')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'staff'
                  ? 'bg-purple-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🛡️ Staff Dashboard
            </button>
          </div>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
            <span className="text-slate-400">Backend API:</span>
            {backendStatus === 'checking' && <span className="text-amber-400 animate-pulse font-medium">Checking...</span>}
            {backendStatus === 'online' && <span className="text-emerald-400 font-semibold flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" /> Online</span>}
            {backendStatus === 'offline' && <span className="text-rose-400 font-semibold">Offline</span>}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'customer' ? (
          <>
            {/* Left Column: Customer Chat & Intent Execution (7 cols) */}
            <section className="lg:col-span-7 flex flex-col bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl h-[720px]">
              <div className="bg-slate-900 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  <h2 className="font-semibold text-sm text-slate-200">Aura Customer Assistant</h2>
                </div>
                
                {/* Current Customer Session Badge */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-400">Session:</span>
                  {customerSession ? (
                    <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-bold border ${
                      customerSession.isVerified
                        ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                        : 'bg-amber-950/80 text-amber-300 border-amber-800'
                    }`}>
                      Customer #{customerSession.customerId} {customerSession.isVerified ? '✓ Verified' : '⚠ Unverified'}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">No session active</span>
                  )}
                </div>
              </div>

              {/* Messages Viewport */}
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

              {/* Quick Action Chips */}
              <div className="px-4 py-2 bg-slate-900/30 border-t border-slate-800/80 flex flex-wrap gap-2 text-xs">
                <span className="text-[11px] text-slate-500 self-center mr-1">Quick Prompts:</span>
                <button
                  onClick={() => setInputText('Track my order 1')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded text-[11px] transition-colors"
                >
                  📦 Track Order #1
                </button>
                <button
                  onClick={() => setInputText('Request refund for order 2')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded text-[11px] transition-colors"
                >
                  💰 Refund Order #2
                </button>
                <button
                  onClick={() => setInputText('Cancel order 1')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded text-[11px] transition-colors"
                >
                  ❌ Cancel Order #1
                </button>
                <button
                  onClick={() => setInputText('Show all my orders')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded text-[11px] transition-colors"
                >
                  📋 List Orders
                </button>
              </div>

              {/* Chat Input Form */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-800 bg-slate-900/50 flex gap-3">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask Aura to track orders, request refunds, cancel, or update shipping..."
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

            {/* Right Column: Customer Auth Control & Live Network Telemetry (5 cols) */}
            <section className="lg:col-span-5 flex flex-col gap-6">
              {/* Lightweight Session & Auth Control Panel */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl flex flex-col">
                <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
                  <h3 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
                    🔑 Customer Session & Identity Gate
                  </h3>
                  <span className="text-[10px] text-blue-400 bg-blue-950 border border-blue-900 px-2 py-0.5 rounded">
                    Lightweight Lookup
                  </span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1">Customer Email / Identifier</label>
                    <input
                      type="email"
                      value={sessionInputEmail}
                      onChange={(e) => setSessionInputEmail(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500"
                      placeholder="e.g. john.doe@example.com"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Order ID for Verification (Optional)</label>
                    <input
                      type="number"
                      value={sessionInputOrderId}
                      onChange={(e) => setSessionInputOrderId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500"
                      placeholder="e.g. 1"
                    />
                  </div>

                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => handleCreateCustomerSession(false)}
                      className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 px-3 rounded font-medium transition-colors"
                    >
                      Start Lookup Session (Unverified)
                    </button>
                    <button
                      onClick={handleVerifySession}
                      className="flex-1 bg-emerald-700 hover:bg-emerald-600 text-white py-1.5 px-3 rounded font-medium transition-colors"
                    >
                      Verify Session
                    </button>
                  </div>

                  <div className="bg-slate-900/60 border border-slate-800/80 rounded p-2.5 text-[11px] text-slate-400 space-y-1">
                    <div className="flex justify-between">
                      <span>Status:</span>
                      <strong className={customerSession?.isVerified ? 'text-emerald-400' : 'text-amber-400'}>
                        {customerSession?.isVerified ? 'Verified (Sensitive Actions Unlocked)' : 'Unverified (Tracking & FAQs Only)'}
                      </strong>
                    </div>
                    <div className="flex justify-between">
                      <span>JWT Role:</span>
                      <span className="font-mono text-slate-300">customer</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Real Backend REST API Network Inspector */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl flex-1 flex flex-col min-h-[300px]">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-200 text-sm">REST API Network Inspector</h3>
                    <p className="text-[11px] text-slate-400">Live HTTP telemetry to FastAPI backend</p>
                  </div>
                  <span className="text-[10px] text-emerald-400 bg-emerald-950 border border-emerald-900 px-2 py-0.5 rounded">
                    Live Telemetry
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-xs max-h-[250px] pr-1">
                  {networkLogs.length === 0 ? (
                    <div className="text-slate-500 text-center py-8 text-xs italic">
                      No API calls dispatched yet.
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
                              : log.statusCode === 409 || log.statusCode === 403
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
          </>
        ) : (
          /* Staff & Analytics Dashboard (Full 12 cols) */
          <section className="lg:col-span-12 flex flex-col gap-6">
            {!staffSession ? (
              /* Staff Login View */
              <div className="max-w-md mx-auto w-full bg-slate-950 border border-slate-800 rounded-xl p-8 shadow-2xl my-12">
                <div className="text-center mb-6">
                  <div className="h-10 w-10 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-xl flex items-center justify-center mx-auto mb-3 text-lg font-bold">
                    🛡️
                  </div>
                  <h2 className="text-lg font-bold text-white">Internal Staff Portal</h2>
                  <p className="text-xs text-slate-400 mt-1">Authenticate to access tickets & escalation analytics</p>
                </div>

                <form onSubmit={handleStaffLogin} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1">Username</label>
                    <input
                      type="text"
                      value={staffUsername}
                      onChange={(e) => setStaffUsername(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2.5 text-slate-200 text-xs focus:outline-none focus:border-purple-500"
                    />
                    <span className="text-[10px] text-slate-500 mt-1 block">Default: agent_sarah (support_agent) or admin_alex (admin)</span>
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Password</label>
                    <input
                      type="password"
                      value={staffPassword}
                      onChange={(e) => setStaffPassword(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2.5 text-slate-200 text-xs focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isLoadingStaffData}
                    className="w-full bg-purple-600 hover:bg-purple-500 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm shadow-lg shadow-purple-950/50"
                  >
                    {isLoadingStaffData ? 'Authenticating...' : 'Sign In as Staff'}
                  </button>
                </form>
              </div>
            ) : (
              /* Authenticated Staff Dashboard View */
              <div className="space-y-6">
                {/* Staff Header */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-base font-bold text-white">Escalation & Analytics Dashboard</h2>
                      <span className="bg-purple-950 text-purple-300 border border-purple-800 text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold">
                        Role: {staffSession.role}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Logged in as {staffSession.name} (@{staffSession.username})</p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => loadStaffDashboard(staffSession.token)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                    >
                      🔄 Refresh Data
                    </button>
                    <button
                      onClick={() => setStaffSession(null)}
                      className="bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Logout
                    </button>
                  </div>
                </div>

                {/* Metrics Grid */}
                {analytics && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                      <span className="text-[11px] text-slate-400">Total Escalation Tickets</span>
                      <p className="text-2xl font-bold text-white mt-1">{analytics.total_tickets}</p>
                      <span className="text-[10px] text-amber-400">{analytics.open_tickets} Open / Pending</span>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                      <span className="text-[11px] text-slate-400">Total Orders Processed</span>
                      <p className="text-2xl font-bold text-white mt-1">{analytics.total_orders}</p>
                      <span className="text-[10px] text-emerald-400">{analytics.total_refunds} Refunds Issued</span>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                      <span className="text-[11px] text-slate-400">Total Customer Accounts</span>
                      <p className="text-2xl font-bold text-white mt-1">{analytics.total_customers}</p>
                      <span className="text-[10px] text-blue-400">Active Profiles</span>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                      <span className="text-[11px] text-slate-400">Escalation Rate</span>
                      <p className="text-2xl font-bold text-white mt-1">{analytics.escalation_rate_pct}%</p>
                      <span className="text-[10px] text-slate-400">Against total orders</span>
                    </div>
                  </div>
                )}

                {/* Escalation Tickets List */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl">
                  <h3 className="font-semibold text-sm text-slate-200 mb-3">Live Escalation Tickets (`GET /api/v1/tickets`)</h3>
                  {tickets.length === 0 ? (
                    <div className="text-slate-500 text-center py-6 text-xs italic">
                      No tickets found in database.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                            <th className="pb-2">ID</th>
                            <th className="pb-2">Customer</th>
                            <th className="pb-2">Channel</th>
                            <th className="pb-2">Intent</th>
                            <th className="pb-2">Reason</th>
                            <th className="pb-2">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                          {tickets.map((t) => (
                            <tr key={t.id} className="hover:bg-slate-900/50">
                              <td className="py-2.5 font-bold text-blue-400">#{t.id}</td>
                              <td className="py-2.5 text-slate-300">Cust #{t.customer_id}</td>
                              <td className="py-2.5 text-slate-400">{t.channel}</td>
                              <td className="py-2.5 text-amber-300">{t.intent}</td>
                              <td className="py-2.5 text-slate-300 max-w-xs truncate font-sans">{t.escalation_reason}</td>
                              <td className="py-2.5">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  t.status === 'open' ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                }`}>
                                  {t.status.toUpperCase()}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-3 mt-auto flex flex-wrap items-center justify-between text-xs text-slate-500">
        <span>Multimodal Autonomous Customer Support Agent • Production-Grade Auth & RBAC Enabled</span>
        <div className="flex gap-4">
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
            Swagger API Docs ↗
          </a>
          <a href="http://localhost:8000/health" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">
            API Health ↗
          </a>
        </div>
      </footer>
    </div>
  );
}
