<p align="center">
  <img src="logo.png" alt="MiraOS Logo" width="180" />
</p>

<h1 align="center">MiraOS</h1>

<p align="center">
  An AI-powered Business Operating System — chat, automate, and manage your business with a single platform.
</p>

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python) |
| AI | Ollama (`qwen3:4b`) |
| DB | MongoDB |
| Infra | Docker Compose |

## Getting Started

```bash
# Start all services
docker compose up --build
```

- **Frontend** → http://localhost:5173  
- **Backend API** → http://localhost:8000  

## Project Structure

```
mira/
├── frontend/          # React/Vite TypeScript app
├── fastapi-backend/   # Python FastAPI server
└── docker-compose.yml
```
