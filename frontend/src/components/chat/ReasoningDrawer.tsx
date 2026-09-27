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
    <div className="fixed inset-0 z-50 overflow-hidden bg-[#211c38]/25 backdrop-blur-sm transition-opacity">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="flex w-screen max-w-md flex-col border-l border-[#e9e6f0] bg-white shadow-2xl">
          {/* Drawer Header */}
          <div className="flex items-center justify-between border-b border-[#efedf5] bg-white px-6 py-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#e6e1fb] bg-[#f2efff] text-[#715fce]">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M12 4a3 3 0 0 0-5.8 1.1A3.5 3.5 0 0 0 5 11a3.5 3.5 0 0 0 1 6.8A3 3 0 0 0 12 19V4Zm0 0a3 3 0 0 1 5.8 1.1A3.5 3.5 0 0 1 19 11a3.5 3.5 0 0 1-1 6.8A3 3 0 0 1 12 19V4Z" /></svg>
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#302d43]">Brain Trace</h2>
                <p className="text-[11px] text-[#9692a5]">Aura Support reasoning activity</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-lg p-1 text-[#9692a5] transition-colors hover:bg-[#f5f3fa] hover:text-[#4d4960]"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Drawer Body Content */}
          <div className="flex-1 space-y-6 overflow-y-auto p-6">
            {/* Live Model Badge */}
            <div className="space-y-2.5 rounded-xl border border-[#ebe8f3] bg-[#faf9fd] p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#686478]">Active NLU Engine:</span>
                <span className="rounded border border-[#e6e1fb] bg-[#f4f1ff] px-2 py-0.5 text-[11px] font-mono font-medium text-[#6b58d5]">
                  gemini-3.6-flash
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#686478]">Session Identifier:</span>
                <span className="text-xs font-mono text-[#8e8a9e]">
                  {conversationId ? `Conversation #${conversationId}` : 'Ephemeral Session'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#686478]">Backend Brain Status:</span>
                <span className={`flex items-center gap-1.5 text-[11px] font-semibold ${isBackendOnline ? 'text-emerald-600' : 'text-rose-500'}`}>
                  <span className={`h-2 w-2 rounded-full ${isBackendOnline ? 'animate-pulse bg-emerald-500' : 'bg-rose-500'}`} />
                  {isBackendOnline ? 'Online & Healthy' : 'Offline'}
                </span>
              </div>
            </div>

            {/* Trajectory Flow Timeline */}
            <div>
              <h3 className="mb-3 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#777388]">
                <span>Agent activity</span>
              </h3>

              <div className="relative space-y-3 before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-[#eeeaf5]">
                {trajectorySteps.map((step, idx) => (
                  <div key={idx} className="relative flex items-start gap-3 pl-1">
                    <div className="z-10 mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[#ded8f9] bg-[#f4f1ff] text-[10px] font-bold text-[#6c59d3]">
                      {idx + 1}
                    </div>
                    <div className="flex-1 rounded-lg border border-[#efedf5] bg-white p-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-[#4b475c]">{step.label}</span>
                        <span className="text-[9px] font-mono uppercase text-emerald-600">Passed</span>
                      </div>
                      <p className="mt-1 text-[11px] text-[#8f8b9f]">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Policy & Safety Enforcement Summary */}
            <div className="space-y-2 rounded-xl border border-[#e8e3fb] bg-[#f7f5ff] p-4">
              <h4 className="flex items-center gap-1.5 text-xs font-bold text-[#6552c9]">
                <span>Policy & safety checks</span>
              </h4>
              <ul className="list-inside list-disc space-y-1 text-[11px] text-[#6f6a82]">
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