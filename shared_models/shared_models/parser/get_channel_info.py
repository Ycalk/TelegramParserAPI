from pydantic import BaseModel
from ..channel import Channel
from typing_extensions import Optional


class GetChannelInfoRequest(BaseModel):
    channel_link: str
    
class GetChannelInfoResponse(BaseModel):
    channel: Channel