from ..base import BaseService
from typing import Optional
from arq.jobs import Job
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse
from ...config import RedisConfig


class Telegram(BaseService):
    def __init__(self):
        super().__init__(RedisConfig.TELEGRAM_QUEUE_NAME)
    
    async def add_client(self, tdata: bytes):
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Telegram.add_client', tdata) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()