from app.config import ApiServiceConfig
from fastapi import APIRouter, HTTPException
import app.services as services
from shared_models.scheduler.add_channel import AddChannelRequest
from shared_models import Channel as ChannelModel
from fastapi import Depends


scheduler_service = services.Scheduler()
router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.post("/add_channel", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=ChannelModel)
async def add_channel(request: AddChannelRequest):
    try:
        return await scheduler_service.add_channel(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))