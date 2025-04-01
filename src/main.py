from fastapi import FastAPI
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from api.auth.auth import auth_backend, fastapi_users
from api.auth.schemas import UserCreate, UserRead

from api.url_shortener.router import router as links_router
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from starlette.requests import Request
from starlette.responses import Response

def cache_key_builder(func,
                      namespace: str = "",
                      request: Request = None,
                      response: Response = None,
                      *args,
                      **kwargs):
    return "".join([
        request.method.lower(),
        request.url.path,
        repr(sorted(request.path_params.items())),
        repr(sorted(request.query_params.items()))
    ])

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url("redis://redis")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache",
                      key_builder=cache_key_builder)
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"]
)
app.include_router(links_router)
