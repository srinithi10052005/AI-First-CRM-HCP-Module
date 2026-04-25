# agent/tools.py — All 5 LangGraph tools

import os, json
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from models.database import SessionLocal
from models.interaction import HCPInteraction

load_dotenv()

def get_llm():
    return ChatGroq(
        model="gemma2-9b-it",
        temperature=0.1,
        max_tokens=1024,
        api_key=os.getenv("GROQ_API_KEY")
    )

def clean_json(raw: str) -> str:
    """Strip markdown code fences from LLM output"""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


# ── TOOL 1: LOG INTERACTION ─────────────────────────────────────────────────
@tool
def log_interaction(user_message: str, logged_by: str = "Field Rep") -> dict:
    """
    Log a new HCP interaction from a natural language description.
    Use when the user wants to record a meeting, call, or visit with a doctor.
    Extracts all structured data using AI and saves to the database.

    Args:
        user_message: Plain English description of the interaction.
        logged_by: Name of the field rep logging the interaction.
    """
    llm = get_llm()
    prompt = f"""
You are a CRM data extraction assistant for a pharmaceutical company.
Extract structured data from this field rep's note and return ONLY valid JSON (no markdown, no extra text):

{{
  "hcp_name": "doctor's full name",
  "hcp_specialty": "medical specialty or null",
  "interaction_type": "Meeting or Call or Email or Conference",
  "interaction_date": "YYYY-MM-DD or null",
  "interaction_time": "HH:MM or null",
  "attendees": "other attendees or null",
  "topics_discussed": "detailed topics summary",
  "materials_shared": "materials/brochures given or null",
  "samples_distributed": "samples and quantity or null",
  "sentiment": "Positive or Neutral or Negative",
  "sentiment_score": 0.75,
  "outcomes": "key results/agreements or null",
  "follow_up_actions": "next steps or null",
  "ai_summary": "2-3 sentence professional summary"
}}

Field rep's note: {user_message}
"""
    try:
        response = llm.invoke(prompt)
        data = json.loads(clean_json(response.content))
    except Exception as e:
        return {"success": False, "error": f"LLM extraction failed: {str(e)}"}

    db = SessionLocal()
    try:
        interaction = HCPInteraction(
            hcp_name=data.get("hcp_name", "Unknown HCP"),
            hcp_specialty=data.get("hcp_specialty"),
            interaction_type=data.get("interaction_type", "Meeting"),
            interaction_date=data.get("interaction_date"),
            interaction_time=data.get("interaction_time"),
            attendees=data.get("attendees"),
            topics_discussed=data.get("topics_discussed"),
            materials_shared=data.get("materials_shared"),
            samples_distributed=data.get("samples_distributed"),
            sentiment=data.get("sentiment", "Neutral"),
            sentiment_score=data.get("sentiment_score"),
            outcomes=data.get("outcomes"),
            follow_up_actions=data.get("follow_up_actions"),
            ai_summary=data.get("ai_summary"),
            raw_chat_input=user_message,
            logged_by=logged_by
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return {
            "success": True,
            "message": f"✅ Interaction with {interaction.hcp_name} logged! (ID: {interaction.id})",
            "interaction_id": interaction.id,
            "data": interaction.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── TOOL 2: EDIT INTERACTION ────────────────────────────────────────────────
@tool
def edit_interaction(interaction_id: int, updates: str) -> dict:
    """
    Edit or update an existing HCP interaction record by its ID.
    Use when the user says 'update interaction 5' or 'change the sentiment for ID 3'.

    Args:
        interaction_id: The numeric ID of the interaction to edit.
        updates: JSON string of fields to update. Example: '{"sentiment": "Positive"}'
    """
    try:
        updates_dict = json.loads(updates) if isinstance(updates, str) else updates
    except Exception:
        return {"success": False, "error": "Invalid updates JSON format"}

    db = SessionLocal()
    try:
        interaction = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
        if not interaction:
            return {"success": False, "error": f"No interaction found with ID {interaction_id}"}

        changed = []
        for field, value in updates_dict.items():
            if hasattr(interaction, field):
                setattr(interaction, field, value)
                changed.append(field)

        # Refresh AI summary if content changed
        if any(f in updates_dict for f in ["topics_discussed", "outcomes", "sentiment"]):
            llm = get_llm()
            resp = llm.invoke(
                f"Write a 2-3 sentence professional CRM summary. "
                f"HCP: {interaction.hcp_name}, Topics: {interaction.topics_discussed}, "
                f"Outcomes: {interaction.outcomes}, Sentiment: {interaction.sentiment}"
            )
            interaction.ai_summary = resp.content.strip()
            changed.append("ai_summary")

        db.commit()
        db.refresh(interaction)
        return {
            "success": True,
            "message": f"✅ Interaction {interaction_id} updated. Changed: {', '.join(changed)}",
            "data": interaction.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── TOOL 3: ANALYZE SENTIMENT ───────────────────────────────────────────────
@tool
def analyze_sentiment(interaction_id: int) -> dict:
    """
    Analyze and update the HCP's sentiment for an interaction using AI.
    Use when user asks 'how was the doctor's reaction?' or 'analyze sentiment for ID 4'.

    Args:
        interaction_id: The ID of the interaction to analyze.
    """
    db = SessionLocal()
    try:
        i = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
        if not i:
            return {"success": False, "error": f"Interaction {interaction_id} not found"}

        llm = get_llm()
        prompt = f"""
Analyze the HCP's receptiveness in this pharma field rep interaction.
Topics: {i.topics_discussed}
Outcomes: {i.outcomes}
HCP: {i.hcp_name} ({i.hcp_specialty or 'unknown specialty'})

Return ONLY valid JSON (no markdown):
{{"sentiment": "Positive or Neutral or Negative", "sentiment_score": 0.0, "explanation": "reason"}}
"""
        resp = llm.invoke(prompt)
        result = json.loads(clean_json(resp.content))

        i.sentiment = result["sentiment"]
        i.sentiment_score = result["sentiment_score"]
        db.commit()

        return {
            "success": True,
            "message": f"🧠 Sentiment: {result['sentiment']} for {i.hcp_name}",
            "sentiment": result["sentiment"],
            "sentiment_score": result["sentiment_score"],
            "explanation": result["explanation"]
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── TOOL 4: SUGGEST FOLLOW-UP ───────────────────────────────────────────────
@tool
def suggest_followup(interaction_id: int) -> dict:
    """
    Generate AI follow-up action recommendations for an HCP interaction.
    Use when user asks 'what should I do next?' or 'suggest follow-ups for ID 2'.

    Args:
        interaction_id: The ID of the interaction to generate follow-ups for.
    """
    db = SessionLocal()
    try:
        i = db.query(HCPInteraction).filter(HCPInteraction.id == interaction_id).first()
        if not i:
            return {"success": False, "error": f"Interaction {interaction_id} not found"}

        llm = get_llm()
        prompt = f"""
You are a pharma sales coach. Suggest follow-up actions for this field rep interaction.
HCP: {i.hcp_name} | Sentiment: {i.sentiment} | Topics: {i.topics_discussed} | Outcomes: {i.outcomes}

Return ONLY valid JSON (no markdown):
{{"suggestions": ["action 1", "action 2", "action 3"], "priority": "High or Medium or Low", "reasoning": "why"}}
"""
        resp = llm.invoke(prompt)
        result = json.loads(clean_json(resp.content))

        i.follow_up_actions = "\n".join(f"• {s}" for s in result["suggestions"])
        db.commit()

        return {
            "success": True,
            "message": f"💡 Follow-ups generated for {i.hcp_name}",
            "suggestions": result["suggestions"],
            "priority": result["priority"],
            "reasoning": result["reasoning"]
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── TOOL 5: FETCH HCP PROFILE ───────────────────────────────────────────────
@tool
def fetch_hcp_profile(hcp_name: str) -> dict:
    """
    Fetch all past interactions and AI relationship summary for an HCP.
    Use when user asks 'show history for Dr. Smith' or 'what's my relationship with Dr. Patel?'.

    Args:
        hcp_name: Name of the HCP to look up (partial name supported).
    """
    db = SessionLocal()
    try:
        interactions = db.query(HCPInteraction).filter(
            HCPInteraction.hcp_name.ilike(f"%{hcp_name}%")
        ).order_by(HCPInteraction.created_at.desc()).all()

        if not interactions:
            return {"success": True, "message": f"No interactions found for '{hcp_name}'", "total": 0}

        history = "\n".join([
            f"- {i.interaction_date}: {i.interaction_type}, Topics: {i.topics_discussed}, Sentiment: {i.sentiment}"
            for i in interactions[:10]
        ])

        llm = get_llm()
        summary = llm.invoke(
            f"Write a 3-4 sentence pharma sales relationship summary for field rep.\n"
            f"HCP: {interactions[0].hcp_name} | Total visits: {len(interactions)}\n"
            f"History:\n{history}"
        )

        return {
            "success": True,
            "hcp_name": interactions[0].hcp_name,
            "hcp_specialty": interactions[0].hcp_specialty,
            "total_interactions": len(interactions),
            "relationship_summary": summary.content.strip(),
            "interactions": [i.to_dict() for i in interactions]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# Export all tools for graph.py
ALL_TOOLS = [log_interaction, edit_interaction, analyze_sentiment, suggest_followup, fetch_hcp_profile]