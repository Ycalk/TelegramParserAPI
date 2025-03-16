from pydantic import BaseModel, model_validator, ValidationError
from ..channel import Channel
from typing_extensions import Self, Optional


class GetChannelInfoRequest(BaseModel):
    channel_link: Optional[str]
    channel_id: Optional[int]
    
    @model_validator(mode='after')
    def check_at_least_one(self) -> Self:
        if self.channel_link is None and self.channel_id is None:
            raise ValidationError('channel_link or channel_id must be provided')
        return self
    
class GetChannelInfoResponse(BaseModel):
    channel: Channel