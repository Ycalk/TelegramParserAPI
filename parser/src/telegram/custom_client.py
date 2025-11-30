import os
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

import socks
from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.sessions import StringSession
from tortoise.expressions import F

from .models import Client, TelegramCredentials


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int


class CustomClient:
    def __init__(self, client: Client, redis_config: RedisConfig) -> None:
        self._redis = Redis(
            host=redis_config.host, port=redis_config.port, db=redis_config.db
        )
        self._client = client
        self._t_client: Optional[TelegramClient] = None
        self._session: Optional[StringSession] = None

    @staticmethod
    def _get_proxy() -> Optional[Tuple]:
        """Получает прокси из переменных окружения.

        Использует SOCKS5 для прокси с аутентификацией,
        так как PySocks не поддерживает HTTP прокси с auth.
        """
        # Определяем тип прокси (по умолчанию SOCKS5)
        proxy_type = os.getenv("PROXY_TYPE", "socks5").lower()

        # Вариант 1: Полная строка прокси
        proxy_url = os.getenv("PROXY")
        if proxy_url:
            try:
                parsed = urlparse(proxy_url)
                if parsed.hostname and parsed.port:
                    username = parsed.username or ""
                    password = parsed.password or ""

                    # Определяем тип из схемы URL или переменной
                    scheme = parsed.scheme.lower()
                    if scheme == "socks5" or (
                        scheme == "http" and proxy_type == "socks5"
                    ):
                        # SOCKS5 с аутентификацией
                        return (
                            socks.SOCKS5,
                            parsed.hostname,
                            parsed.port,
                            username,
                            password,
                        )
                    elif scheme == "http" and not username:
                        # HTTP без аутентификации
                        return (socks.HTTP, parsed.hostname, parsed.port)
                    elif scheme == "http" and username:
                        # HTTP с аутентификацией - используем SOCKS5
                        return (
                            socks.SOCKS5,
                            parsed.hostname,
                            parsed.port,
                            username,
                            password,
                        )
            except Exception:
                pass

        # Вариант 2: Отдельные переменные
        proxy_host = os.getenv("PROXY_HOST")
        proxy_port = os.getenv("PROXY_PORT")
        if proxy_host and proxy_port:
            try:
                username = os.getenv("PROXY_USERNAME", "")
                password = os.getenv("PROXY_PASSWORD", "")

                if proxy_type == "socks5" or (username and password):
                    # SOCKS5 с аутентификацией
                    return (
                        socks.SOCKS5,
                        proxy_host,
                        int(proxy_port),
                        username,
                        password,
                    )
                else:
                    # HTTP без аутентификации
                    return (socks.HTTP, proxy_host, int(proxy_port))
            except ValueError:
                pass

        return None

    async def mark_as_ban(self) -> None:
        # WARNING: Uncomment in production if commented
        self._client.working = False
        await self._client.save()

    async def __aenter__(self) -> TelegramClient:
        session_str = await self._redis.get(str(self._client.id))

        if session_str:
            self._session = StringSession(session_str.decode("utf-8"))
            credentials: TelegramCredentials = (
                await self._client.telegram_credentials
            )
            proxy = self._get_proxy()
            t_client = TelegramClient(
                auto_reconnect=False,
                session=self._session,
                api_id=credentials.api_id,
                api_hash=credentials.api_hash,
                device_model=credentials.device_model,
                system_version=credentials.system_version,
                app_version=credentials.app_version,
                lang_code=credentials.lang_code,
                system_lang_code=credentials.system_lang_code,
                proxy=proxy,
            )
            try:
                await t_client.start()  # type: ignore
                await Client.filter(id=self._client.id).update(
                    users_count=F("users_count") + 1
                )
                self._t_client = t_client
                return t_client
            except Exception as e:
                await self.mark_as_ban()
                raise ValueError(f"Cannot start client: {str(e)}")
        else:
            # Сессия не найдена в Redis
            await self.mark_as_ban()
            raise ValueError(
                "Session not found in Redis for this client. "
                "Please add client with .session file first."
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._redis.set(
                str(self._client.id), self._session.save().encode("utf-8")
            )
        if self._t_client:
            # Отключаем клиент перед обновлением счетчика
            await self._t_client.disconnect()
            await Client.filter(id=self._client.id).update(
                users_count=F("users_count") - 1
            )
        # Закрываем соединение с Redis
        await self._redis.close()
