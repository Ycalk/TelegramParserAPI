from pydantic import BaseModel


class GetChannelRequest(BaseModel):
    channel_id: int