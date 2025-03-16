import logging
from os import link
from tortoise import Tortoise
from .config import TORTOISE_ORM
from shared_models import Channel as ChannelSharedModel
from shared_models.database.update_or_create_channel import UpdateOrCreateChannelResponse
from .models import Channel, ChannelStatistics


class Database:
    def __init__(self) -> None:
        self.logging = logging.getLogger("database")
        
    async def connect(self):
        self.logging.info("Initializing database")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        self.logging.info("Database initialized")
    
    async def close(self):
        await Tortoise.close_connections()
        self.logging.info("Database closed")
    
    
    # Methods
    @staticmethod
    async def update_or_create_channel(ctx, channel: ChannelSharedModel) -> UpdateOrCreateChannelResponse:
        self: Database = ctx['Database_instance']
        self.logging.info(f"Updating or creating channel {channel.name}")
        result, created = await Channel.update_or_create(
            id=channel.channel_id,
            link=channel.link,
            defaults={
                'name': channel.name,
                'description': channel.description,
                'logo_id': channel.channel_photo_id
            }
        )
        await ChannelStatistics.create(
            channel=result,
            subscribers=channel.subscribers,
            views_24h=channel.views,
        )
        
        return UpdateOrCreateChannelResponse(record_created=created)