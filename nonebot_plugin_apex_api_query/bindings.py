"""Per-user query preferences persisted in the localstore-backed ORM database."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from weakref import WeakValueDictionary

from nonebot.adapters import Bot, Event
from nonebot_plugin_orm import get_session
from sqlalchemy import delete, update

from .models import PlayerBinding

_locks: WeakValueDictionary[tuple[str, str], asyncio.Lock] = WeakValueDictionary()


def owner_key(bot: Bot, event: Event) -> tuple[str, str]:
    # Include the bot and underlying platform: bridged adapters can reuse IDs.
    scope = json.dumps([bot.adapter.get_name(), str(getattr(bot, 'platform', '') or ''), bot.self_id],
                       ensure_ascii=False, separators=(',', ':'))
    return scope, event.get_user_id()


def owner_lock(owner: tuple[str, str]) -> asyncio.Lock:
    if (lock := _locks.get(owner)) is None:
        lock = asyncio.Lock()
        _locks[owner] = lock
    return lock


async def get_binding(owner: tuple[str, str]) -> PlayerBinding | None:
    async with get_session() as session:
        return await session.get(PlayerBinding, owner)


# Caller holds owner_lock across API validation and this write.
async def save_binding(owner: tuple[str, str], uid: str, player_name: str, platform: str) -> None:
    async with get_session() as session:
        await session.merge(PlayerBinding(scope=owner[0], user_id=owner[1], uid=uid,
            player_name=player_name, platform=platform, updated_at=datetime.now(timezone.utc)))
        await session.commit()


async def delete_binding(owner: tuple[str, str]) -> bool:
    async with owner_lock(owner):
        async with get_session() as session:
            result = await session.execute(delete(PlayerBinding).where(
                PlayerBinding.scope == owner[0], PlayerBinding.user_id == owner[1]))
            await session.commit()
            return bool(result.rowcount)


async def refresh_binding_name(owner: tuple[str, str], uid: str, platform: str, name: str) -> None:
    # A slow query must not overwrite a different account bound in the meantime.
    async with owner_lock(owner):
        async with get_session() as session:
            await session.execute(update(PlayerBinding).where(
                PlayerBinding.scope == owner[0], PlayerBinding.user_id == owner[1],
                PlayerBinding.uid == uid, PlayerBinding.platform == platform,
            ).values(player_name=name, updated_at=datetime.now(timezone.utc)))
            await session.commit()
