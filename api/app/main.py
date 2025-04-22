from fastapi import FastAPI
from app.routers import parser
from app.routers import public
from app.routers import scheduler
from .config import ApiServiceConfig


app = FastAPI(title=ApiServiceConfig.PROJECT_NAME, version=ApiServiceConfig.VERSION)
app.include_router(parser.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(public.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(scheduler.router, prefix=ApiServiceConfig.BASE_PREFIX)
