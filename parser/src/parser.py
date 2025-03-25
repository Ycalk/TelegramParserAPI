import asyncio
from datetime import datetime, timedelta
from pytz import UTC
import logging
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types.messages import ChatFull
from telethon.tl import types
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse
from .telegram import Telegram
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError, InviteRequestSentError, InviteHashExpiredError, AuthKeyDuplicatedError, UserDeactivatedBanError, FloodWaitError
from shared_models.parser.errors import FloodWait, InvalidChannelLink, UserBan, CannotGetChannelInfo
from telethon.tl.functions.messages import ImportChatInviteRequest
from shared_models import Channel as ChannelInfo
from shared_models.parser.get_image import GetImageRequest, GetImageResponse
from telethon.tl.types import InputPhoto
from telethon.tl.types import Photo


class Parser:
    def __init__(self, telegram: Telegram) -> None:
        self.logger = logging.getLogger('parser')
        self.telegram = telegram
    
    async def get_channel_entity(self, activated_client: TelegramClient, entity) -> types.Channel:
        try:
            channel_entity = await activated_client.get_entity(entity)
        except ValueError:
            try:
                channel_entity = await self.join_private_channel(activated_client, entity) # type: ignore
            except InviteHashExpiredError as e:
                raise InvalidChannelLink(entity, str(e))
            except FloodWaitError as e:
                raise FloodWait(e.seconds)
            except UserDeactivatedBanError as e:
                raise UserBan(str(e))
        if not channel_entity:
            raise CannotGetChannelInfo(entity)
        return channel_entity # type: ignore
    
    async def join_private_channel(self, activated_client: TelegramClient, url: str):
        if url.startswith('https://t.me/+'):
            url_suffix = url.removeprefix('https://t.me/+')
        else:
            url_suffix = url.removeprefix('https://t.me/joinchat/')
        try:
            await activated_client(ImportChatInviteRequest(url_suffix))
        except UserAlreadyParticipantError:
            return await activated_client.get_entity(url)
        except InviteRequestSentError:
            counter = 0
            while True:
                counter += 1
                if counter > 3:
                    break
                try:
                    return await activated_client.get_entity(url)
                except ValueError:
                    await asyncio.sleep(10)
                    continue
        return await activated_client.get_entity(url)
    
    async def get_channel(self, client, entity: types.Channel, url: str) -> ChannelInfo:
        channel_info : ChatFull = await client(GetFullChannelRequest(channel=entity))  # type: ignore
        if url.startswith('https://'):
            url = url.removeprefix('https://')
        elif url.startswith('http://'):
            url = url.removeprefix('http://')
        
        return ChannelInfo(
            channel_id=channel_info.full_chat.id,
            link=url,
            name=entity.title,
            description=channel_info.full_chat.about,
            subscribers=channel_info.full_chat.participants_count, # type: ignore
            views=await self.__get_posts_views(client, entity),
        )
    
    async def __get_posts_views(self, client: TelegramClient, entity: types.Channel) -> int:
        start_date = datetime.now(UTC)
        end_date = start_date - timedelta(hours=24)
        
        views = 0
        async for post in client.iter_messages(entity, offset_date=start_date):
            post: types.Message
            post_date = post.date.replace(tzinfo=UTC) if post.date.tzinfo is None else post.date # type: ignore
            if post_date.timestamp() < end_date.timestamp(): # type: ignore
                break
            views += post.views or 0
            
        return views
    
    # Cron
    @staticmethod
    async def update_client(ctx):
        self: Parser = ctx['Parser_instance']
        await self.telegram.update_client()
    
    
    # Methods
    @staticmethod
    async def get_channel_info(ctx, request: GetChannelInfoRequest) -> GetChannelInfoResponse:
        self: Parser = ctx['Parser_instance']
        client = await self.telegram.get_client()
        
        async with client:
            entity = await self.get_channel_entity(client, request.channel_link)
            if request.get_logo:
                try:
                    logo = await client.download_profile_photo(entity, file=bytes) # type: ignore
                except Exception:
                    logo = None
            else:
                logo = None
            return GetChannelInfoResponse(
                channel=await self.get_channel(client, entity, request.channel_link),
                logo=logo # type: ignore
            )