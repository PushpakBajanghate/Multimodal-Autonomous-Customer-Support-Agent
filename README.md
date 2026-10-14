# Multimodal Autonomous Customer Support Agent

A state-of-the-art multimodal autonomous customer support platform with real-time reasoning and thought transparency. The system features a unified AI agent brain, **Aura**, delivering seamless omnichannel customer service across live text chat and voice interfaces, backed by strict Role-Based Access Control (RBAC), lightweight customer session lookups, and internal staff escalation management.

---

## 🚀 Local Endpoints

| Service | URL | Description |
| :--- | :--- | :--- |
| Frontend Web App | [http://localhost:3000](http://localhost:3000) | Next.js chat UI, after `make frontend` or `make dev` |
| FastAPI Backend | [http://localhost:8000](http://localhost:8000) | REST service, after `make backend` or `make dev` |
| API Docs | [http://localhost:8000/docs](http://localhost:8000/docs) | Available while the backend is running |
| Health Check | [http://localhost:8000/health](http://localhost:8000/health) | Available while the backend is running |

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
        LocalSQLite[(SQLite: backend/macs.db)]
        PostgreSQL[(PostgreSQL via Docker Compose)]
    end

    CustomerChat --> BearerAuth
    CustomerVoice --> ServiceAuth
    StaffDashboard --> BearerAuth

    BearerAuth --> VerificationGate
    ServiceAuth --> VerificationGate

    VerificationGate --> ServiceLayer

    ServiceLayer --> LocalSQLite
    ServiceLayer --> PostgreSQL
```

Local development uses SQLite by default. If `DATABASE_URL` is set, it takes precedence; Docker Compose sets it to the Postgres service. Redis is present in the compose file for planned infrastructure work and is not currently used by the application.

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

### One-command development

```bash
make setup
make dev
```

`make dev` runs the backend and frontend together. To run them separately, use `make backend` and `make frontend`.

On Windows PowerShell, use the equivalent commands:

```powershell
python -m pip install -r backend\requirements.txt
npm --prefix frontend install
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload'
npm --prefix frontend run dev
```

For deterministic local chat testing, set `LLM_PROVIDER=mock` in `.env`.

### Manual startup

#### 1. Start the FastAPI backend
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Start the Next.js frontend
```bash
npm --prefix frontend run dev
```

#### 3. Run the automated test suite
```bash
LLM_PROVIDER=mock python -m pytest backend/tests -q
```

---

## 🧪 Test Verification

The suite currently contains 78 tests. Run the command above to verify the current pass count; mock mode keeps tests independent of external LLM credentials.

## Roadmap

Redis-backed sessions/pub-sub and browser automation coverage (for example, Playwright) are planned but are not implemented in this baseline.
