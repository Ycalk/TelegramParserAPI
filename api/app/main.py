from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import parser
from .routers import public
from .routers import scheduler
from .config import ApiServiceConfig


app = FastAPI(title=ApiServiceConfig.PROJECT_NAME, version=ApiServiceConfig.VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(parser.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(public.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(scheduler.router, prefix=ApiServiceConfig.BASE_PREFIX)
