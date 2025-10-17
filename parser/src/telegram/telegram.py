import asyncio
import logging
import os
import re
import shutil
from typing import Optional
from .custom_client import CustomClient, RedisConfig
from tortoise import Tortoise
from ..config import Config, TORTOISE_ORM, TelegramClientConfig
from .models import Client, TelegramCredentials
import zipfile
import io
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from opentele.td.tdesktop import TDesktop
from opentele.api import API


class Telegram:
    TELEGRAM_SERVICE_ID = 777000

    def __init__(
        self, redis_host: str, redis_port: int, telegram_clients_redis_db: int
    ) -> None:
        self.logger = logging.getLogger("telegram")
        self.__redis_config = RedisConfig(
            host=redis_host, port=redis_port, db=telegram_clients_redis_db
        )

    async def init_database(self) -> None:
        self.logger.info("Initializing database")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        self.logger.info("Database initialized")

    async def close(self) -> None:
        await Tortoise.close_connections()

    async def get_client(self) -> CustomClient:
        client = (
            await Client.filter(working=True, is_master=False)
            .order_by("users_count", "id")
            .first()
        )
        if client:
            return CustomClient(client, self.__redis_config)

        master = (
            await Client.filter(is_master=True, working=True)
            .order_by("users_count", "id")
            .first()
        )
        if not master:
            raise ValueError("No working clients found")

        new_child = await self._create_child_client(master)
        return CustomClient(new_child, self.__redis_config)

    async def get_client_from_master(self, master_client_id: int) -> CustomClient:
        master = await Client.get(id=master_client_id, is_master=True)
        if not master.working:
            raise ValueError("Master client is not active")

        child = (
            await Client.filter(master_client=master, working=True)
            .order_by("users_count", "id")
            .first()
        )
        if child is None:
            child = await self._create_child_client(master)

        return CustomClient(child, self.__redis_config)

    async def _create_child_client(self, master_client: Client) -> Client:
        if not master_client.phone_number:
            raise ValueError("Master client phone number is not set")

        credentials: TelegramCredentials = await master_client.telegram_credentials
        child_client = await Client.create(
            telegram_credentials_id=master_client.telegram_credentials_id,
            working=False,
            is_master=False,
            master_client=master_client,
            phone_number=master_client.phone_number,
        )

        target_directory = os.path.join(Config.TDATA_PATH, str(child_client.id))
        tdata_directory = os.path.join(target_directory, "tdata")
        os.makedirs(tdata_directory, exist_ok=True)

        password = self._get_master_password(master_client)
        last_message_id = await self._get_last_telegram_message_id(master_client)

        telethon_client = TelegramClient(
            session=StringSession(),
            api_id=credentials.api_id,
            api_hash=credentials.api_hash,
            device_model=credentials.device_model,
            system_version=credentials.system_version,
            app_version=credentials.app_version,
            lang_code=credentials.lang_code,
            system_lang_code=credentials.system_lang_code,
        )

        try:
            await telethon_client.connect()
            sent_code = await telethon_client.send_code_request(
                master_client.phone_number
            )
            code = await self._fetch_login_code(master_client, last_message_id)
            try:
                await telethon_client.sign_in(
                    phone=master_client.phone_number,
                    code=code,
                    phone_code_hash=sent_code.phone_code_hash,
                )
            except SessionPasswordNeededError:
                if password is None:
                    raise ValueError(
                        "Two-factor password required but not provided for master client"
                    )
                await telethon_client.sign_in(password=password)

            tdesk = await TDesktop.FromTelethon(
                telethon_client, api=API.TelegramDesktop, password=password
            )
            tdesk.SaveTData(tdata_directory)
        except Exception:
            await child_client.delete()
            shutil.rmtree(target_directory, ignore_errors=True)
            raise
        finally:
            await telethon_client.disconnect()

        if password:
            with open(os.path.join(target_directory, "2FA.txt"), "w") as f:
                f.write(password)

        child_custom_client = CustomClient(child_client, self.__redis_config)
        async with child_custom_client:
            self.logger.info("Child client activated")
            child_client.working = True
            await child_client.save()
        return child_client

    # Methods
    @staticmethod
    async def add_client(ctx, tdata: bytes) -> None:
        self: Telegram = ctx["Telegram_instance"]
        self.logger.info("Adding client")

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

        master_client = await Client.create(
            telegram_credentials=telegram_credentials, working=False, is_master=True
        )

        target_directory = os.path.join(Config.TDATA_PATH, str(master_client.id))
        os.makedirs(target_directory, exist_ok=True)
        with io.BytesIO(tdata) as zip_buffer:
            with zipfile.ZipFile(zip_buffer) as z:
                z.extractall(target_directory)
        if not os.path.exists(os.path.join(target_directory, "tdata")):
            raise zipfile.BadZipFile("tdata directory not found")

        client = CustomClient(master_client, self.__redis_config)
        async with client as master_session:
            self.logger.info("Master client activated")
            master_client.working = True
            me = await master_session.get_me()
            phone_number = getattr(me, "phone", None)
            if not phone_number:
                raise ValueError("Unable to get phone number for master client")
            master_client.phone_number = phone_number
            await master_client.save()

        await self._create_child_client(master_client)

    def _get_master_password(self, master_client: Client) -> Optional[str]:
        password_path = os.path.join(
            Config.TDATA_PATH, str(master_client.id), "2FA.txt"
        )
        if not os.path.exists(password_path):
            return None
        with open(password_path, "r") as f:
            password = f.read().strip()
        return password or None

    async def _get_last_telegram_message_id(self, master_client: Client) -> int:
        master_custom_client = CustomClient(master_client, self.__redis_config)
        async with master_custom_client as master_session:
            service_peer = await self._resolve_telegram_service_peer(master_session)
            self.logger.debug(
                "Fetching last message id from service peer %s for master %s",
                service_peer,
                master_client.id,
            )
            messages = await master_session.get_messages(service_peer, limit=1)
            if not messages:
                self.logger.debug(
                    "No prior service messages found for master %s", master_client.id
                )
                return 0
            last_id = messages[0].id
            self.logger.debug(
                "Last service message for master %s has id %s",
                master_client.id,
                last_id,
            )
            return last_id

    async def _fetch_login_code(
        self, master_client: Client, last_message_id: int, timeout: int = 120
    ) -> str:
        master_custom_client = CustomClient(master_client, self.__redis_config)
        async with master_custom_client as master_session:
            service_peer = await self._resolve_telegram_service_peer(master_session)
            self.logger.info(
                "Waiting for login code in service chat for master %s starting from message id %s (timeout %ss)",
                master_client.id,
                last_message_id,
                timeout,
            )
            for _ in range(timeout):
                messages = await master_session.get_messages(service_peer, limit=5)
                for message in messages:
                    if message.id <= last_message_id:
                        continue
                    preview = (
                        (message.message or "").replace("\n", " ").strip()[:80]
                        if message.message
                        else ""
                    )
                    self.logger.debug(
                        "Examining service message id %s for master %s: '%s'",
                        message.id,
                        master_client.id,
                        preview,
                    )
                    code = self._extract_code(message.message)
                    if code:
                        self.logger.info(
                            "Login code %s detected in message id %s for master %s",
                            code,
                            message.id,
                            master_client.id,
                        )
                        return code
                await asyncio.sleep(1)
            self.logger.error(
                "Timeout waiting for login code for master %s after %ss",
                master_client.id,
                timeout,
            )
        raise TimeoutError("Failed to receive login code from master client")

    @staticmethod
    def _extract_code(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"(\d{5,6})", text)
        if match:
            return match.group(1)
        return None

    async def _resolve_telegram_service_peer(
        self, client: TelegramClient
    ) -> object:
        try:
            peer = await client.get_entity(self.TELEGRAM_SERVICE_ID)
            self.logger.debug("Resolved Telegram service peer by id %s", self.TELEGRAM_SERVICE_ID)
            return peer
        except Exception:
            self.logger.warning(
                "Failed to resolve Telegram service by id %s, falling back to username lookup",
                self.TELEGRAM_SERVICE_ID,
            )
            return "Telegram"
