# main.py — FastAPI application entry point
# This is the file you run: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import os

# Import our database setup
from models.database import engine, Base, get_db
from models.interaction import HCPInteraction

# Import the LangGraph agent runner
from agent.graph import run_agent

# ── Create all database tables if they don't exist ──────────────────────────
# This runs once on startup — creates the hcp_interactions table
Base.metadata.create_all(bind=engine)

# ── Create the FastAPI app instance ─────────────────────────────────────────
app = FastAPI(
    title="AI-First CRM — HCP Module",
    description="LangGraph-powered CRM for pharmaceutical field reps",
    version="1.0.0"
)

# ── CORS Middleware ──────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Without this, browsers BLOCK requests from localhost:3000 → localhost:8000
# allow_origins=["*"] allows ALL origins (use specific URL in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve the frontend HTML file ────────────────────────────────────────────
# This mounts the ../frontend folder so FastAPI can serve index.html
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_frontend():
    """Serve the main HTML frontend page"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI-First CRM API is running. Frontend at /static/index.html"}


# ── Pydantic Request/Response Models ────────────────────────────────────────
# Pydantic validates incoming JSON automatically — if a required field is missing,
# FastAPI returns a 422 error with a clear message (no manual validation needed)

class ChatRequest(BaseModel):
    """Request body for the /agent/chat endpoint"""
    message: str                              # user's typed message
    conversation_history: Optional[List[dict]] = []  # previous messages

class InteractionCreateRequest(BaseModel):
    """Request body for POST /interactions (structured form submission)"""
    hcp_name: str
    hcp_specialty: Optional[str] = None
    interaction_type: str = "Meeting"
    interaction_date: Optional[str] = None
    interaction_time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    logged_by: Optional[str] = "Field Rep"

class InteractionUpdateRequest(BaseModel):
    """Request body for PUT /interactions/{id}"""
    hcp_name: Optional[str] = None
    hcp_specialty: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_date: Optional[str] = None
    interaction_time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    samples_distributed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


# ── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple health check — tells you the server is running"""
    return {"status": "healthy", "service": "AI-First CRM HCP Module"}


# ── AGENT CHAT ENDPOINT ──────────────────────────────────────────────────────
@app.post("/agent/chat")
def chat_with_agent(request: ChatRequest):
    """
    Main endpoint — sends user message to the LangGraph agent.
    The agent decides which tool(s) to use and returns the response.

    Example request:
    POST /agent/chat
    {"message": "Met Dr. Sharma today, discussed OncoBoost Phase 3, he was very positive"}
    """
    try:
        # Run the LangGraph agent — it handles tool selection automatically
        response = run_agent(request.message, request.conversation_history)
        return {
            "success": True,
            "response": response,
            "message_type": "agent"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# ── INTERACTION CRUD ENDPOINTS ───────────────────────────────────────────────

@app.post("/interactions")
def create_interaction(
    data: InteractionCreateRequest,
    db: Session = Depends(get_db)   # Depends() injects the DB session automatically
):
    """
    Create a new interaction via the STRUCTURED FORM (not chat).
    This is the direct form submission path — no LLM involved.
    """
    interaction = HCPInteraction(**data.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return {"success": True, "message": "Interaction logged!", "data": interaction.to_dict()}


@app.get("/interactions")
def get_all_interactions(
    skip: int = 0,         # pagination: how many to skip
    limit: int = 50,       # pagination: max results to return
    db: Session = Depends(get_db)
):
    """Get all interactions (paginated). Used to populate the interactions list."""
    interactions = db.query(HCPInteraction).offset(skip).limit(limit).all()
    return {
        "success": True,
        "total": len(interactions),
        "interactions": [i.to_dict() for i in interactions]
    }


@app.get("/interactions/{interaction_id}")
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Get a single interaction by its ID."""
    interaction = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")
    return {"success": True, "data": interaction.to_dict()}


@app.put("/interactions/{interaction_id}")
def update_interaction(
    interaction_id: int,
    data: InteractionUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update an existing interaction. Only updates fields that are provided."""
    interaction = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")

    # model_dump(exclude_none=True) gives us only the fields that were actually provided
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)
    return {"success": True, "message": "Updated!", "data": interaction.to_dict()}


@app.delete("/interactions/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Delete an interaction record."""
    interaction = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")
    db.delete(interaction)
    db.commit()
    return {"success": True, "message": f"Interaction {interaction_id} deleted"}


@app.get("/interactions/hcp/{hcp_name}")
def get_by_hcp(hcp_name: str, db: Session = Depends(get_db)):
    """Get all interactions with a specific HCP (partial name search)."""
    interactions = db.query(HCPInteraction).filter(
        HCPInteraction.hcp_name.ilike(f"%{hcp_name}%")
    ).order_by(HCPInteraction.created_at.desc()).all()
    return {
        "success": True,
        "hcp_name": hcp_name,
        "total": len(interactions),
        "interactions": [i.to_dict() for i in interactions]
    }