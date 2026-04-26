# agent/graph.py
# Builds the LangGraph ReAct agent

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from agent.tools import ALL_TOOLS

load_dotenv()

SYSTEM_PROMPT = """You are an AI assistant for a pharmaceutical CRM system helping field representatives manage HCP (Healthcare Professional) interactions.

You have access to these 5 tools:
1. log_interaction — Record a new HCP meeting/call from natural language description
2. edit_interaction — Update/modify an existing interaction by its ID
3. analyze_sentiment — Use AI to classify HCP sentiment for an interaction
4. suggest_followup — Generate AI-powered follow-up action recommendations
5. fetch_hcp_profile — Retrieve all past interactions + relationship summary for an HCP

Always be professional, precise, and pharma-industry focused.
When logging, extract all available details from the user's message.
When editing, confirm what was changed.
Always confirm actions taken with clear, structured responses."""


def build_agent():
    """
    Builds the LangGraph ReAct agent.
    
    FIX: Newer LangGraph versions removed 'state_modifier' parameter.
    Use 'prompt' parameter instead — it accepts a SystemMessage object.
    """
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY")
    )

    # ✅ FIXED: use 'prompt' with SystemMessage instead of 'state_modifier'
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT)
    )

    return agent


# Single shared agent instance reused across all requests
agent_executor = build_agent()


def run_agent(user_message: str, conversation_history: list = None) -> str:
    """
    Runs the LangGraph agent and returns the final text response.
    
    Args:
        user_message: What the user typed in the chat
        conversation_history: Previous messages for context
    Returns:
        Agent's final response as a string
    """
    messages = []

    # Add previous conversation messages for context
    if conversation_history:
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    # Run the agent — it loops: think → pick tool → run tool → think → answer
    result = agent_executor.invoke({"messages": messages})

    # Last message in the list = agent's final answer
    return result["messages"][-1].content