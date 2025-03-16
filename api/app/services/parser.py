from .base import BaseService
from typing import Optional
from arq.jobs import Job
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse

class Parser(BaseService):
    async def add_client(self, tdata: bytes):
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Telegram.add_client', tdata) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()
    
    async def get_channel_info(self, request: GetChannelInfoRequest) -> GetChannelInfoResponse:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Parser.get_channel_info', request.dict()) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()