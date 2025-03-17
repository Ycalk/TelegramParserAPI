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

class RedisConfig:
    PARSER_QUEUE_NAME = os.getenv('PARSER_QUEUE_NAME', 'parser')
    TELEGRAM_QUEUE_NAME = os.getenv('TELEGRAM_QUEUE_NAME', 'telegram')
    DATABASE_QUEUE_NAME = os.getenv('DATABASE_QUEUE_NAME', 'database')
    SCHEDULER_QUEUE_NAME= os.getenv('SCHEDULER_QUEUE_NAME', 'scheduler')
    REDIS_SETTINGS = RedisSettings(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))