from arq import ArqRedis, create_pool
from typing import Optional
from ..config import REDIS_SETTINGS


class BaseService:
    def __init__(self) -> None:
        self.redis: Optional[ArqRedis] = None
    
    async def init(self):
        if not self.redis:
            self.redis = await create_pool(REDIS_SETTINGS)