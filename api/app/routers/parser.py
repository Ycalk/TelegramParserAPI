from fastapi import APIRouter, HTTPException, File, UploadFile
from app.config import ApiServiceConfig, REDIS_SETTINGS
import app.services as services
from shared_models.parser.get_channel_info import GetChannelInfoResponse, GetChannelInfoRequest


parser_service = services.Parser()
router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post("/add_client", responses=ApiServiceConfig.DEFAULT_RESPONSE)
async def add_client(tdata: UploadFile = File(...)):
    await parser_service.add_client(tdata.file.read())
    return {"message": "Client added successfully"}

@router.post("/get_channel_info", responses=ApiServiceConfig.DEFAULT_RESPONSE, response_model=GetChannelInfoResponse)
async def get_channel_info(request: GetChannelInfoRequest):
    return await parser_service.get_channel_info(request)