from fastapi import APIRouter, HTTPException
from app.config import ApiServiceConfig


router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post("/create_task", responses=ApiServiceConfig.DEFAULT_RESPONSE)
async def create_task():
    return {"message": "Task created successfully"}