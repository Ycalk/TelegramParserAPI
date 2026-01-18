import logging
import os
import json
import random
import tempfile
from arq import create_pool
from arq.connections import RedisSettings
import zipfile
import io
from .custom_client import CustomClient, RedisConfig
from tortoise import Tortoise
from tortoise.expressions import F
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
        self.redis = None

    async def init_redis(self):
        """Инициализирует ARQ Redis пул для telegram очереди"""
        if not self.redis:
            self.redis = await create_pool(
                RedisSettings(
                    self.__redis_config.host,
                    self.__redis_config.port
                ),
                default_queue_name=os.getenv("TELEGRAM_QUEUE_NAME", "telegram")
            )

    async def init_database(self) -> None:
        self.logger.info("Initializing database")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        self.logger.info("Database initialized")

    async def close(self) -> None:
        await Tortoise.close_connections()

    async def get_client(self) -> CustomClient:
        """Получает рабочего клиента с блокировкой через Redis lock + users_count"""
        # Освобождаем зависшие блокировки (для нерабочих клиентов)
        await Client.filter(
            working=False, users_count__gt=0
        ).update(users_count=0)

        # Получаем всех рабочих клиентов
        clients = await Client.filter(working=True).all()
        clients_list = list(clients)
        random.shuffle(clients_list)

        if not clients:
            self.logger.error("No working clients found in database")
            raise ValueError("No working clients found")

        # Создаем Redis для блокировки
        redis_lock = Redis(
            host=self.__redis_config.host,
            port=self.__redis_config.port,
            db=0  # Используем отдельную БД для локов
        )
        
        try:
            # Пытаемся заблокировать клиента атомарно
            for client in clients_list:
                lock_key = f"client_lock:{client.id}"
                
                # Пытаемся получить Redis lock (атомарная операция)
                # NX - set if not exists, EX - expire in seconds
                lock_acquired = await redis_lock.set(
                    lock_key, 
                    "1", 
                    nx=True,  # Только если ключ не существует
                    ex=120    # TTL 120 секунд (на случай сбоя)
                )
                
                if not lock_acquired:
                    # Лок уже занят, пробуем следующего клиента
                    self.logger.debug(
                        f"Client ID {client.id} is locked in Redis, trying next..."
                    )
                    continue
                
                # Redis lock получен, теперь пытаемся обновить database
                try:
                    # Атомарная попытка увеличить users_count с 0 до 1
                    updated = await Client.filter(
                        id=client.id,
                        users_count=0  # Проверяем, что счетчик = 0
                    ).update(
                        users_count=F("users_count") + 1
                    )

                    if updated > 0:
                        # Успешно заблокировали (увеличили с 0 до 1)
                        await client.refresh_from_db()
                        self.logger.info(
                            f"Locked client ID {client.id} "
                            f"(users_count={client.users_count})"
                        )
                        custom_client = CustomClient(client, self.__redis_config)
                        return custom_client
                    else:
                        # Database блокировка не удалась, освобождаем Redis lock
                        await redis_lock.delete(lock_key)
                        self.logger.debug(
                            f"Client ID {client.id} is already in use in DB "
                            f"(users_count={client.users_count}), trying next..."
                        )
                        continue
                except Exception as e:
                    # При ошибке освобождаем Redis lock
                    await redis_lock.delete(lock_key)
                    raise

            # Если все клиенты заняты
            self.logger.error(
                f"All {len(clients)} clients are in use (users_count > 0)"
            )
            raise ValueError("No available clients (all are in use)")
        finally:
            await redis_lock.close()

    @staticmethod
    async def enable_client(ctx, client_id: int) -> None:
        """Включает клиента обратно после FloodWait"""
        self: Telegram = ctx["Telegram_instance"]
        try:
            client = await Client.get(id=client_id)
            client.working = True
            await client.save()
            self.logger.info(f"Client ID {client_id} enabled after FloodWait")
        except Exception as e:
            self.logger.error(f"Failed to enable client ID {client_id}: {e}")

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
                # Получаем прокси из переменных окружения
                proxy = CustomClient._get_proxy()
                temp_client = TelegramClient(
                    sqlite_session,
                    api_id=telegram_credentials.api_id,
                    api_hash=telegram_credentials.api_hash,
                    proxy=proxy,
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
