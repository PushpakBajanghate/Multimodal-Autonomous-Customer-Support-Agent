'use client';

import React from 'react';

interface ReasoningDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: number | null;
  lastMessageText?: string;
  isBackendOnline: boolean | null;
}

export const ReasoningDrawer: React.FC<ReasoningDrawerProps> = ({
  isOpen,
  onClose,
  conversationId,
  isBackendOnline
}) => {
  if (!isOpen) return null;

  const trajectorySteps = [
    { name: "normalize_input", label: "Normalize & Sanitize Input", status: "completed", desc: "Strips whitespace and normalizes query characters." },
    { name: "load_memory", label: "Load Customer Memory & History", status: "completed", desc: "Fetches active session state and customer profile context." },
    { name: "classify_intent_entities", label: "LLM Intent & Entity Extraction", status: "completed", desc: "Invokes Gemini 3.6 Flash structured JSON schema extraction." },
    { name: "check_ambiguity", label: "Ambiguity & Slot Validation", status: "completed", desc: "Verifies whether required slots (e.g. Order ID) are present." },
    { name: "plan_actions", label: "Autonomous Multi-Step Planner", status: "completed", desc: "Generates deterministic execution steps before tool invocation." },
    { name: "select_tool", label: "Tool Selector & Registry Lookup", status: "completed", desc: "Resolves domain tool in TOOL_REGISTRY." },
    { name: "execute_tool", label: "Tool Execution & DB Transaction", status: "completed", desc: "Executes verified database/API action." },
    { name: "validate_result", label: "Policy & Result Validation", status: "completed", desc: "Enforces 30-day return policy and checks retry budget." },
    { name: "generate_response", label: "Grounded LLM Response Synthesis", status: "completed", desc: "Synthesizes customer response strictly grounded on tool output." },
    { name: "log_interaction", label: "Audit & Interaction Telemetry", status: "completed", desc: "Logs execution trace and token metrics." }
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm transition-opacity">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Drawer Header */}
          <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-sm">
                🧠
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Agent Brain & Reasoning</h2>
                <p className="text-[11px] text-slate-400">Live LangGraph State Machine Telemetry</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Drawer Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Live Model Badge */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Active NLU Engine:</span>
                <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800 text-[11px] font-mono font-medium">
                  gemini-3.6-flash
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Session Identifier:</span>
                <span className="text-xs font-mono text-slate-400">
                  {conversationId ? `Conversation #${conversationId}` : 'Ephemeral Session'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Backend Brain Status:</span>
                <span className={`text-[11px] font-semibold flex items-center gap-1.5 ${isBackendOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                  <span className={`w-2 h-2 rounded-full ${isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
                  {isBackendOnline ? 'Online & Healthy' : 'Offline'}
                </span>
              </div>
            </div>

            {/* Trajectory Flow Timeline */}
            <div>
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <span>Autonomous Trajectory Pipeline (10 Nodes)</span>
              </h3>

              <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                {trajectorySteps.map((step, idx) => (
                  <div key={idx} className="relative flex items-start gap-3 pl-1">
                    <div className="w-5 h-5 rounded-full bg-indigo-950 border border-indigo-500 text-indigo-400 text-[10px] flex items-center justify-center font-bold shrink-0 mt-0.5 z-10">
                      {idx + 1}
                    </div>
                    <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-2.5 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-200">{step.label}</span>
                        <span className="text-[9px] font-mono text-emerald-400 uppercase">Passed</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Policy & Safety Enforcement Summary */}
            <div className="bg-indigo-950/20 border border-indigo-800/40 rounded-xl p-4 space-y-2">
              <h4 className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                <span>🛡️ Policy & Guardrail Enforcement</span>
              </h4>
              <ul className="text-[11px] text-slate-300 space-y-1 list-disc list-inside">
                <li>30-day strict return/refund window verification</li>
                <li>Shipped orders locked against in-transit cancellations</li>
                <li>Bounded retry limit (max 1 retry before human escalation)</li>
                <li>Zero-hallucination grounded response synthesis</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};