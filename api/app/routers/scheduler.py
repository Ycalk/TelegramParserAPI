from app.config import ApiServiceConfig
from fastapi import APIRouter, HTTPException
import app.services as services
from shared_models.scheduler.add_channel import AddChannelRequest, AddChannelResponse
from ..models.scheduler_add_channel import AddChannelResponse as SchedulerAddChannelResponse
from fastapi.responses import JSONResponse
from app.services.token import verify_api_key
from fastapi import Depends


scheduler_service = services.Scheduler()
router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.post(
    "/add_channel",
    responses={
        200: {"model": SchedulerAddChannelResponse, "description": "Successful response"},
        302: {"model": SchedulerAddChannelResponse, "description": "Channel already exists"},
        **ApiServiceConfig.DEFAULT_RESPONSE,
    },
    response_model=SchedulerAddChannelResponse,
)
async def add_channel(request: AddChannelRequest, api_key_verified: None = Depends(verify_api_key)):
    """Add channel to the scheduler"""
    try:
        response: AddChannelResponse = await scheduler_service.add_channel(request)
        if response.success:
            return JSONResponse(
                status_code=200,
                content={
                    "channel": response.channel,
                },
            )
        else:
            return JSONResponse(
                status_code=302,
                content={
                    "channel": response.channel,
                },
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))