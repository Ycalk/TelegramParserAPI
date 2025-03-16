from pydantic import BaseModel
from typing import Optional


class Channel(BaseModel):
    channel_id: int
    link: str
    name: str
    description: Optional[str]
    channel_photo_id: Optional[str]
    subscribers: int
    views: int