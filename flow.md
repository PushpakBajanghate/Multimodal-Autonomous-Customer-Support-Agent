# Multimodal Autonomous Customer Support Agent (Aura) — System Flow & Execution Architecture

This document provides a comprehensive end-to-end technical reference for the execution flows, state machine lifecycle, decision routing, multimodal channel interaction, and security gates of the **Aura** customer support platform.

---

## 1. High-Level System Architecture & Flow

```mermaid
flowchart TD
    User([Customer / User]) -->|HTTP / WebSocket / WebRTC| ChannelLayer[Omnichannel Layer: Web Chat UI / Voice Simulation]
    Staff([Support Agent / Admin]) -->|REST API / Bearer JWT| StaffPortal[Staff Management & Analytics Portal]

    subgraph AuthGateway [Authentication & Authorization Gateway]
        direction TB
        TokenExtractor[Extract Bearer JWT or Session Key]
        RoleVerifier{Role Verification}
        LightweightLookup[Lightweight Customer Session Lookup]
        VerifiedGate{Is Session Verified?}
    end

    ChannelLayer --> TokenExtractor
    StaffPortal --> TokenExtractor
    TokenExtractor --> RoleVerifier
    RoleVerifier -->|Customer Session| LightweightLookup
    LightweightLookup --> VerifiedGate
    RoleVerifier -->|Staff / Agent Token| AgentBrain

    VerifiedGate -->|Unverified: General Read Actions| AgentBrain[Unified Agent Brain: LangGraph StateGraph]
    VerifiedGate -->|Verified: Sensitive Actions Allowed| AgentBrain

    subgraph AgentBrainPipeline [Agent Brain Execution Pipeline]
        direction TB
        NLU[Intent Classification & Entity Extraction - Gemini/OpenAI]
        AmbiguityCheck{Is Ambiguous?}
        Clarification[Generate Clarification Prompt]
        Planner[Autonomous Action Planner]
        ToolDispatch[Domain Tool Selector & Executor]
        PolicyValidator{Policy & Output Validation}
        RetryGate{Retry Count < 1?}
        Escalation[Human Escalation & Ticket Creation]
        ResponseSynthesizer[Grounded LLM Response Synthesizer]
    end

    AgentBrain --> NLU
    NLU --> AmbiguityCheck
    AmbiguityCheck -->|Yes| Clarification --> ResponseSynthesizer
    AmbiguityCheck -->|No| Planner --> ToolDispatch --> PolicyValidator
    PolicyValidator -->|Pass| ResponseSynthesizer
    PolicyValidator -->|Fail & Retry| RetryGate
    RetryGate -->|Yes| ToolDispatch
    RetryGate -->|No| Escalation --> ResponseSynthesizer

    subgraph DataStorage [Resilient Persistence Layer]
        Postgres[(PostgreSQL Relational DB / SQLite Fallback)]
        Redis[(Redis Session & Pub/Sub Broker)]
    end

    ToolDispatch <--> Postgres
    ResponseSynthesizer --> User
```

---

## 2. Autonomous Agent Brain: LangGraph State Machine Lifecycle

The agent brain is modeled as a compiled LangGraph `StateGraph` consisting of 10 discrete nodes and deterministic conditional branching logic:

```mermaid
stateDiagram-v2
    [*] --> NormalizeInput
    NormalizeInput --> LoadMemory: Sanitized utterance & Context
    LoadMemory --> ClassifyIntentEntities: Customer history injected
    ClassifyIntentEntities --> CheckAmbiguity: Intent & entities parsed

    state CheckAmbiguity <<choice>>
    CheckAmbiguity --> ClarificationQuestion: is_ambiguous == True
    CheckAmbiguity --> PlanActions: is_ambiguous == False

    ClarificationQuestion --> LogInteraction

    PlanActions --> SelectTool: Multi-step action plan created
    SelectTool --> ExecuteTool: Tool & arguments resolved
    ExecuteTool --> ValidateResult: Tool output received

    state ValidateResult <<choice>>
    ValidateResult --> RetryTool: Failure & retry_count < 1
    ValidateResult --> Escalate: Failure & retry_count >= 1
    ValidateResult --> GenerateResponse: Success verified

    RetryTool --> ExecuteTool: Increment retry_count
    Escalate --> LogInteraction: Support ticket created
    GenerateResponse --> LogInteraction: Grounded LLM response synthesized
    LogInteraction --> [*]
```

### LangGraph State Nodes Reference

