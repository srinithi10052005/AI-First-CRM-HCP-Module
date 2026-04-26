from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from models.database import Base

class HCPInteraction(Base):
    __tablename__ = "hcp_interactions"
    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(255), nullable=False)
    hcp_specialty = Column(String(255), nullable=True)
    interaction_type = Column(String(100), default="Meeting")
    interaction_date = Column(String(50), nullable=True)
    interaction_time = Column(String(20), nullable=True)
    attendees = Column(Text, nullable=True)
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)
    samples_distributed = Column(Text, nullable=True)
    sentiment = Column(String(50), default="Neutral")
    sentiment_score = Column(Float, nullable=True)
    ai_summary = Column(Text, nullable=True)
    raw_chat_input = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    logged_by = Column(String(255), default="Field Rep")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id, "hcp_name": self.hcp_name, "hcp_specialty": self.hcp_specialty,
            "interaction_type": self.interaction_type, "interaction_date": self.interaction_date,
            "interaction_time": self.interaction_time, "attendees": self.attendees,
            "topics_discussed": self.topics_discussed, "materials_shared": self.materials_shared,
            "samples_distributed": self.samples_distributed, "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score, "ai_summary": self.ai_summary,
            "raw_chat_input": self.raw_chat_input, "outcomes": self.outcomes,
            "follow_up_actions": self.follow_up_actions, "logged_by": self.logged_by,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }