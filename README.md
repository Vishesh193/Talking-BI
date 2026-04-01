# 🎙️ Talking BI — Agentic Voice-Enabled Business Intelligence

A production-ready, full-stack internal BI tool where you speak (or type) natural language questions and an AI agent pipeline automatically queries your data, picks the best visualization, and narrates insights back to you.

---

## ⚡ Quickstart (5 minutes)

### Prerequisites
- Python 3.11+
- Node.js 20+
- A Groq API key (get one free at console.groq.com)

### 1. Clone and configure

```bash
git clone <your-repo>
cd talking-bi

# Backend config
cp backend/.env.example backend/.env
# Open backend/.env and add: GROQ_API_KEY=your_key_here
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# Backend running at http://localhost:8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Frontend running at http://localhost:3000
```

### 4. Open and try it

Open http://localhost:3000. Click a starter query or say:
> *"Show total revenue by product this month"*
> *"Compare product sales this month vs last month"*
> *"What is our revenue trend this year?"*

It works immediately with **built-in demo data** — no database needed.

---

## 🏗️ Architecture

```
Browser (React)
    ↓ voice audio / text query (WebSocket)
FastAPI Backend
    ↓
LangGraph Orchestrator
    ├─ IntentAgent    → Groq LLM parses "compare sales by product MoM" → structured JSON
    ├─ SchemaAgent    → retrieves relevant DB schema / file schema
    ├─ QueryAgent     → Groq LLM generates SQL → executes on right source
    │   ├─ MySQL/Postgres (SQLAlchemy)
    │   ├─ Excel/CSV  (DuckDB)
    │   ├─ Power BI   (REST API)
    │   └─ Salesforce/Shopify (httpx)
    ├─ VizAgent       → picks best chart type → Recharts config
    ├─ InsightAgent   → Groq LLM generates ranked "so what" insights + anomaly detection
    ├─ TTSAgent       → generates spoken summary text
    └─ MemoryAgent    → saves context for follow-up queries (Redis)
    ↓ WebSocket stream
React Dashboard
    ├─ ChartRenderer  (Bar, Line, Area, Grouped Bar, Pie, KPI Card, Table)
    ├─ InsightsList   (ranked cards with confidence scores)
    └─ VoiceBar       (mic button, waveform, text input)
```

**Total voice → dashboard roundtrip: ~2–4 seconds.**

---

## 📁 Project Structure

```
talking-bi/
├── backend/
│   ├── main.py                    # FastAPI app + WebSocket endpoint
│   ├── core/
│   │   ├── config.py              # All settings (env vars)
│   │   ├── database.py            # SQLAlchemy models + async engine
│   │   └── redis_client.py        # Redis caching + session memory
│   ├── agents/
│   │   ├── orchestrator.py        # LangGraph pipeline (7 agents)
│   │   ├── intent_agent.py        # Groq: transcript → intent JSON
│   │   ├── schema_agent.py        # Schema registry + context builder
│   │   ├── query_agent.py         # NL→SQL + 4 data source connectors
│   │   ├── viz_agent.py           # Chart type selection + config builder
│   │   ├── insight_agent.py       # Groq: ranked insights + anomaly detection
│   │   ├── memory_agent.py        # Redis session context
│   │   └── tts_agent.py           # Spoken summary generator
│   ├── api/
│   │   ├── routes.py              # REST: KPIs, upload, connectors, dashboards
│   │   └── websocket_handler.py   # Real-time WS: voice, text, streaming
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Root layout
│   │   ├── stores/biStore.ts      # Zustand global state
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts    # WS connection + message routing
│   │   │   └── useVoiceRecorder.ts # MediaRecorder + VAD
│   │   ├── services/api.ts        # Axios REST client
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Header.tsx     # Status bar + controls
│   │   │   │   ├── Sidebar.tsx    # History, connectors, files, KPIs
│   │   │   │   └── SettingsPanel.tsx
│   │   │   ├── voice/
│   │   │   │   └── VoiceBar.tsx   # Mic button + waveform + text input
│   │   │   ├── dashboard/
│   │   │   │   ├── DashboardGrid.tsx
│   │   │   │   ├── DashboardPanel.tsx
│   │   │   │   ├── InsightsList.tsx
│   │   │   │   └── EmptyState.tsx
│   │   │   └── charts/
│   │   │       ├── ChartRenderer.tsx  # All Recharts chart types
│   │   │       ├── KPICard.tsx
│   │   │       └── DataTable.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔌 Connecting Your Data Sources

### SQL Database (MySQL / PostgreSQL)

```env
# backend/.env
ANALYTICS_DB_URL=mysql+aiomysql://user:password@localhost:3306/your_database
# or
ANALYTICS_DB_URL=postgresql+asyncpg://user:password@localhost:5432/your_database
```

The Schema Agent will auto-introspect your tables on startup. Add column descriptions in `agents/schema_agent.py` under `DEMO_SCHEMA` to help the NL→SQL agent understand your business terminology.

### Excel / CSV Files

Upload directly via the sidebar Files tab or drag-and-drop. Files are parsed with pandas + DuckDB, so full SQL works on them. Try:
> *"Show me revenue from the uploaded spreadsheet by region"*

### Power BI

```env
POWERBI_CLIENT_ID=your_azure_app_id
POWERBI_CLIENT_SECRET=your_azure_secret
POWERBI_TENANT_ID=your_tenant_id
```

Requires an Azure AD app registration with Power BI API permissions. The agent will generate DAX queries against your existing datasets.

### Salesforce

```env
SALESFORCE_USERNAME=your@email.com
SALESFORCE_PASSWORD=yourpassword
SALESFORCE_SECURITY_TOKEN=yourtoken
```

### Shopify

```env
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your_private_app_token
```

---

## 🗣️ Voice Commands That Work

| Command | What happens |
|---|---|
| "Show total revenue by product" | Bar chart, product breakdown |
| "Compare sales this month vs last month" | Grouped bar chart, MoM comparison |
| "What's our revenue trend this year?" | Line chart, monthly trend |
| "Top 5 customers by lifetime value" | Ranked bar chart |
| "Show that for North region only" | Follow-up — applies filter using memory |
| "Drill into Product A" | Follow-up — filters to single product |
| "Which campaigns had the best ROAS?" | Marketing analysis |
| "Is anything unusual in today's data?" | Anomaly detection |
| "Forecast revenue for next quarter" | Trend + projection |

---

## 🎛️ KPI Registry

Register business KPIs so the system knows what "churn", "ARR", "NPS" mean for your data:

```bash
# Seed built-in demo KPIs
curl -X POST http://localhost:8000/api/v1/seed-demo-kpis

