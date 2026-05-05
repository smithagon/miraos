from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.terminal_service import TerminalService

router = APIRouter(prefix="/system", tags=["system"])

class CommandRequest(BaseModel):
    command: str

@router.post("/execute")
async def execute_command(req: CommandRequest):
    # For security, we should ideally restrict commands here, 
    # but for this local agent loop, we will allow execution 
    # with user approval on the frontend.
    result = TerminalService.execute(req.command)
    return result
