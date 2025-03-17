import logging
from allocator.allocator import Allocator
from arq.connections import RedisSettings
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse
from arq import create_pool


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
    
    async def init(self):
        if not self.parser_redis:
            self.parser_redis = await create_pool(self.parser_redis_settings, default_queue_name=self.parser_queue_name)
        if not self.database_redis:
            self.database_redis = await create_pool(self.database_redis_settings, default_queue_name=self.database_queue_name)
    
    @staticmethod
    async def run_iteration(ctx):
        self: Scheduler = ctx['Scheduler_instance']
        
        if not self.parser_redis:
            await self.init()
        if not self.database_redis:
            await self.init()
        
        self.logger.info("Running iteration")
        update_channels = self.allocator.get_next_channels()
        pass