| Node Name | Purpose | Output Mutation |
| :--- | :--- | :--- |
| `normalize_input` | Strips whitespace, sanitizes control characters | `normalized_input`, `trajectory` |
| `load_memory` | Loads customer profile, order history, and active conversation state | `customer_context`, `trajectory` |
| `classify_intent_entities` | Invokes Gemini 3.6 Flash / OpenAI structured JSON extraction | `intent`, `intent_confidence`, `entities`, `is_ambiguous` |
| `check_ambiguity` | Evaluates missing critical slots (e.g., missing Order ID for refund) | `trajectory` |
| `clarification_question` | Crafts a polite question requesting specific missing parameters | `final_response`, `trajectory` |
| `plan_actions` | Builds an explicit step-by-step resolution plan | `plan`, `trajectory` |
| `select_tool` | Maps intent and parameters to domain tool (`TOOL_REGISTRY`) | `selected_tool`, `tool_args`, `trajectory` |
| `execute_tool` | Invokes domain service via isolated Phase 2 API layer | `tool_results`, `tool_status`, `trajectory` |
| `validate_result` | Verifies tool output against business policies; detects failure | `needs_retry`, `needs_escalation`, `risk_score` |
| `retry_tool` | Bounded automatic retry loop (max 1 retry) | `retry_count += 1`, `needs_retry = False` |
| `escalate` | Dispatches incident to human staff queue with automatic ticket | `final_response`, `trajectory` |
| `generate_response` | Synthesizes grounded, empathetic customer reply | `final_response`, `trajectory` |
| `log_interaction` | Records interaction logs, token usage, and trajectory metrics | `trajectory` |

---

## 3. Natural Language Understanding (NLU) Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant API as FastAPI /api/v1/chat
    participant NLU as LLM NLU Engine (llm_client.py)
    participant Gemini as Google Gemini 3.6 Flash
    participant Heuristics as Deterministic Heuristic Engine

    Customer->>API: "Where is my package for order 101?"
    API->>NLU: analyze_utterance(text, conversation_history)
    
    alt Gemini API Key Configured
        NLU->>Gemini: POST /v1beta/models/gemini-3.6-flash:generateContent (Structured JSON Schema)
        Gemini-->>NLU: 200 OK: {"intent": "ORDER_TRACKING", "entities": {"order_id": 101}, "confidence": 0.98}
    else Gemini Network / Rate Limit Timeout
        NLU->>Heuristics: analyze_utterance_rule_based(text, context)
        Heuristics-->>NLU: Fallback Extraction: IntentType.ORDER_TRACKING, order_id=101
    end

    NLU-->>API: Validated AnalysisResult Schema
```

---

## 4. Authentication & Authorization Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Frontend as Next.js Web Chat
    participant Auth as Auth Gateway (/api/v1/auth)
    participant DB as PostgreSQL / SQLite
    participant Agent as Agent Execution Gate

    Note over Customer,Auth: 1. Lightweight Anonymous Lookup
    Customer->>Frontend: Opens Chat Interface
    Frontend->>Auth: POST /customer-session (No credentials required)
    Auth-->>Frontend: Returns JWT (role: customer, is_verified: false)

    Customer->>Frontend: "Can you track order #101?"
    Frontend->>Agent: POST /chat (Bearer Token: is_verified=false)
    Agent-->>Frontend: 200 OK: Order #101 Tracking Info (Read-Only Allowed)

    Note over Customer,Auth: 2. Identity Verification Elevation
    Customer->>Frontend: "I want to refund order #101"
    Frontend->>Auth: POST /customer-session/verify (order_id=101, email="alice@example.com")
    Auth->>DB: Validate order ownership matching email
    DB-->>Auth: Verified Match
    Auth-->>Frontend: New Elevated JWT (is_verified: true)

    Note over Customer,Agent: 3. Sensitive Operation Execution
    Frontend->>Agent: POST /orders/101/refund (Bearer Token: is_verified=true)
    Agent->>DB: Process Refund Transaction ($129.99)
    DB-->>Agent: Refund Processed
    Agent-->>Frontend: 200 OK: Refund Approved and Credited
```

---

## 5. Bounded Retry & Human Escalation Matrix

```mermaid
flowchart TD
    ToolCall[Execute Domain Tool] --> ResultCheck{Result Status}
    ResultCheck -->|Success| FormatResponse[Synthesize Grounded Customer Response]
    ResultCheck -->|Failure: Policy / Network / Data| RetryCheck{Retry Count < 1?}
    
    RetryCheck -->|Yes: First Failure| RetryTool[Increment Retry Count -> Re-invoke Tool]
    RetryTool --> ToolCall
    
    RetryCheck -->|No: Repeated Failure| CreateTicket[Invoke create_ticket Tool]
    CreateTicket --> PersistTicket[(Postgres: tickets table)]
    PersistTicket --> NotifyCustomer["Notify Customer: Escalated to Senior Support Specialist"]
    NotifyCustomer --> StaffQueue[Internal Staff Dashboard /api/v1/tickets]
```

---

## 6. Omnichannel Architecture (Web Chat & Voice Simulation)

```mermaid
flowchart LR
    subgraph Channels [Omnichannel Ingestion]
        WebChat[Next.js Web Chat UI]
        VoiceSim[Voice Audio Stream / Simulated WebRTC]
    end

    subgraph AudioProcessing [Speech Processing Pipeline]
        STT[Speech-to-Text: Whisper / Gemini Audio API]
        TTS[Text-to-Speech: ElevenLabs / Web Speech Synthesis]
    end

    VoiceSim --> STT --> CoreAPI
    WebChat --> CoreAPI[FastAPI Agent Ingestion Gateway]
    CoreAPI --> StateGraph[LangGraph State Machine Engine]
    StateGraph --> GroundedGen[Grounded LLM Generator]
    GroundedGen --> WebChat
    GroundedGen --> TTS --> VoiceSim