# Or via the Settings → KPIs tab in the UI
```

Custom KPI via API:
```bash
curl -X POST http://localhost:8000/api/v1/kpis \
  -H "Content-Type: application/json" \
  -d '{
    "name": "monthly_recurring_revenue",
    "display_name": "MRR",
    "description": "Monthly recurring revenue from active subscriptions",
    "data_source": "sql",
    "sql_expression": "SUM(amount) WHERE subscription_status = active",
    "category": "revenue",
    "unit": "currency",
    "direction": "up_good"
  }'
```

---

## 🐳 Docker Deployment

```bash
# Create a .env file at project root with your API keys
cat > .env << EOF
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key
EOF

docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## 🔧 Without Redis / Without Real DB

Both are optional:

- **No Redis**: An in-memory dict fallback is used automatically. Session memory works within a single server process.
- **No analytics DB**: Demo data (100 orders, 5 products, 4 regions) is used automatically. Full NL→SQL + charting works.
- **No OpenAI key**: Voice recording is disabled; text queries work fully.
- **No Groq key**: The LLM agents won't function — this is the only required key.

---

## 🧠 How Follow-Up Queries Work

The Memory Agent saves context after every query. So this conversation works:

1. *"Show revenue by product"* → groups bar chart renders
2. *"Now compare that to last month"* → agent injects previous metric/dimension into new intent
3. *"Filter to just Electronics"* → applies category filter to the same query
4. *"What's unusual here?"* → insight agent runs anomaly detection on current data

Context resets when you start a new browser session or say *"start fresh"*.

---

## 📡 WebSocket Message Protocol

```typescript
// Client → Server
{ type: "text_query", query: "Show revenue by product" }
{ type: "voice_audio", audio: "<base64 webm>" }
{ type: "clarification", response: "I meant unit sales" }
{ type: "ping" }

// Server → Client
{ type: "agent_thinking", stage: "intent", message: "Analyzing..." }
{ type: "transcription", transcript: "Show revenue by product" }
{ type: "agent_result", data: { chart, insights, tts_text, sql, ... } }
{ type: "clarification_needed", question: "Did you mean revenue or units?" }
{ type: "error", message: "..." }
```

---

## 🔒 Security Notes (for production)

1. Add authentication (e.g., NextAuth, Clerk, or session-based)
2. Implement row-level security: filter queries by user's allowed regions/departments
3. Store API keys in a secret manager (AWS Secrets Manager, HashiCorp Vault)
4. Enable HTTPS + WSS (terminate at nginx or load balancer)
5. Rate-limit the `/ws` and `/api` endpoints
6. All generated SQL is validated (SELECT-only) before execution

---

## 🛠️ Extending the System

### Add a new data source connector

1. Add credentials to `core/config.py`
2. Add a `_query_yourservice()` method to `agents/query_agent.py`
3. Add routing in the `run()` method for the new `data_source` value
4. Add connector status to `api/routes.py` `/connectors` endpoint

### Add a new chart type

1. Add the type to `ChartType` enum in `models/schemas.py`
2. Add selection logic in `agents/viz_agent.py`
3. Add rendering in `frontend/src/components/charts/ChartRenderer.tsx`

### Add a new agent

1. Create `agents/your_agent.py` with an `async def run(self, ...)` method
2. Add node to the LangGraph graph in `agents/orchestrator.py`
3. Add edge connections and state fields in `BIState`

---

## 📊 REST API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/connectors` | All data source connector statuses |
| GET | `/api/v1/kpis` | List KPI registry |
| POST | `/api/v1/kpis` | Register a KPI |
| DELETE | `/api/v1/kpis/{id}` | Remove a KPI |
| POST | `/api/v1/seed-demo-kpis` | Seed 5 demo KPIs |
| POST | `/api/v1/upload` | Upload Excel/CSV |
| GET | `/api/v1/dashboards` | List saved dashboards |
| POST | `/api/v1/dashboards` | Save a dashboard |
| GET | `/api/v1/query-log` | Recent query history |
| WS | `/ws/{session_id}` | Main agent pipeline |

Full interactive docs at http://localhost:8000/docs (Swagger UI auto-generated by FastAPI).

---

Built with: FastAPI · LangGraph · Groq (Llama 3.3 70B) · OpenAI Whisper · React · Recharts · Zustand · DuckDB · SQLAlchemy
