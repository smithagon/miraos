from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# ── Chat ────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str                      # "user" | "assistant" | "system"
    content: str
    thought: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    session_id: str
    template_id: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SessionCreate(BaseModel):
    template_id: Optional[str] = None

# ── Items (CRUD entity) ─────────────────────────────────────────────────
class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    status: str = "active"

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
class Nl2SqlConfig(BaseModel):
    connection_string: Optional[str] = None
    status: Optional[str] = None

# ── Templates (Base Prompts) ──────────────────────────────────────────
class PromptTemplate(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    base_prompt: str
    is_active: bool = True
    nl2sql_config: Optional[Nl2SqlConfig] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TemplateCreate(BaseModel):
    name: str
    base_prompt: str
    is_active: bool = True
    nl2sql_config: Optional[Nl2SqlConfig] = None

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    base_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    nl2sql_config: Optional[Nl2SqlConfig] = None
