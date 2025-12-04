import asyncio
import logging
from datetime import datetime, timedelta
from .telegram.models import Client

from pytz import UTC
from shared_models.message import Message as MessageSharedModel
from shared_models.message import MessageMedia, MessageMediaType
from shared_models.parser.errors import (
    CannotGetChannelInfo,
    FloodWait,
    InvalidChannelLink,
    UserBan,
)
from shared_models.parser.get_channel_info import (
    GetChannelInfoRequest,
    GetChannelInfoResponse,
)
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import (
    FloodWaitError,
    InviteHashExpiredError,
    InviteRequestSentError,
    UserAlreadyParticipantError,
    UserDeactivatedBanError,
)
from telethon.tl import types
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types.messages import ChatFull

from shared_models import Channel as ChannelInfo

from .config import Config
from .telegram import Telegram


class Parser:
    def __init__(self, telegram: Telegram) -> None:
        self.logger = logging.getLogger("parser")
        self.telegram = telegram

    async def get_channel_entity(
        self, activated_client: TelegramClient, link
    ) -> types.Channel:
        try:
            channel_entity = await activated_client.get_entity(link)
        except ValueError:
            try:
                channel_entity = await self.join_private_channel(activated_client, link)  # type: ignore
            except InviteHashExpiredError as e:
                raise InvalidChannelLink(link, str(e))
            except FloodWaitError as e:
                raise FloodWait(e.seconds)
            except UserDeactivatedBanError as e:
                raise UserBan(str(e))
        except FloodWaitError as e:
            raise FloodWait(e.seconds)
        except Exception as e:
            raise InvalidChannelLink(link, str(e))
        if not channel_entity:
            raise CannotGetChannelInfo(link)
        return channel_entity  # type: ignore

    async def join_private_channel(self, activated_client: TelegramClient, url: str):
        invite_hash = url.split("/")[-1]
        if invite_hash.startswith("+"):
            invite_hash = invite_hash[1:]
        try:
            await activated_client(ImportChatInviteRequest(invite_hash))  # type: ignore
        except UserAlreadyParticipantError:
            return await activated_client.get_entity(url)
        except InviteRequestSentError:
            for _ in range(3):
                await asyncio.sleep(10)
                try:
                    return await activated_client.get_entity(url)
                except ValueError:
                    continue
        return await activated_client.get_entity(url)

    async def get_channel(
        self, client, entity: types.Channel, url: str, posts: list[MessageSharedModel]
    ) -> ChannelInfo:
        channel_info: ChatFull = await client(GetFullChannelRequest(channel=entity))  # type: ignore
        if url.startswith("https://"):
            url = url.removeprefix("https://")
        elif url.startswith("http://"):
            url = url.removeprefix("http://")

        views = (0, 0)
        if len(posts) > 0:
            views = (posts[0].date, posts[0].views if posts[0].views else 0)
            for post in posts:
                if post.date < views[0] and post.views and post.views != 0:
                    views = (post.date, post.views)
        return ChannelInfo(
            channel_id=channel_info.full_chat.id,
            link=url,
            name=entity.title,
            description=channel_info.full_chat.about,
            subscribers=channel_info.full_chat.participants_count,  # type: ignore
            views=views[1],
            posts_count=len(posts),
        )

    async def __get_posts(
        self,
        client: TelegramClient,
        entity: types.Channel,
        download_media: bool = False,
    ) -> list[MessageSharedModel]:
        start_date = datetime.now(UTC)
        end_date = start_date - timedelta(hours=24)

        grouped_messages: dict[int, MessageSharedModel] = {}

        async for post in client.iter_messages(entity, offset_date=start_date):  # type: ignore
            post: types.Message
            post_date = (
                post.date.replace(tzinfo=UTC) if post.date.tzinfo is None else post.date  # type: ignore
            )  # type: ignore

            if post_date.timestamp() < end_date.timestamp():  # type: ignore
                break

            group_key = post.grouped_id if post.grouped_id else post.id

            if group_key not in grouped_messages:
                new_message = MessageSharedModel(
                    message_id=post.id,
                    date=post_date.timestamp(),  # type: ignore
                    text=post.message or "",
                    views=post.views,
                )
                grouped_messages[group_key] = new_message
            else:
                existing_message = grouped_messages[group_key]
                if post.message and not existing_message.text:
                    existing_message.text = post.message

                if post.views and (
                    not existing_message.views or post.views > existing_message.views
                ):
                    existing_message.views = post.views

            # Обрабатываем медиа
            if (
                isinstance(
                    post.media, (types.MessageMediaPhoto, types.MessageMediaDocument)
                )
                and len(grouped_messages) <= Config.POSTS_COLLECTION_COUNT
            ):
                data = None
                if download_media:
                    data = await client.download_media(post, file=bytes, thumb=-1)  # type: ignore

                message_to_update = grouped_messages[group_key]

                if isinstance(post.media, types.MessageMediaDocument):
                    message_to_update.media.append(
                        MessageMedia(
                            media_type=MessageMediaType.DOCUMENT,
                            data=data,  # type: ignore
                            mime_type=getattr(post.media.document, "mime_type", ""),
                            id=None,
                        )
                    )
                elif isinstance(post.media, types.MessageMediaPhoto):
                    message_to_update.media.append(
                        MessageMedia(
                            media_type=MessageMediaType.PHOTO,
                            data=data,  # type: ignore
                            mime_type="image/jpeg",
                            id=None,
                        )
                    )

        return list(grouped_messages.values())[: Config.POSTS_COLLECTION_COUNT]

    # Methods
    @staticmethod
    async def get_channel_info(
        ctx, request: GetChannelInfoRequest, retry_count: int = 0
    ) -> GetChannelInfoResponse:
        self: Parser = ctx["Parser_instance"]

        # Пробуем получить рабочего клиента с повторными попытками
        max_client_retries = 3
        client_retry = 0
        last_client_error = None
        
        while client_retry < max_client_retries:
            try:
                non_active_client = await self.telegram.get_client()
                async with non_active_client as client:
                    try:
                        return await asyncio.wait_for(
                            self._get_channel_info_internal(client, request),
                            timeout=60
                        )
                    except asyncio.TimeoutError:
                        return await self.get_channel_info(
                                ctx, request, retry_count + 1
                            )
                    except FloodWait as e:
                        client_id = non_active_client._client.id
                        client_db = await Client.get(id=client_id)
                        client_db.working = False
                        await client_db.save()
                        await self.telegram.redis.enqueue_job(
                            "Telegram.enable_client",
                            client_id,
                            _defer_by=e.seconds
                        )
                        if retry_count < 3:
                            wait_seconds = e.seconds
                            attempt = retry_count + 1
                            self.logger.warning(
                                f"FloodWaitError: waiting {wait_seconds}s "
                                f"(attempt {attempt}/3)"
                            )
                            return await self.get_channel_info(
                                ctx, request, retry_count + 1
                            )
                        else:
                            self.logger.error(
                                f"FloodWaitError: max retries (3) reached. "
                                f"Last wait: {e.seconds}s"
                            )
                            raise FloodWait(e.seconds)
            except ValueError as e:
                error_msg = str(e)
                if "Cannot start client" in error_msg:
                    # Клиент не смог запуститься, пробуем следующий
                    client_retry += 1
                    last_client_error = e
                    self.logger.warning(
                        f"Client failed to start (attempt {client_retry}/"
                        f"{max_client_retries}): {error_msg}. "
                        "Trying next client..."
                    )
                    if client_retry >= max_client_retries:
                        self.logger.error(
                            f"All client retries exhausted. "
                            f"Last error: {error_msg}"
                        )
                        raise ValueError(
                            f"Failed to start any client after "
                            f"{max_client_retries} attempts: {error_msg}"
                        )
                    continue
                else:
                    # Другая ошибка, пробрасываем дальше
                    raise
            except Exception:
                # Другие ошибки пробрасываем дальше
                raise

        # Если дошли сюда - все попытки исчерпаны
        raise ValueError(
            f"Failed to get working client. "
            f"Last error: {last_client_error}"
        )

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

    async def _get_channel_info_internal(
        self, client: TelegramClient, request: GetChannelInfoRequest
    ) -> GetChannelInfoResponse:
        entity = await self.get_channel_entity(client, request.channel_link)
        if request.get_logo:
            try:
                logo = await client.download_profile_photo(entity, file=bytes)  # type: ignore
            except Exception:
                logo = None
        else:
            logo = None
        posts = await self.__get_posts(client, entity, request.download_message_media)
        return GetChannelInfoResponse(
            channel=await self.get_channel(client, entity, request.channel_link, posts),
            logo=logo,  # type: ignore
            messages=posts,
        )
