import logging
from shared_models.parser.get_channel_info import GetChannelInfoRequest, GetChannelInfoResponse


class Parser:
    def __init__(self) -> None:
        self.logger = logging.getLogger('parser')
    
    
    # Methods
    @staticmethod
    async def get_channel_info(ctx, request: GetChannelInfoRequest) -> GetChannelInfoResponse:
        self: Parser = ctx['Parser_instance']