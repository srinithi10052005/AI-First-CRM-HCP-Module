# 🏥 AI-First CRM — HCP Module

> A LangGraph-powered Customer Relationship Management system for pharmaceutical field representatives to log and manage Healthcare Professional (HCP) interactions.

---

## 📸 Screenshots

<img width="1882" height="909" alt="image" src="https://github.com/user-attachments/assets/98ed81d9-35cc-4e51-a803-49d65f002c93" />


---

## 🧠 What This Project Does

Pharmaceutical field representatives visit doctors (HCPs) daily. This CRM lets them:
- **Log visits** either by filling a form OR just typing naturally in a chat
- **AI automatically extracts** doctor name, date, topics, sentiment from plain English
- **Get AI suggestions** for follow-up actions after each visit
- **View full history** of all interactions with any doctor

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
│         React + Redux (Single HTML file, no npm)         │
│   ┌─────────────────┐     ┌──────────────────────┐      │
│   │ Structured Form │     │   AI Chat Interface  │      │
│   │ (Manual Entry)  │     │ (Natural Language)   │      │
│   └────────┬────────┘     └──────────┬───────────┘      │
└────────────┼─────────────────────────┼────────────────── ┘
             │ REST API                │ POST /agent/chat
             ▼                         ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                       │
│                   Python + Uvicorn                       │
│                                                          │
│   POST /interactions    GET /interactions                │
│   PUT /interactions/{id}  DELETE /interactions/{id}      │
│   POST /agent/chat      GET /health                      │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              LANGGRAPH REACT AGENT                       │
│                                                          │
│  Think → Pick Tool → Run Tool → Observe → Answer        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │log_interaction│  │edit_interact │  │analyze_sentim │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │suggest_follow│  │fetch_hcp_prof│                      │
│  └──────────────┘  └──────────────┘                      │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐   ┌────────────────────────────┐
│     GROQ API         │   │   PostgreSQL (Neon)         │
│   gemma2-9b-it       │   │   HCP Interactions Table   │
│  (LLM for AI tasks)  │   │   (Stores all data)        │
└─────────────────────┘   └────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Redux (CDN, no npm) |
| Styling | CSS Variables + Google Inter Font |
| Backend | Python + FastAPI |
| AI Agent | LangGraph (ReAct pattern) |
| LLM | Groq — gemma2-9b-it |
| Database | PostgreSQL (Neon cloud) |
| ORM | SQLAlchemy |

---

## 📁 Project Structure

```
crm-hcp/
├── backend/
│   ├── main.py                  # FastAPI app — all API routes
│   ├── .env                     # API keys and DB URL (not committed)
│   ├── requirements.txt         # Python dependencies
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph ReAct agent setup
│   │   └── tools.py             # All 5 LangGraph tools
│   └── models/
│       ├── __init__.py
│       ├── database.py          # SQLAlchemy DB connection
│       └── interaction.py       # HCPInteraction table model
└── frontend/
    └── index.html               # Complete React+Redux UI (no npm needed)
```

---

## 🤖 LangGraph AI Agent — 5 Tools Explained

The LangGraph agent uses the **ReAct (Reasoning + Acting)** pattern:
1. **Thinks** about what the user wants
2. **Picks** the right tool
3. **Runs** the tool
4. **Observes** the result
5. **Answers** the user

### Tool 1: `log_interaction`
**Trigger:** User describes a meeting in natural language
**What it does:**
- Sends the text to Groq LLM (gemma2-9b-it)
- LLM extracts: HCP name, date, topics, sentiment, outcomes
- Saves structured data to PostgreSQL
- Returns confirmation with interaction ID

**Example input:** *"Met Dr. Sharma today, discussed OncoBoost Phase 3, he was positive, gave 5 samples"*

### Tool 2: `edit_interaction`
**Trigger:** User says "update interaction 5" or "change sentiment for ID 3"
**What it does:**
- Finds the interaction by ID in the database
- Updates only the specified fields
- Re-generates AI summary if content changed
- Returns updated record

### Tool 3: `analyze_sentiment`
**Trigger:** User asks "how was the doctor's reaction?" or "analyze sentiment for ID 4"
**What it does:**
- Reads the interaction's topics and outcomes
- Sends to LLM for sentiment classification
- Returns: Positive / Neutral / Negative + confidence score
- Updates the sentiment field in the database

### Tool 4: `suggest_followup`
**Trigger:** User asks "what should I do next?" or "suggest follow-ups for ID 2"
**What it does:**
- Reads the interaction context (HCP, topics, sentiment)
- LLM generates 3-5 specific pharma sales follow-up actions
- Saves suggestions back to the database
- Returns prioritized action list

