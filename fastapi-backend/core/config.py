import os

class Settings:
    # App
    APP_TITLE = "Business OS API"
    APP_VERSION = "2.0.0"

    # Security
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://business_frontend",
    ]

    # Database
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/business?authSource=admin")
    DB_NAME = "business_os"

    # LLM
    MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:8b")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    # Qwen3 and other “thinking” models expose reasoning via Ollama’s `thinking` stream field when enabled.
    OLLAMA_THINK = os.getenv("OLLAMA_THINK", "true").lower() in ("1", "true", "yes")

    # System prompt
    SYSTEM_PROMPT = (
        "You are Mira, an intelligent AI assistant for Business OS — a premium workspace platform. "
        "Be concise, insightful, and professional. When reasoning through complex questions, "
        "wrap your internal thinking inside <thought>...</thought> tags before giving your final answer."
    )

settings = Settings()
