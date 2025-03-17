from ..base import BaseService
from typing import Optional
from arq.jobs import Job
from shared_models.scheduler.add_channel import AddChannelRequest
from shared_models import Channel
from ...config import RedisConfig


class Scheduler(BaseService):
    def __init__(self):
        super().__init__(RedisConfig.SCHEDULER_QUEUE_NAME)
    
    async def add_channel(self, request: AddChannelRequest) -> Channel:
        await self.init()
        task: Optional[Job] = await self.redis.enqueue_job('Scheduler.add_channel', request) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()