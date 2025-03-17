from app.config import ApiServiceConfig
from fastapi import APIRouter, HTTPException
import app.services as services
from shared_models.database.get_channel import GetChannelRequest
from shared_models.database.get_channels_ids import GetChannelsIdsResponse
from shared_models.database.get_24h_statistics import Get24hStatisticsRequest, Get24hStatisticsResponse
from shared_models import Channel as ChannelModel
from fastapi import Depends


database_service = services.Database()
router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/get_channel", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=ChannelModel)
async def add_client(request: GetChannelRequest = Depends()):
    try:
        return await database_service.get_channel(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_channels_ids", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=GetChannelsIdsResponse)
async def get_channels_ids():
    try:
        return await database_service.get_channels_ids()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_24h_statistics", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=Get24hStatisticsResponse)
async def get_24h_statistics(request: Get24hStatisticsRequest = Depends()):
    try:
        return await database_service.get_24h_statistics(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))