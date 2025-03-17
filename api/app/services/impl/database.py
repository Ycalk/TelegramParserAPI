from ..base import BaseService
from typing import Optional
from arq.jobs import Job
from shared_models.database.get_channel import GetChannelRequest
from shared_models.database.get_channels_ids import GetChannelsIdsResponse
from shared_models.database.get_24h_statistics import Get24hStatisticsRequest, Get24hStatisticsResponse
from shared_models import Channel
from ...config import RedisConfig


class Database(BaseService):
    def __init__(self):
        super().__init__(RedisConfig.DATABASE_QUEUE_NAME)
    
    async def get_channel(self, request: GetChannelRequest) -> Channel:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Database.get_channel', request) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()
    
    async def get_channels_ids(self) -> GetChannelsIdsResponse:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Database.get_channel') # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()
    
    async def get_24h_statistics(self, request: Get24hStatisticsRequest) -> Get24hStatisticsResponse:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Database.get_24h_statistics', request) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()