from pydantic import BaseModel, model_validator, ValidationError
from typing_extensions import Self, Optional

class AddChannelRequest(BaseModel):
    channel_link: Optional[str] = None
    channel_id: Optional[int] = None
    
    @model_validator(mode='after')
    def check_at_least_one(self) -> Self:
        if self.channel_link is None and self.channel_id is None:
            raise ValidationError('channel_link or channel_id must be provided')
        return self