import asyncio
import logging
from .allocator.allocator import Allocator
from shared_models.database.get_channel import GetChannelRequest, GetChannelResponse
from arq.connections import RedisSettings
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse
from shared_models.scheduler.add_channel import AddChannelRequest, AddChannelResponse
from shared_models.database.get_channels_ids import GetChannelsIdsResponse
from shared_models import Channel
from typing import Optional
from arq import create_pool
from arq.jobs import Job


class Scheduler:
    def __init__(self, slots_count: int, allocation_interval_minutes: int, 
                 parser_redis: RedisSettings, parser_queue_name: str,
                 database_redis: RedisSettings, database_queue_name: str) -> None:
        self.logger = logging.getLogger('scheduler')
        self.allocator = Allocator(slots_count, allocation_interval_minutes)
        
        self.parser_redis_settings = parser_redis
        self.parser_redis = None
        self.parser_queue_name = parser_queue_name
        
        self.database_redis_settings = database_redis
        self.database_redis = None
        self.database_queue_name = database_queue_name
        
        self.__allocator_init = False
    
    async def get_channel_from_db(self, channel_id: int) -> GetChannelResponse:
        task: Optional[Job] = await self.database_redis.enqueue_job('Database.get_channel', GetChannelRequest(channel_id=channel_id)) # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        return await task.result()


    async def init_allocator(self):
        task: Optional[Job] = await self.database_redis.enqueue_job('Database.get_channels_ids') # type: ignore
        if task is None:
            raise ValueError("Task was not created")
        channels_ids: GetChannelsIdsResponse = await task.result()
        
        jobs = [self.get_channel_from_db(channel_id) for channel_id in channels_ids.channel_ids]
        results = await asyncio.gather(*jobs, return_exceptions=True)
        channels: list[GetChannelResponse] = []
        for result in results:
            if isinstance(result, Exception):
                raise ValueError(f"Failed to get channel info: {result}")
            else:
                channels.append(result) # type: ignore
        
        channels.sort(key=lambda x: x.last_update)
        for channel in channels:
            self.allocator.add_channel(channel.channel.channel_id)
        
    async def init(self):
        if not self.parser_redis:
            self.parser_redis = await create_pool(self.parser_redis_settings, default_queue_name=self.parser_queue_name)
        if not self.database_redis:
            self.database_redis = await create_pool(self.database_redis_settings, default_queue_name=self.database_queue_name)
        if not self.__allocator_init:
            await self.init_allocator()
            self.__allocator_init = True
            
    async def get_channel(self, channel_link: str) -> GetChannelInfoResponse:
        request = GetChannelInfoRequest(channel_link=channel_link)
        response = await self.parser_redis.enqueue_job('Parser.get_channel_info', request) # type: ignore
        if not response:
            raise ValueError(f"Failed to get response for channel {channel_link}")
        return await response.result()
        
    @staticmethod
    async def run_iteration(ctx):
        self: Scheduler = ctx['Scheduler_instance']
        if not self.parser_redis or not self.database_redis:
            await self.init()
        
        self.logger.info("Running iteration")
        update_channels = self.allocator.get_next_channels()
        if not update_channels:
            self.logger.info("No channels to update")
            return
        
        jobs = []
        
        for channel_id in update_channels:
            channel = await self.get_channel_from_db(channel_id)
            jobs.append(self.get_channel(channel_link=channel.channel.link))
        
        results = await asyncio.gather(*jobs, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Failed to get channel info: {result}")
                continue
            else:
                await self.database_redis.enqueue_job('Database.update_or_create_channel', result.channel) # type: ignore
    
    
    # Methods
    @staticmethod
    async def add_channel(ctx, request: AddChannelRequest) -> AddChannelResponse:
        self: Scheduler = ctx['Scheduler_instance']
        if not self.parser_redis or not self.database_redis:
            await self.init()
            
        if not isinstance(request, AddChannelRequest):
            raise ValueError(f"Invalid request: {request}")
        
        channel = await self.get_channel(channel_link=request.channel_link)
        await self.database_redis.enqueue_job('Database.update_or_create_channel', channel.channel) # type: ignore
        self.allocator.add_channel(channel.channel.channel_id)
        return AddChannelResponse(channel=channel.channel)