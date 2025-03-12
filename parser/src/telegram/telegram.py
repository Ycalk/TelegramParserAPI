import os
from telethon import TelegramClient
from tortoise import Tortoise
from ..config import Config, TORTOISE_ORM
from .models import Client
from telegram.opentele.src.td import TDesktop
from telegram.opentele.src.api import API
import uuid
from typing import Optional

class Telegram:
    def __init__(self) -> None:
        self.__initialized = False
        self.__session_path = os.path.join(Config.SESSION_DIR, f"{uuid.uuid4()}.session")
        self.__telegram_client: Optional[TelegramClient] = None
        self.__client: Optional[Client] = None
    
    async def __initialize(self) -> None:
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        
        if self.__initialized:
            return
        
        self.__client = await Client.filter(working=True).order_by("users_count", "id").first()
        if self.__client is None:
            raise ValueError("No active clients found")
        self.__client.users_count += 1
        await self.__client.save()
        
        tdata_path = os.path.join(Config.TDATA_PATH, str(self.__client.id), "tdata")
        api = API.TelegramDesktop(
            api_id=self.__client.api_id,
            api_hash=self.__client.api_hash,
            device_model=self.__client.device_model,
            system_version=self.__client.system_version,
            app_version=self.__client.app_version,
            lang_code=self.__client.lang_code,
            system_lang_code=self.__client.system_lang_code,
            lang_pack=self.__client.lang_pack,
        )
        tdesk = TDesktop(tdata_path, api)
        
        pass_path = os.path.join(Config.TDATA_PATH, str(self.__client.id), "2FA.txt")
        password = None
        if os.path.exists(pass_path):
            password = open(pass_path).read().strip()
            
        self.__telegram_client = await tdesk.ToTelethon(self.__session_path, api, password=password) # type: ignore
        
    async def get_client(self) -> TelegramClient:
        await self.__initialize()
        if self.__telegram_client is None:
            raise ValueError("Client is None")
        return self.__telegram_client
    
    async def close(self) -> None:
        if self.__telegram_client is not None:
            await self.__telegram_client.disconnect() # type: ignore
        self.__telegram_client = None
        if os.path.exists(self.__session_path):
            os.remove(self.__session_path)
        self.__initialized = False
        await Tortoise.close_connections()