### Tool 5: `fetch_hcp_profile`
**Trigger:** User asks "show history for Dr. Smith" or "what's my relationship with Dr. Patel?"
**What it does:**
- Searches database by HCP name (partial match supported)
- Retrieves all past interactions
- LLM generates a relationship summary
- Returns full history + AI summary

---

## 🗄️ Database Schema

```sql
Table: hcp_interactions
┌─────────────────────┬──────────────┬──────────────────────────────┐
│ Column              │ Type         │ Description                  │
├─────────────────────┼──────────────┼──────────────────────────────┤
│ id                  │ Integer (PK) │ Auto-increment primary key   │
│ hcp_name            │ String(255)  │ Doctor's full name           │
│ hcp_specialty       │ String(255)  │ Medical specialty            │
│ interaction_type    │ String(100)  │ Meeting/Call/Email/Conf      │
│ interaction_date    │ String(50)   │ Date of interaction          │
│ interaction_time    │ String(20)   │ Time of interaction          │
│ attendees           │ Text         │ Other people present         │
│ topics_discussed    │ Text         │ What was discussed           │
│ materials_shared    │ Text         │ Brochures/PDFs given         │
│ samples_distributed │ Text         │ Drug samples given           │
│ sentiment           │ String(50)   │ AI-classified sentiment      │
│ sentiment_score     │ Float        │ Confidence 0.0 to 1.0        │
│ ai_summary          │ Text         │ LLM-generated summary        │
│ raw_chat_input      │ Text         │ Original chat message        │
│ outcomes            │ Text         │ Key results/agreements       │
│ follow_up_actions   │ Text         │ Next steps                   │
│ logged_by           │ String(255)  │ Field rep name               │
│ created_at          │ DateTime     │ Auto-set on insert           │
│ updated_at          │ DateTime     │ Auto-set on update           │
└─────────────────────┴──────────────┴──────────────────────────────┘
```

---

## ▶️ Setup & Run

### Prerequisites
- Python 3.10 or higher
- Groq API key (free at https://console.groq.com)
- PostgreSQL database (free at https://neon.tech) OR use SQLite locally

### Step 1 — Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/crm-hcp.git
cd crm-hcp
```

### Step 2 — Setup environment
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment variables
Create a `.env` file inside the `backend` folder:
```env
GROQ_API_KEY=gsk_your_api_key
DATABASE_URL=your_database_url

```

### Step 5 — Run the backend
```bash
uvicorn main:app --reload
```
Backend runs at: **http://127.0.0.1:8000**

### Step 6 — Open the frontend
Simply open `frontend/index.html` in your browser.
No npm, no build step, no Node.js required.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/agent/chat` | Chat with LangGraph agent |
| POST | `/interactions` | Create interaction (form) |
| GET | `/interactions` | List all interactions |
| GET | `/interactions/{id}` | Get single interaction |
| PUT | `/interactions/{id}` | Update interaction |
| DELETE | `/interactions/{id}` | Delete interaction |
| GET | `/interactions/hcp/{name}` | Search by HCP name |

### Interactive API Docs
Visit **http://127.0.0.1:8000/docs** for full Swagger UI

---

## 💡 Key Design Decisions

1. **Dual-mode input** — Form for structured data, chat for speed. Field reps choose based on context.
2. **LangGraph ReAct** — Agent autonomously decides which tool to use based on user intent.
3. **gemma2-9b-it on Groq** — Fast inference, free tier, specifically required for this project.
4. **No npm frontend** — React loaded via CDN makes setup instant and avoids npm dependency issues.
5. **SQLAlchemy ORM** — Database-agnostic: works with SQLite (dev) or PostgreSQL (production) by changing one env variable.

---

## 🧪 Testing the 5 Tools via Chat

Once the app is running, try these chat messages:

```
Tool 1 — Log:
"Met Dr. Patel today, discussed CardioPlus efficacy study, 
she was very positive, gave 10 samples of 5mg dose"

Tool 2 — Edit:
"Update interaction 1, change the sentiment to Positive"

Tool 3 — Sentiment:
"Analyze sentiment for interaction 1"

Tool 4 — Follow-up:
"Suggest follow-ups for interaction 1"

Tool 5 — Profile:
"Show me the history for Dr. Patel"
```

---
## 👩‍💻 Author (Srinithi)
Built a part  — AI-First CRM HCP Module
