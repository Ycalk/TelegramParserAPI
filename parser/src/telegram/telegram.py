import logging
import os
from telethon.sessions import MemorySession
from telethon import TelegramClient
from tortoise import Tortoise
from ..config import Config, TORTOISE_ORM, TelegramClientConfig
from .models import Client, TelegramCredentials
from opentele.td import TDesktop
from opentele.api import API
from typing import Optional
from telethon.errors import SessionPasswordNeededError
from shared_models.parser.errors import SessionPasswordNeeded
import zipfile
import io
from tortoise.expressions import F


class Telegram:
    def __init__(self) -> None:
        self.logger = logging.getLogger("telegram")
        self.__telegram_client: Optional[TelegramClient] = None
        self.__client: Optional[Client] = None
    
    async def init_database(self) -> None:
        self.logger.info("Initializing database")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        self.logger.info("Database initialized")
    
    async def initialize(self) -> None:
        if self.__client:
            return
        
        self.logger.info("Getting client")
        self.__client = await Client.filter(working=True).order_by("users_count", "id").first()
        if self.__client is None:
            self.logger.error("No working clients found")
            return 
        await Client.filter(id=self.__client.id).update(users_count=F('users_count') + 1)
        telegram_credentials: TelegramCredentials = await self.__client.telegram_credentials
        
        self.logger.info("Creating session")
        tdata_path = os.path.join(Config.TDATA_PATH, str(self.__client.id), "tdata")
        api = API.TelegramDesktop(
            api_id=telegram_credentials.api_id,
            api_hash=telegram_credentials.api_hash,
            device_model=telegram_credentials.device_model,
            system_version=telegram_credentials.system_version,
            app_version=telegram_credentials.app_version,
            lang_code=telegram_credentials.lang_code,
            system_lang_code=telegram_credentials.system_lang_code,
            lang_pack=telegram_credentials.lang_pack,
        )
        tdesk = TDesktop(tdata_path, api)
        
        pass_path = os.path.join(Config.TDATA_PATH, str(self.__client.id), "2FA.txt")
        password = None
        if os.path.exists(pass_path):
            password = open(pass_path).read().strip()
        
        try:
            self.__telegram_client = await tdesk.ToTelethon(session=MemorySession(), api=api, password=password) # type: ignore
        except SessionPasswordNeededError as e:
            self.__client.working = False
            await self.__client.save()
            raise SessionPasswordNeeded()
        
    async def get_client(self) -> TelegramClient:
        await self.initialize()
        if self.__telegram_client is None:
            raise ValueError("No available clients")
        return self.__telegram_client
    
    async def close(self) -> None:
        if self.__telegram_client is not None:
            await self.__telegram_client.disconnect() # type: ignore
            self.__telegram_client = None
        if self.__client is not None:
            await Client.filter(id=self.__client.id).update(users_count=F('users_count') - 1)
        await Tortoise.close_connections()
    
    async def update_client(self):
        new_client = await Client.filter(working=True).order_by("users_count", "id").first()
        if new_client is None:
            self.logger.error("No working clients found")
            return
        if self.__client is not None and new_client.id == self.__client.id:
            self.logger.info("Client is the same")
            return

        old_client = self.__client
        old_telegram_client = self.__telegram_client
        
        self.__client = None
        await self.initialize()
        
        if old_client is not None:
            self.logger.info("Disconnecting from old client")
            await Client.filter(id=old_client.id).update(users_count=F('users_count') - 1)
            if old_telegram_client is not None:
                await old_telegram_client.disconnect() # type: ignore
        
    # Methods
    @staticmethod
    async def add_client(ctx, tdata: bytes) -> None:
        self: Telegram = ctx['Telegram_instance']
        self.logger.info('Adding client')
        
        telegram_credentials, _ = await TelegramCredentials.get_or_create(
            api_id=TelegramClientConfig.API_ID,
            api_hash=TelegramClientConfig.API_HASH,
            device_model=TelegramClientConfig.DEVICE_MODEL,
            system_version=TelegramClientConfig.SYSTEM_VERSION,
            app_version=TelegramClientConfig.APP_VERSION,
            lang_code=TelegramClientConfig.LANG_CODE,
            system_lang_code=TelegramClientConfig.SYSTEM_LANG_CODE,
            lang_pack=TelegramClientConfig.LANG_PACK,
        )
        
        new_client = await Client.create(
            telegram_credentials=telegram_credentials,
            working=False
        )
        await new_client.save()
        target_directory = os.path.join(Config.TDATA_PATH, str(new_client.id))
        os.makedirs(target_directory, exist_ok=True)
        with io.BytesIO(tdata) as zip_buffer:
            with zipfile.ZipFile(zip_buffer) as z:
                z.extractall(target_directory)
        if not os.path.exists(os.path.join(target_directory, "tdata")):
            raise zipfile.BadZipFile("tdata directory not found")
        
        new_client.working = True
        await new_client.save()
