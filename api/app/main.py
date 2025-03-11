from fastapi import FastAPI
from app.routers import parser
from .config import ApiServiceConfig


app = FastAPI()
app.include_router(parser.router, prefix=ApiServiceConfig.BASE_PREFIX)
