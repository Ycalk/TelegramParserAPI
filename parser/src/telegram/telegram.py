import logging
import os
import json
import tempfile
import zipfile
import io
from .custom_client import CustomClient, RedisConfig
from tortoise import Tortoise
from ..config import TORTOISE_ORM, TelegramClientConfig
from .models import Client, TelegramCredentials
from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.sessions import SQLiteSession, StringSession


class Telegram:
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
        """Получает рабочего клиента, пропуская нерабочих"""
        clients = await Client.filter(working=True).order_by(
            "users_count", "id"
        ).all()

        if not clients:
            self.logger.error("No working clients found in database")
            raise ValueError("No working clients found")

        # Пробуем клиентов по очереди
        last_error = None
        for client in clients:
            try:
                custom_client = CustomClient(client, self.__redis_config)
                # Пробуем проверить доступность
                self.logger.info(
                    f"Trying client ID {client.id} "
                    f"(users_count={client.users_count})"
                )
                return custom_client
            except Exception as e:
                self.logger.warning(
                    f"Client ID {client.id} is not available: {e}. "
                    "Trying next client..."
                )
                last_error = e
                continue

        # Если все клиенты не работают
        self.logger.error(
            f"All {len(clients)} clients failed. "
            f"Last error: {last_error}"
        )
        raise ValueError(
            f"No working clients found. Last error: {last_error}"
        )

    # Methods
    @staticmethod
    async def add_client(ctx, archive_data: bytes) -> None:
        self: Telegram = ctx["Telegram_instance"]
        self.logger.info("Adding client from archive with .session and .json files")

        # Распаковываем архив во временную директорию
        session_data = None
        json_data = None
        
        with io.BytesIO(archive_data) as zip_buffer:
            try:
                with zipfile.ZipFile(zip_buffer) as z:
                    # Ищем .session и .json файлы в архиве
                    for file_info in z.namelist():
                        if file_info.endswith('.session'):
                            session_data = z.read(file_info)
                            self.logger.info(f"Found .session file: {file_info}")
                        elif file_info.endswith('.json'):
                            json_data = z.read(file_info)
                            self.logger.info(f"Found .json file: {file_info}")
                    
                    if not session_data:
                        raise ValueError("No .session file found in archive")
            except zipfile.BadZipFile:
                raise ValueError("Invalid ZIP archive")

        # Парсим JSON если предоставлен
        device_info = {}
        if json_data:
            try:
                device_info = json.loads(json_data.decode('utf-8'))
                self.logger.info("Parsed device info from JSON")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON file: {e}, using defaults")

        # Получаем или создаем credentials
        telegram_credentials, _ = await TelegramCredentials.get_or_create(
            api_id=device_info.get('api_id') or TelegramClientConfig.API_ID,
            api_hash=device_info.get('api_hash') or TelegramClientConfig.API_HASH,
            device_model=device_info.get('device_model') or TelegramClientConfig.DEVICE_MODEL,
            system_version=device_info.get('system_version') or TelegramClientConfig.SYSTEM_VERSION,
            app_version=device_info.get('app_version') or TelegramClientConfig.APP_VERSION,
            lang_code=device_info.get('lang_code') or TelegramClientConfig.LANG_CODE,
            system_lang_code=device_info.get('system_lang_code') or TelegramClientConfig.SYSTEM_LANG_CODE,
            lang_pack=device_info.get('lang_pack') or TelegramClientConfig.LANG_PACK,
        )

        # Создаем нового клиента
        new_client = await Client.create(
            telegram_credentials=telegram_credentials, working=False
        )
        await new_client.save()

        # Конвертируем .session файл в StringSession и сохраняем в Redis
        try:
            # Создаем временный файл для загрузки сессии
            with tempfile.NamedTemporaryFile(suffix='.session', delete=False) as tmp_file:
                tmp_file.write(session_data)
                tmp_session_path = tmp_file.name
            
            try:
                # Загружаем сессию из файла и конвертируем в StringSession
                # Создаем временный клиент для конвертации сессии
                sqlite_session = SQLiteSession(tmp_session_path)
                temp_client = TelegramClient(
                    sqlite_session,
                    api_id=telegram_credentials.api_id,
                    api_hash=telegram_credentials.api_hash,
                )
                
                # Подключаемся и получаем строку сессии
                await temp_client.connect()
                if await temp_client.is_user_authorized():
                    # Конвертируем SQLiteSession в StringSession
                    string_session = StringSession()
                    # Копируем данные из SQLiteSession
                    string_session.set_dc(
                        sqlite_session.dc_id,
                        sqlite_session.server_address,
                        sqlite_session.port
                    )
                    if sqlite_session.auth_key:
                        string_session.auth_key = sqlite_session.auth_key
                    if hasattr(sqlite_session, 'takeout_id'):
                        string_session.takeout_id = sqlite_session.takeout_id
                    
                    session_string = string_session.save()
                    
                    # Сохраняем в Redis
                    redis = Redis(
                        host=self.__redis_config.host,
                        port=self.__redis_config.port,
                        db=self.__redis_config.db
                    )
                    await redis.set(
                        str(new_client.id), session_string.encode('utf-8')
                    )
                    await redis.close()
                    
                    self.logger.info(
                        f"Session saved to Redis for client {new_client.id}"
                    )
                else:
                    raise ValueError("Session is not authorized")
                
                await temp_client.disconnect()
                
            finally:
                # Удаляем временный файл
                if os.path.exists(tmp_session_path):
                    os.unlink(tmp_session_path)
            
            client = CustomClient(new_client, self.__redis_config)
            async with client:
                self.logger.info("Client activated")
                new_client.working = True
                await new_client.save()
                
        except Exception as e:
            self.logger.error(f"Failed to add client: {e}")
            # Удаляем клиента если не удалось активировать
            await new_client.delete()
            raise
