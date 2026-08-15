# Multimodal Autonomous Customer Support Agent

[![Application Status: Running](https://img.shields.io/badge/System_Status-Running_&_Healthy-success?style=for-the-badge&logo=fastapi)](http://localhost:8000/health)
[![Frontend UI: Active](https://img.shields.io/badge/Frontend_UI-http%3A%2F%2Flocalhost%3A3000-blue?style=for-the-badge&logo=next.js)](http://localhost:3000)
[![Backend API: Active](https://img.shields.io/badge/API_Docs-http%3A%2F%2Flocalhost%3A8000%2Fdocs-teal?style=for-the-badge&logo=swagger)](http://localhost:8000/docs)

A state-of-the-art multimodal autonomous customer support platform with real-time reasoning and thought transparency. The system features a unified AI agent brain, **Aura**, delivering seamless omnichannel customer service across live text chat and voice interfaces, backed by strict Role-Based Access Control (RBAC), lightweight customer session lookups, and internal staff escalation management.

---

## 🚀 Live Working Links & Application Status

| Service | Working Local Link | Description | Status |
| :--- | :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:3000](http://localhost:3000) | Next.js interactive chat & voice simulation dashboard | 🟢 **Running** |
| **FastAPI Backend Root** | [http://localhost:8000](http://localhost:8000) | Autonomous Agent Brain REST service | 🟢 **Running** |
| **Interactive API Docs (Swagger UI)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Full interactive OpenAPI test bench | 🟢 **Live** |
| **Alternative API Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Detailed endpoint schema & payload documentation | 🟢 **Live** |
| **Backend Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Real-time backend connectivity check | 🟢 **Healthy** |
| **Staff Analytics Dashboard API** | [http://localhost:8000/api/v1/analytics/dashboard](http://localhost:8000/api/v1/analytics/dashboard) | Escalation metrics and resolution analytics | 🟢 **Protected (Staff JWT)** |

---

## 🏛 System Architecture

```mermaid
flowchart TB
    subgraph ClientLayer [Client & Channel Layer]
        CustomerChat[Customer Web Chat UI\n:3000]
        CustomerVoice[Voice Call Simulation / Gateway]
        StaffDashboard[Internal Staff Dashboard]
    end

    subgraph SecurityLayer [AuthN & AuthZ Gateway]
        BearerAuth[JWT Bearer Validation\nCustomer & Staff Tokens]
        ServiceAuth[Scoped Service Auth\nX-Agent-Service-Key]
        VerificationGate{Identity Verified\nin Session?}
    end

    subgraph ServiceLayer [FastAPI Agent Brain :8000]
        AuthRouter[/api/v1/auth]
        CustomerRouter[/api/v1/customers]
        OrderRouter[/api/v1/orders]
        TicketRouter[/api/v1/tickets]
        AnalyticsRouter[/api/v1/analytics]
    end

    subgraph PersistenceLayer [Data & Cache Infrastructure]
        PostgreSQL[(PostgreSQL Relational DB :5435)]
        Redis[(Redis Session & Pub/Sub :6379)]
    end

    CustomerChat --> BearerAuth
    CustomerVoice --> ServiceAuth
    StaffDashboard --> BearerAuth

    BearerAuth --> VerificationGate
    ServiceAuth --> VerificationGate

    VerificationGate --> ServiceLayer

    ServiceLayer --> PostgreSQL
    ServiceLayer --> Redis
```

---

## 🔐 Authentication & Authorization Model

The backend implements a dual-actor security model with role separation, lightweight lookup workflows, and scoped tool credentials:

### 1. End Customer Authentication (Chat / Voice)
- **Lightweight Lookup Flow:** Customers can initiate an inquiry (e.g., *"Where is my order?"*) without needing a pre-registered password or full account login.
- **Unverified Sessions (`is_verified: false`):** Permitted to perform general read queries (such as checking tracking status or general FAQ).
- **Session Verification (`is_verified: true`):** Elevated automatically when a customer validates an order number belonging to their account or inputs a verification code.
- **Sensitive Operations Gate:** Sensitive actions (`POST /orders/{id}/refund`, `POST /orders/{id}/cancel`, `POST /customers/{id}/address`, `POST /customers/{id}/password-reset`) strictly require `require_verified_customer` in the current session.

### 2. Internal Staff Authorization
- Dedicated staff login (`POST /api/v1/auth/staff-login`) issuing signed staff JWTs.
- Supports role enforcement:
  - `support_agent`: View and manage escalation tickets (`GET /api/v1/tickets`).
  - `admin`: Full administrative access, escalation stats, and analytics dashboard (`GET /api/v1/analytics/dashboard`).

### 3. Scoped Agent Service Credentials
- Tool executions and backend calls invoked autonomously by the agent pipeline use scoped service headers (`X-Agent-Service-Key`), preventing unauthorized direct DB access while preserving tenant isolation.

---

## 📡 API Endpoint Reference

| Method | Endpoint | Description | Auth Requirement |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/customer-session` | Create lightweight customer session | Public / Session Lookup |
| `POST` | `/api/v1/auth/customer-session/verify` | Elevate session to verified status | Customer JWT |
| `POST` | `/api/v1/auth/staff-login` | Authenticate internal support staff / admin | Staff Credentials |
| `GET` | `/api/v1/customers/{id}` | Retrieve customer profile | Customer JWT / Agent / Staff |
| `GET` | `/api/v1/customers/{id}/orders` | List customer orders | Customer JWT / Agent / Staff |
| `POST` | `/api/v1/customers/{id}/address` | Update shipping address | **Verified Customer Session** |
| `POST` | `/api/v1/customers/{id}/password-reset` | Request password reset token | **Verified Customer Session** |
| `GET` | `/api/v1/orders/{id}` | Get order details | Customer JWT / Agent / Staff |
| `GET` | `/api/v1/orders/{id}/tracking` | Real-time carrier tracking lookup | Customer JWT / Agent / Staff |
| `POST` | `/api/v1/orders/{id}/refund` | Submit refund request (30-day window) | **Verified Customer Session** |
| `POST` | `/api/v1/orders/{id}/cancel` | Cancel un-shipped order | **Verified Customer Session** |
| `POST` | `/api/v1/tickets` | Create human escalation ticket | Customer / Agent / Staff |
| `GET` | `/api/v1/tickets` | List escalation tickets | Staff JWT (`support_agent`, `admin`) |
| `GET` | `/api/v1/tickets/{id}` | Get detailed escalation ticket | Staff JWT (`support_agent`, `admin`) |
| `GET` | `/api/v1/analytics/dashboard` | Escalation metrics & resolution rates | Staff JWT (`support_agent`, `admin`) |

---

## 💻 Running the Application Locally

### 1. Start the FastAPI Backend
```powershell
# In root directory or backend directory
.\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the Next.js Frontend
```powershell
cd frontend
npm run dev
```

### 3. Run Automated Test Suite
```powershell
.\venv\Scripts\pytest backend\tests -v
```

---

## 🧪 Test Verification

All 38 automated test cases covering authentication, customer sessions, verified sensitive action requirements, staff RBAC, and agent service headers pass with 100% success rate.
