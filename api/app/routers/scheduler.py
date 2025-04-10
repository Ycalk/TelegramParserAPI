from app.config import ApiServiceConfig
from fastapi import APIRouter, HTTPException
import app.services as services
from shared_models.scheduler.add_channel import AddChannelRequest, AddChannelResponse
from app.services.token import verify_api_key
from fastapi import Depends


scheduler_service = services.Scheduler()
router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.post("/add_channel", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=AddChannelResponse)
async def add_channel(request: AddChannelRequest, api_key_verified: None = Depends(verify_api_key)):
    """Add channel to the scheduler"""
    try:
        return await scheduler_service.add_channel(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))