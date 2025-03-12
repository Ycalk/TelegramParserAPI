from pydantic import BaseModel


class ChannelInfo(BaseModel):
    channel_id: int
    link: str
    name: str
    description: str
    chat_photo_id: str
    subscribers: int
    views: int