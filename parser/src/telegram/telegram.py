import os
from telethon import TelegramClient
from ..config import Config
from .models import Client
from telegram.opentele.src.td import TDesktop
from telegram.opentele.src.api import API
import uuid
from typing import Optional

class Telegram:
    def __init__(self, client_id: int) -> None:
        self.__client_id = client_id
        self.__initialized = False
        self.__session_path = os.path.join(Config.SESSION_DIR, f"{uuid.uuid4()}.session")
        self.__client: Optional[TelegramClient] = None
    
    async def __initialize(self) -> None:
        if self.__initialized:
            return
        client = await Client.get(id=self.__client_id)
        if client is None:
            raise ValueError("Client not found")
        if client.working == False:
            raise ValueError("Client is not working")
        tdata_path = os.path.join(Config.TDATA_PATH, str(client.id), "tdata")
        api = API.TelegramDesktop(
            api_id=client.api_id,
            api_hash=client.api_hash,
            device_model=client.device_model,
            system_version=client.system_version,
            app_version=client.app_version,
            lang_code=client.lang_code,
            system_lang_code=client.system_lang_code,
            lang_pack=client.lang_pack,
        )
        tdesk = TDesktop(tdata_path, api)
        pass_path = os.path.join(Config.TDATA_PATH, str(client.id), "2FA.txt")
        password = None
        if os.path.exists(pass_path):
            password = open(pass_path).read().strip()
        self.__client = await tdesk.ToTelethon(self.__session_path, api, password=password) # type: ignore
        
    async def get_client(self) -> TelegramClient:
        await self.__initialize()
        if self.__client is None:
            raise ValueError("Client is None")
        return self.__client
