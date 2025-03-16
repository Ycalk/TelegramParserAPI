import os
from dotenv import load_dotenv
from typing import Any, Dict, Union
from arq.connections import RedisSettings
load_dotenv()


class ApiServiceConfig:
    BASE_PREFIX = '/api/v1'
    DEFAULT_RESPONSE: Dict[Union[int,str], Dict[str, Any]] = {500: {"description": "Internal Error"}, 
                                                              504: {"description": "Timeout Error"},
                                                              400: {"description": "Something went wrong while processing request"},
                                                              200: {"description": "Success"}}

REDIS_SETTINGS = RedisSettings(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))