from ..base import BaseService
from typing import Optional
from arq.jobs import Job
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse
from ...config import RedisConfig


class Parser(BaseService):
    def __init__(self):
        super().__init__(RedisConfig.PARSER_QUEUE_NAME)
    
    async def get_channel_info(self, request: GetChannelInfoRequest) -> GetChannelInfoResponse:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Parser.get_channel_info', request) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()