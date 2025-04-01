import secrets
import string
from datetime import datetime
from http import HTTPStatus

from api.auth.auth import fastapi_users, current_active_user
from config import DAYS_TO_EXPIRE
from db.database import get_async_session
from db.models import Link
from db.models import User
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from .schemas import LinkRequest, LinkResponse, LinkStatsResponse, LinkDetailedResponse

alphabet = string.ascii_letters + string.digits

router = APIRouter(
    prefix="/links",
    tags=["Links"]
)

@router.post("/shorten", response_model=LinkResponse)
async def add_short_link(link_request: LinkRequest, expires_at: datetime = None, user_id: int = None, session: AsyncSession = Depends(get_async_session)):
    '''Создание короткой ссылки с помощью генерации уникального кода либо строки пользователя'''
    custom_alias = link_request.custom_alias
    custom_alias_set = custom_alias is not None

    request_dict = link_request.model_dump(exclude_unset=True)
    if custom_alias_set:
        request_dict["short_code"] = request_dict.pop("custom_alias")

    link = Link(**request_dict)
    link.expires_at = expires_at

    if custom_alias_set:
        query = select(func.count(Link.id)).filter_by(short_code=custom_alias, deleted=False)
        result = await session.execute(query)
        row_count = result.scalar()

        if row_count == 0:
            link.short_code = custom_alias
        elif row_count > 0:
            raise HTTPException(status_code=HTTPStatus.CONFLICT,
                                detail=f"Link with the short code {custom_alias} already exists")
        else:
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                                detail=f"Error occurred while checking the custom alias {custom_alias}")
    else:
        link.short_code = generate_short_code()

    if user_id:
        query = select(User).filter_by(id=user_id)
        result = await session.execute(query)
        user = result.scalar_one()
        link.user_id = user.id
        link.user = user

    session.add(link)
    await session.commit()
    return LinkResponse(original_url=link.original_url, short_code=link.short_code)

@router.get("/search", response_model=list[LinkResponse])
@cache(expire=60)
async def find_by(original_url: str, session: AsyncSession = Depends(get_async_session), request: Request = None):
    '''Поиск короткой ссылки по оригинальному URL'''
    try:
        query = select(Link).filter_by(original_url=original_url, deleted=False)
        result = await session.execute(query)
        links = result.scalars().all()

        return [LinkResponse(original_url=link.original_url, short_code=link.short_code) for link in links]

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while searching the links by original url {original_url}: {e}")


@router.get("/history_expired", response_model=list[LinkDetailedResponse])
async def get_history_of_expired_links(session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    '''Отображение истории всех истекших ссылок пользователя с информацией о них'''
    try:
        query = select(Link).filter(Link.user == user, Link.expires_at < datetime.now())
        result = await session.execute(query)
        links = result.scalars().all()

        links_responses = []
        for link in links:
            link_response = LinkDetailedResponse(original_url=link.original_url, short_code=link.short_code,
                                                 creation_date=link.creation_date, expires_at=link.expires_at,
                                                 clicks_count=link.clicks_count, deleted=link.deleted)

            if link.last_usage_at is not None:
                link_response.last_usage_at = link.last_usage_at

            links_responses.append(link_response)

        return links_responses

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while getting the history of expired links: {e}")

@router.get("/all", response_model=list[LinkDetailedResponse])
async def get_all_active_links(session: AsyncSession = Depends(get_async_session), user: User = Depends(current_active_user)):
    '''Получение всех активных коротких ссылок пользователя с информацией о них'''
    try:
        query = select(Link).filter(Link.user == user, Link.deleted == False)
        result = await session.execute(query)
        links = result.scalars().all()

        links_responses = []
        for link in links:
            link_response = LinkDetailedResponse(original_url=link.original_url, short_code=link.short_code,
                                                 creation_date=link.creation_date, clicks_count=link.clicks_count,
                                                 deleted=link.deleted)

            if link.expires_at is not None:
                link_response.expires_at = link.expires_at

            if link.last_usage_at is not None:
                link_response.last_usage_at = link.last_usage_at

            links_responses.append(link_response)

        return links_responses

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while getting the active links: {e}")

@router.get("/{short_code}", response_class=RedirectResponse)
async def get_link_by(short_code: str, session: AsyncSession = Depends(get_async_session), request: Request = None):
    '''Перенаправление на оригинальный URL по коду'''
    try:
        query = select(Link).filter_by(short_code=short_code, deleted=False)
        result = await session.execute(query)
        link = result.scalar_one()

        key = build_stats_cache_key(request)
        await FastAPICache.clear(key=key)

        link.clicks_count += 1
        link.last_usage_at = datetime.now()
        await session.commit()
        return link.original_url

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while getting the link by short code {short_code}: {e}")


@router.get("/{short_code}/stats", response_model=LinkStatsResponse)
@cache(expire=60)
async def get_link_stats_by(short_code: str, session: AsyncSession = Depends(get_async_session), request: Request = None):
    '''Получение статистики по короткой ссылке: даты создания, количества переходов и даты последнего использования'''
    try:
        query = select(Link).filter_by(short_code=short_code, deleted=False)
        result = await session.execute(query)
        link = result.scalar_one()
        link_stats_response = LinkStatsResponse(creation_date=link.creation_date, clicks_count=link.clicks_count)

        if link.last_usage_at is not None:
            link_stats_response.last_usage_at = link.last_usage_at

        return link_stats_response

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while getting statistics for the link by short code {short_code}: {e}")

@router.delete("/{short_code}")
async def remove_link(short_code: str, session: AsyncSession = Depends(get_async_session),
                      user: User = Depends(current_active_user),
                      request: Request = None):
    '''Удаление короткой ссылки'''
    try:
        query = select(Link).filter_by(short_code=short_code, deleted=False)
        result = await session.execute(query)
        link = result.scalar_one()

        if link.user != user:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="You are not authorized to perform this action")

        link.deleted = True

        key = build_stats_cache_key(request)
        await FastAPICache.clear(key=key)

        await session.commit()

        return f"Link with short code {short_code} has been removed"

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while removing the link by short code {short_code}: {e}")


@router.put("/{short_code}", response_model=LinkResponse)
async def update_short_link(short_code: str, session: AsyncSession = Depends(get_async_session),
                            user: User = Depends(current_active_user),
                            request: Request = None):
    '''Обновление кода короткой ссылки'''
    try:
        query = select(Link).filter_by(short_code=short_code, deleted=False)
        result = await session.execute(query)
        link = result.scalar_one()

        if link.user != user:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="You are not authorized to perform this action")

        new_short_code = generate_short_code()
        link.short_code = new_short_code

        key = build_stats_cache_key(request)
        await FastAPICache.clear(key=key)

        # session.add(link)
        await session.commit()
        return LinkResponse(original_url=link.original_url, short_code=link.short_code)

    except (BaseException, Exception) as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail=f"Error occurred while updating the link by short code {short_code}: {e}")


def generate_short_code() -> str:
    return "".join(secrets.choice(alphabet) for _ in range(5))

def build_stats_cache_key(request: Request) -> str:
    return "".join([
        "get",
        request.url.path + "/stats",
        repr(sorted(request.path_params.items())),
        repr(sorted(request.query_params.items()))
    ])
