from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from weakref import WeakValueDictionary

import httpx
from nonebot import get_driver, require
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

os.environ.setdefault("ALEMBIC_STARTUP_CHECK", "false")

require("nonebot_plugin_localstore")
require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")
require("nonebot_plugin_htmlrender")

from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Option,
    Subcommand,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_htmlrender import render_template
from nonebot_plugin_localstore import get_plugin_data_dir
from nonebot_plugin_orm import get_session
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from .config import config
from .models import PlayerStats
from .bindings import delete_binding, get_binding, owner_key, owner_lock, refresh_binding_name, save_binding

_SERVER_SECTIONS: dict[str, str] = {
    "Origin 登录": "Origin_login",
    "EA Novafusion": "EA_novafusion",
    "EA 账户": "EA_accounts",
    "Apex 跨平台验证": "ApexOauth_Crossplay",
    "ALS 服务状态": "selfCoreTest",
    "其他平台": "otherPlatforms",
}
_SERVER_REGIONS: dict[str, str] = {
    "欧洲西部": "EU-West",
    "欧洲东部": "EU-East",
    "美国西部": "US-West",
    "美国中部": "US-Central",
    "美国东部": "US-East",
    "南美洲": "SouthAmerica",
    "亚洲": "Asia",
}
_SELF_CORE_TESTS: dict[str, str] = {
    "网站状态": "Status-website",
    "数据查询 API": "Stats-API",
    "Overflow 节点 #1": "Overflow-#1",
    "Overflow 节点 #2": "Overflow-#2",
    "Origin API": "Origin-API",
    "Playstation API": "Playstation-API",
    "Xbox API": "Xbox-API",
}
_OTHER_PLATFORMS: dict[str, str] = {
    "Playstation Network": "Playstation-Network",
    "Xbox Live": "Xbox-Live",
}


logger = logging.getLogger(__name__)

_api_key_available: bool | None = None

driver = get_driver()
__plugin_meta__ = PluginMetadata(
    name="Apex API Query",
    description="Apex Legends API 查询插件",
    usage="/apex 或 .apex",
    type="application",
    homepage="https://github.com/H-xiaoH/nonebot-plugin-apex-api-query",
    config=config.__class__,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra={"author": "H-xiaoH <a412454922@gmail.com>"},
)

def convert(name: Any) -> Any:
    if name is not None and not isinstance(name, (str, int, float)):
        return None
    if not hasattr(convert, "_translations"):
        path = Path(__file__).parent / "data" / "translations.json"
        with path.open(encoding="utf-8") as f:
            convert._translations = json.load(f)  # type: ignore[attr-defined]
    if isinstance(name, (int, float)):
        return convert._translations.get(str(name), name)  # type: ignore[attr-defined]
    return convert._translations.get(name, name)  # type: ignore[attr-defined]


class AsyncTTLCache:
    """异步 TTL 缓存，asyncio.Lock 保证并发安全。"""

    def __init__(self, ttl: int = 300) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Task[Any]] = {}

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, val = entry
            if time.monotonic() - ts < self._ttl:
                return val
            del self._store[key]
            return None

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = (time.monotonic(), value)

    async def get_or_fetch(self, key: str, fetch: Callable[[], Awaitable[Any]]) -> Any:
        if (value := await self.get(key)) is not None:
            return value
        if key not in self._pending:
            async def load() -> Any:
                try:
                    value = await fetch()
                    await self.set(key, value)
                    return value
                finally:
                    self._pending.pop(key, None)
            task = asyncio.create_task(load())
            # Retrieve failures even if every waiting caller was cancelled.
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
            self._pending[key] = task
        return await asyncio.shield(self._pending[key])

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


_map_rotation_cache = AsyncTTLCache(ttl=60)
_server_status_cache = AsyncTTLCache(ttl=30)
_predator_cache = AsyncTTLCache(ttl=300)
_missing_image_cache = AsyncTTLCache(ttl=3600)
_player_locks: WeakValueDictionary[tuple[str, str], asyncio.Lock] = WeakValueDictionary()


def _player_lock(uid: str, platform: str) -> asyncio.Lock:
    key = (uid, platform)
    if (lock := _player_locks.get(key)) is None:
        lock = asyncio.Lock()
        _player_locks[key] = lock
    return lock


@dataclass
class PlayerStatsData:
    level: int
    rank_score: int
    rank_name: str
    rank_div: int | None
    prestige: int | None = None


async def get_latest_record(uid: str, platform: str) -> PlayerStats | None:
    async with get_session() as session:
        result = await session.execute(
            select(PlayerStats)
            .where(PlayerStats.uid == uid, PlayerStats.platform == platform)
            .order_by(desc(PlayerStats.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


async def save_record(
    uid: str, player_name: str, platform: str, stats: PlayerStatsData,
    *, observed_at: datetime | None = None,
) -> None:
    async with get_session() as session:
        record = PlayerStats(
            uid=uid,
            player_name=player_name,
            platform=platform,
            level=stats.level,
            prestige=stats.prestige,
            rank_score=stats.rank_score,
            rank_name=stats.rank_name,
            rank_div=stats.rank_div,
            created_at=observed_at or datetime.now(tz=timezone.utc),
        )
        session.add(record)
        await session.commit()


def _format_rank(name: str, division: int | None) -> str:
    undivided = ("Master", "Apex Predator", "Unranked")
    if name in undivided or name in {convert(key) for key in undivided}:
        return name
    return f"{name} {division}" if division else name


def format_comparison(
    current: PlayerStatsData, previous: PlayerStatsData,
) -> dict[str, str]:
    changes: dict[str, str] = {}
    # Legacy rows have no prestige; do not infer a cumulative level for them.
    level_diff = 0
    if current.prestige is not None and previous.prestige is not None:
        level_diff = (current.prestige - previous.prestige) * 500 + current.level - previous.level
    if level_diff > 0:
        changes["等级"] = f"(↑{level_diff})"
    elif level_diff < 0:
        changes["等级"] = f"(↓{abs(level_diff)})"

    score_diff = current.rank_score - previous.rank_score
    if score_diff > 0:
        changes["大逃杀分数"] = f"(↑{score_diff})"
    elif score_diff < 0:
        changes["大逃杀分数"] = f"(↓{abs(score_diff)})"

    prev_rank = _format_rank(previous.rank_name, previous.rank_div)
    curr_rank = _format_rank(current.rank_name, current.rank_div)
    if prev_rank != curr_rank:
        changes["大逃杀段位"] = f"({prev_rank})"

    return changes


def format_map_data(map_data: dict[str, Any], mode_name: str) -> str:
    current = _mapping(map_data.get("current"))
    next_map = _mapping(map_data.get("next"))
    return (
        f"{mode_name}:\n"
        f"当前地图: {convert(current.get('map'))}\n"
        f"下一张: {convert(next_map.get('map'))}\n"
        f"剩余时间: {convert(current.get('remainingTimer'))}\n\n"
    )


def format_server_status(sections: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for section in sections:
        lines.append(f"{section['section_name']}:")
        lines.extend(
            f"{row['name']}: {convert(row['status'])}"
            for row in section["rows"]
        )
        lines.append("")
    lines.append("Data from apexlegendsstatus.com")
    return "\n".join(lines)


def format_predator(data: dict[str, Any]) -> str:
    platform_display: dict[str, str] = {
        "PC": "PC 端",
        "PS4": "PS4/5 端",
        "X1": "Xbox 端",
        "SWITCH": "Switch 端",
    }
    lines: list[str] = ["大逃杀:"]
    for pk, pn in platform_display.items():
        if pk not in data:
            continue
        info = data[pk]
        lines.append(
            f"{pn}:\n"
            f"顶尖猎杀者人数: {info['found_rank'] if info['found_rank'] is not None else '未知'}\n"
            f"顶尖猎杀者分数: {info['val'] if info['val'] is not None else '未知'}\n"
            f"顶尖猎杀者UID: {info['uid'] or '未知'}\n"
            "大师和顶尖猎杀者人数: "
            f"{info['total_masters'] if info['total_masters'] is not None else '未知'}"
        )
    return "\n\n".join(lines)


def format_player_stats(player_info: dict[str, Any]) -> str:
    return "玩家信息:\n" + "\n".join(
        f"{key}: {value}"
        for key, value in player_info.items()
        if value is not None
    )


class ApexAPIError(Exception):
    pass


async def query_apex_api(
    server: str,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> httpx.Response:
    payload: dict[str, Any] = {}
    if params:
        payload.update(params)
    base = base_url or config.apex_api_url
    async with httpx.AsyncClient(
        headers={"Authorization": config.apex_api_key, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    ) as client:
        return await client.get(f"{base}/{server}", params=payload, timeout=30)


async def _fetch(
    endpoint: str,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    global _api_key_available
    if not config.apex_api_key:
        _api_key_available = False
        logger.warning("API密钥不可用：未配置 APEX_API_KEY")
        raise ApexAPIError("API密钥不可用")
    try:
        response = await query_apex_api(endpoint, params, base_url)
    except httpx.HTTPError as e:
        logger.warning("API %s network request failed", endpoint)
        raise ApexAPIError("查询失败: 网络请求错误") from e  # noqa: TRY003
    if response.status_code in (401, 403):
        _api_key_available = False
        logger.warning("API密钥不可用：认证失败（HTTP %d）", response.status_code)
        raise ApexAPIError("API密钥不可用")
    if response.status_code != 200:
        logger.warning("API %s returned HTTP %d", endpoint, response.status_code)
        raise ApexAPIError(f"查询失败: API 返回 HTTP {response.status_code}，请稍后重试")
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logger.exception("Failed to parse %s response", endpoint)
        raise ApexAPIError("查询失败: API 返回数据格式错误") from e  # noqa: TRY003
    if not isinstance(data, dict):
        raise ApexAPIError("查询失败: API 返回数据结构错误")
    _api_key_available = True
    return data


@driver.on_startup
async def check_api_key() -> None:
    try:
        await _fetch("servers")
    except ApexAPIError:
        if _api_key_available is not False:
            logger.warning("暂时无法检查 API 密钥，请稍后重试查询")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return None


def _validate_player_payload(data: dict[str, Any]) -> dict[str, Any]:
    global_data = dict(_mapping(data.get("global")))
    rank = dict(_mapping(global_data.get("rank")))
    uid = global_data.get("uid")
    level = _nonnegative_int(global_data.get("level"))
    score = _nonnegative_int(rank.get("rankScore"))
    rank_name = rank.get("rankName")
    division = _nonnegative_int(rank.get("rankDiv"))
    divided = isinstance(rank_name, str) and rank_name in {"Rookie", "Bronze", "Silver", "Gold", "Platinum", "Diamond"}
    if (
        not isinstance(uid, (str, int)) or isinstance(uid, bool) or not str(uid).strip()
        or level is None or score is None
        or not isinstance(rank_name, str) or not rank_name.strip()
        or (divided and division not in (1, 2, 3, 4))
    ):
        raise ApexAPIError("查询失败: 玩家数据不完整，请稍后重试")
    global_data.update(level=level, rank={**rank, "rankScore": score, "rankDiv": division})
    global_data["bans"] = _mapping(global_data.get("bans"))
    global_data["battlepass"] = _mapping(global_data.get("battlepass"))
    legends = _mapping(data.get("legends"))
    selected = dict(_mapping(legends.get("selected")))
    selected["gameInfo"] = _mapping(selected.get("gameInfo"))
    selected["ImgAssets"] = _mapping(selected.get("ImgAssets"))
    if not isinstance(selected.get("data"), list):
        selected["data"] = []
    return {**data, "global": global_data, "realtime": _mapping(data.get("realtime")),
            "legends": {**legends, "selected": selected}}


def _player_details(response_data: dict[str, Any]) -> dict[str, Any]:
    """Keep optional account fields and equipped trackers in their API scope."""
    global_data = response_data.get("global") or {}
    rank = global_data.get("rank") or {}
    selected = (response_data.get("legends") or {}).get("selected") or {}
    game_info = selected.get("gameInfo") or {}
    assets = selected.get("ImgAssets") or {}
    percentile = rank.get("ALStopPercentGlobal")
    if not isinstance(percentile, (int, float)) or not 0 <= percentile <= 100:
        percentile = None
    season = rank.get("rankedSeason") or ""
    if not isinstance(season, str):
        season = ""
    if match := re.fullmatch(r"br_ranked_s(\d+)_s(\d+)", season):
        season = f"S{match[1]} · 第 {match[2]} 赛段"
    trackers = []
    for tracker in selected.get("data") or []:
        if not isinstance(tracker, dict):
            continue
        value = tracker.get("value")
        name = tracker.get("name") or tracker.get("key")
        if isinstance(name, str) and name and isinstance(value, (int, float)) and value >= 0:
            trackers.append({"name": convert(name), "value": value})
    return {
        "prestige": _nonnegative_int(global_data.get("levelPrestige")),
        "battlepass_level": (global_data.get("battlepass") or {}).get("level"),
        "ranked_season": season,
        "global_rank_pct": percentile,
        "legend_banner": assets.get("banner") or "",
        "legend_key": selected.get("LegendName") or (response_data.get("realtime") or {}).get("selectedLegend") or "",
        "legend_skin": game_info.get("skin") or "",
        "legend_skin_rarity": game_info.get("skinRarity") or "",
        "tracker_legend": convert(selected.get("LegendName") or ""),
        "trackers": trackers,
    }


def _checked_platform(platform: str) -> str:
    platform = platform.strip().upper()
    if platform not in ("PC", "PS4", "X1", "SWITCH"):
        raise ApexAPIError("平台参数错误，请输入 PC、PS4、X1、SWITCH")
    return platform


def _checked_uid(uid: str) -> str:
    uid = uid.strip()
    if not (1 <= len(uid) <= 32 and uid.isascii() and uid.isdecimal() and uid.strip("0")):
        raise ApexAPIError("UID 格式错误，请输入有效的数字 UID")
    return uid.lstrip("0")


async def get_player_stats(
    player_name: str, platform: str = "PC", *, uid: str | None = None,
) -> tuple[str, dict[str, Any]]:
    platform = _checked_platform(platform)
    params = {"platform": platform}
    if uid is not None:
        uid = _checked_uid(uid)
        params["uid"] = uid
    else:
        params["player"] = player_name
    response_data = _validate_player_payload(await _fetch(
        "bridge", params
    ))

    global_data: dict[str, Any] = response_data.get("global", {})
    if uid is not None and str(global_data["uid"]) != uid:
        raise ApexAPIError("查询失败: API 返回的 UID 与请求不一致")
    realtime_data: dict[str, Any] = response_data.get("realtime", {})
    bans_data: dict[str, Any] = global_data.get("bans", {})
    rank_data: dict[str, Any] = global_data.get("rank", {})
    display_name = global_data.get("name")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = player_name

    player_info: dict[str, Any] = {
        "名称": display_name,
        "UID": global_data.get("uid"),
        "平台": global_data.get("platform") or platform,
        "等级": global_data.get("level"),
        "升级进度": (
            f"{global_data.get('toNextLevelPercent')}%"
            if global_data.get("toNextLevelPercent") is not None
            else "未知"
        ),
    }

    if bans_data.get("isActive"):
        player_info.update({
            "封禁状态": convert(bans_data.get("isActive")),
            "剩余秒数": bans_data.get("remainingSeconds"),
            "最后封禁原因": convert(bans_data.get("last_banReason")),
        })

    rank_div = rank_data.get("rankDiv")
    rank_name = convert(rank_data.get("rankName"))
    rank_display = _format_rank(rank_name, rank_div)

    player_info.update({
        "大逃杀分数": rank_data.get("rankScore"),
        "大逃杀段位": rank_display,
        "大厅状态": convert(realtime_data.get("lobbyState")),
        "在线": convert(realtime_data.get("isOnline")),
        "可加入": convert(realtime_data.get("canJoin")),
        "队伍已满": convert(realtime_data.get("partyFull")),
        "已选传奇": convert(realtime_data.get("selectedLegend")),
        "当前状态": convert(realtime_data.get("currentState")),
        "状态": convert(realtime_data.get("currentStateAsText")),
    })

    details = _player_details(response_data)
    player_info.update({
        "转生等级": details["prestige"],
        "战斗通行证等级": details["battlepass_level"],
        "排位赛季": details["ranked_season"] or None,
        "ALS 收录玩家排名": (
            f"前 {details['global_rank_pct']}%"
            if details["global_rank_pct"] is not None else None
        ),
        "当前传奇皮肤": details["legend_skin"] or None,
    })
    for tracker in details["trackers"]:
        player_info[f"{details['tracker_legend'] or '当前传奇'}追踪器 · {tracker['name']}"] = tracker["value"]
    if details["trackers"]:
        player_info["追踪器说明"] = "仅展示已装备追踪器，不代表完整生涯统计"

    raw_data: dict[str, Any] = {
        "uid": global_data.get("uid"),
        "name": display_name,
        "platform": global_data.get("platform") or platform,
        "level": global_data.get("level"),
        "rank_score": rank_data.get("rankScore"),
        "rank_name": convert(rank_data.get("rankName")),
        "rank_div": rank_data.get("rankDiv"),
        "rank_img": rank_data.get("rankImg", ""),
        "avatar": global_data.get("avatar", ""),
        "selected_legend": convert(realtime_data.get("selectedLegend", "")),
        "current_state": convert(realtime_data.get("currentState", "")),
        "to_next_level_pct": global_data.get("toNextLevelPercent"),
        "lobby_state": convert(realtime_data.get("lobbyState", "")),
        "is_online": convert(realtime_data.get("isOnline")),
        "can_join": convert(realtime_data.get("canJoin")),
        "party_full": convert(realtime_data.get("partyFull")),
        "state_as_text": convert(realtime_data.get("currentStateAsText", "")),
        "ban_is_active": bans_data.get("isActive"),
        "ban_remaining_secs": bans_data.get("remainingSeconds"),
        "ban_reason": convert(bans_data.get("last_banReason", "")),
        **details,
    }

    return format_player_stats(player_info), raw_data


async def get_map_rotation_data() -> dict[str, Any]:
    async def load() -> dict[str, Any]:
        data = await _fetch("maprotation", {"version": "2"})
        modes = {}
        for key in ("battle_royale", "ranked", "ltm"):
            mode = _mapping(data.get(key))
            current = _mapping(mode.get("current"))
            next_map = _mapping(mode.get("next"))
            if not isinstance(current.get("map"), str):
                current = {}
            if not isinstance(next_map.get("map"), str):
                next_map = {}
            modes[key] = {**mode, "current": current, "next": next_map}
        if not any(mode["current"].get("map") for mode in modes.values()):
            raise ApexAPIError("查询失败: 地图数据不完整，请稍后重试")
        return modes
    return await _map_rotation_cache.get_or_fetch("rotation", load)


async def get_map_rotation() -> tuple[str, dict[str, Any]]:
    try:
        response_data = await get_map_rotation_data()
    except ApexAPIError as e:
        return str(e), {}

    battle_royale = response_data.get("battle_royale", {})
    ranked = response_data.get("ranked", {})
    ltm = response_data.get("ltm", {})

    text = (
        format_map_data(battle_royale, "大逃杀")
        + format_map_data(ranked, "排位赛")
        + format_map_data(ltm, "混录带")
    ).strip()
    return text, response_data


def _server_row(name: str, data: Any) -> dict[str, Any]:
    entry = _mapping(data)
    status = entry.get("Status")
    return {"name": name, "status": status if isinstance(status, str) else "",
            "response_time": _nonnegative_int(entry.get("ResponseTime"))}


async def _traverse_server_sections(
    raw_data: dict[str, Any],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_name, section_key in _SERVER_SECTIONS.items():
        section_rows: list[dict[str, Any]] = []
        section_data = _mapping(raw_data.get(section_key))
        if section_key == "selfCoreTest":
            for test_name, test_key in _SELF_CORE_TESTS.items():
                section_rows.append(_server_row(test_name, section_data.get(test_key)))
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in _OTHER_PLATFORMS.items():
                section_rows.append(_server_row(platform_name, section_data.get(platform_key)))
        else:
            for region_name, region_key in _SERVER_REGIONS.items():
                section_rows.append(_server_row(region_name, section_data.get(region_key)))
        if section_rows:
            sections.append({
                "section_name": section_name,
                "section_key": section_key,
                "rows": section_rows,
            })
    return sections


async def get_server_status_data() -> list[dict[str, Any]]:
    async def load() -> list[dict[str, Any]]:
        sections = await _traverse_server_sections(await _fetch("servers"))
        if not any(row["status"] for section in sections for row in section["rows"]):
            raise ApexAPIError("查询失败: 服务器状态数据不完整，请稍后重试")
        return sections
    return await _server_status_cache.get_or_fetch("status", load)


async def get_server_status() -> tuple[str, list[dict[str, Any]]]:
    try:
        sections = await get_server_status_data()
    except ApexAPIError as e:
        return str(e), []
    return format_server_status(sections), sections


async def _load_predator_data() -> dict[str, Any]:
    platform_display: dict[str, str] = {
        "PC": "PC 端",
        "PS4": "PS4/5 端",
        "X1": "Xbox 端",
        "SWITCH": "Switch 端",
    }
    response_data = await _fetch("predator")
    rp = _mapping(response_data.get("RP"))
    result: dict[str, Any] = {}
    for pk, pn in platform_display.items():
        platform_data = _mapping(rp.get(pk))
        if not platform_data:
            continue
        result[pk] = {
            "name": pn,
            "found_rank": _nonnegative_int(platform_data.get("foundRank")),
            "val": _nonnegative_int(platform_data.get("val")),
            "uid": platform_data.get("uid", ""),
            "total_masters": _nonnegative_int(platform_data.get("totalMastersAndPreds")),
        }
    if not result:
        raise ApexAPIError("查询失败: 顶猎数据不完整，请稍后重试")
    return result


async def get_predator_data() -> dict[str, Any]:
    return await _predator_cache.get_or_fetch("predator", _load_predator_data)


async def get_predator() -> tuple[str, dict[str, Any]]:
    try:
        data = await get_predator_data()
    except ApexAPIError as e:
        return str(e), {}
    return format_predator(data), data


apex = on_alconna(Alconna(
    ["/", "."],
    "apex",
    Args["player_name?#玩家名称", str]["platform?#平台", str],
    Option("m|map|地图", dest="map", help_text="查询地图信息"),
    Option("s|server|服务器", dest="server", help_text="查询服务器状态"),
    Option("p|predator|顶猎", dest="predator", help_text="查询顶猎分数"),
    Subcommand("bind|绑定", Args["bind_name?#玩家名称", str]["bind_platform?#平台", str],
           dest="bind", help_text="绑定玩家名称；不带名称时查看绑定"),
    Subcommand("binduid|绑定UID|绑定uid", Args["bind_uid?#UID", str]["bind_uid_platform?#平台", str],
           dest="binduid", help_text="通过 UID 绑定玩家"),
    Option("unbind|解绑", dest="unbind", help_text="解除自己的玩家绑定"),
    meta=CommandMeta(
        description=__plugin_meta__.description,
        usage=__plugin_meta__.usage,
        example="/apex [玩家名称/地图/服务器/顶猎] [平台]",
        author=__plugin_meta__.extra["author"],
    ),
))

_player_matcher = apex.dispatch("$main")
_map_matcher = apex.dispatch("map")
_server_matcher = apex.dispatch("server")
_predator_matcher = apex.dispatch("predator")
_bind_matcher = apex.dispatch("bind")
_bind_uid_matcher = apex.dispatch("binduid")
_unbind_matcher = apex.dispatch("unbind")


async def _check_command_api_key(matcher: Matcher) -> None:
    if not config.apex_api_key or _api_key_available is False:
        await matcher.finish("API密钥不可用")


for _matcher in (_player_matcher, _map_matcher, _server_matcher, _predator_matcher,
                 _bind_matcher, _bind_uid_matcher, _unbind_matcher):
    _matcher.handle()(_check_command_api_key)



# ── HTML rendering ──
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# Official EA character artwork, used only when the API banner is unavailable.
_LEGEND_BACKGROUNDS = {
    # https://www.ea.com/games/apex-legends/apex-legends/characters-hub/alter
    "Alter": "https://drop-assets.ea.com/images/1iPb6t3TxDIESHeSllr56c/a5d03b2b0d25b1e112ec04120cd46c61/Apex-Legends_Alter-16x9.png",
    # https://www.ea.com/games/apex-legends/apex-legends/characters-hub/axle
    "Axle": "https://drop-assets.ea.com/images/37eQmZPoSmnSovrEXlnydN/b0206115ce11e2730272cb5471ed1685/Apex-Legends_Axle-16x9__1_.png",
    # https://www.ea.com/games/apex-legends/apex-legends/characters-hub/sparrow
    "Sparrow": "https://drop-assets.ea.com/images/5dm4sqqFWQkSDsB8bDrLH3/5b5f93f29476267b5c48dc90bd3393cf/Apex-Legends_Sparrow-16x9.png",
}


@lru_cache(maxsize=1)
def _font_bytes() -> bytes:
    return (_TEMPLATE_DIR.parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf").read_bytes()


_ARTWORK_TIMEOUT = 10.0


async def _image_uri(url: str) -> str:
    try:
        return await asyncio.wait_for(_load_image_uri(url), timeout=_ARTWORK_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("Optional card artwork exceeded its total time budget")
        return ""


async def _load_image_uri(url: str) -> str:
    """Fetch optional artwork outside the browser; failures leave a plain panel."""
    if not url or not url.startswith(("https://", "http://")):
        return ""
    if await _missing_image_cache.get(url):
        return ""
    cache_dir = get_plugin_data_dir() / "card_images"
    path = cache_dir / hashlib.sha256(url.encode()).hexdigest()
    try:
        if path.exists():
            raw = await asyncio.to_thread(path.read_bytes)
        else:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > 8 * 1024 * 1024:
                            raise ValueError("Artwork exceeds 8 MiB")
                    raw = bytes(chunks)
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            return ""
        if not path.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, raw)
        return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (404, 410):
            await _missing_image_cache.set(url, True)
        logger.warning("Optional card artwork returned HTTP %d", exc.response.status_code)
        return ""
    except Exception:
        logger.warning("Failed to load optional card artwork")
        return ""


async def _render_card(template: str, width: int, **variables: Any) -> bytes:
    image = await render_template(
        _TEMPLATE_DIR, template,
        {**variables, "font": await asyncio.to_thread(_font_bytes)},
        filters={"convert": convert}, width=width, device_pixel_ratio=1,
        timeout_seconds=30,
    )
    return bytes(image)


async def render_map_card(data: dict[str, Any]) -> bytes:
    modes = []
    for key, label in (("battle_royale", "大逃杀"), ("ranked", "排位赛"), ("ltm", "混录带")):
        mode = data.get(key, {})
        if not mode.get("current"):
            continue
        current = dict(mode["current"])
        current["asset"] = await _image_uri(current.get("asset") or "")
        start, end = current.get("start"), current.get("end")
        time_range = ""
        if start and end:
            tz = timezone(timedelta(hours=8))
            time_range = f"{datetime.fromtimestamp(int(start), tz):%H:%M} – {datetime.fromtimestamp(int(end), tz):%H:%M}"
        remaining = max(0, int(current.get("remainingSecs") or 0))
        duration = max(1, int(current.get("DurationInSecs") or 1))
        modes.append({"label": label, "current": current, "next": mode.get("next", {}),
                      "time_range": time_range, "progress": min(100, remaining / duration * 100)})
    return await _render_card("map.html", 900, title="Apex 地图轮换", modes=modes)


async def render_server_card(sections: list[dict[str, Any]]) -> bytes:
    return await _render_card("server.html", 760, title="Apex 服务器状态", sections=sections)


async def render_predator_card(data: dict[str, Any]) -> bytes:
    return await _render_card("predator.html", 460, title="Apex 猎杀者", platforms=list(data.values()))


async def render_player_card(
    player: dict[str, Any], changes: dict[str, str] | None = None,
    score_diff: int | None = None,
) -> bytes:
    rank_img, banner, avatar = await asyncio.gather(
        _image_uri(player.get("rank_img") or ""),
        _image_uri(player.get("legend_banner") or ""),
        _image_uri(player.get("avatar") or ""),
    )
    if not banner and (fallback := _LEGEND_BACKGROUNDS.get(player.get("legend_key"))):
        banner = await _image_uri(fallback)
    player = {**player, "rank_img": rank_img, "legend_banner": banner,
              "avatar": avatar,
              "rank_display": _format_rank(player.get("rank_name") or "未知", player.get("rank_div"))}
    return await _render_card("player.html", 460, title="Apex 玩家信息", player=player,
                              changes=changes or {}, score_diff=score_diff)


# ── Handlers ──

async def _send_card_or_text(matcher: Any, pic: bytes, text: str) -> None:
    try:
        # Strict export prevents unsupported images becoming "[image]" text.
        await matcher.send(UniMessage.image(raw=pic), fallback=False)
    except Exception:
        logger.warning("Failed to export or send card, falling back to text")
        await matcher.finish(text)
        return
    await matcher.finish()


async def _render_or_fallback(
    matcher: Any,
    get_both: Any,
    render: Any,
) -> None:
    if config.apex_only_text:
        text, _ = await get_both()
        await matcher.finish(text)
        return
    text, data = await get_both()
    if not data:
        await matcher.finish(text)
        return
    try:
        pic = await render(data)
    except Exception:
        logger.exception("Failed to render, falling back to text")
        await matcher.finish(text)
        return
    await _send_card_or_text(matcher, pic, text)


@_map_matcher.handle()
async def apex_map() -> None:
    await _render_or_fallback(
        matcher=_map_matcher,
        get_both=get_map_rotation,
        render=render_map_card,
    )


@_server_matcher.handle()
async def apex_server() -> None:
    await _render_or_fallback(
        matcher=_server_matcher,
        get_both=get_server_status,
        render=render_server_card,
    )


@_predator_matcher.handle()
async def apex_predator() -> None:
    await _render_or_fallback(
        matcher=_predator_matcher,
        get_both=get_predator,
        render=render_predator_card,
    )


def _binding_text(binding: Any) -> str:
    return f"玩家: {binding.player_name}\nUID: {binding.uid}\n平台: {binding.platform}"


async def _bind_account(
    matcher: Any, bot: Bot, event: Event, target: str, platform: str, *, by_uid: bool = False,
) -> None:
    try:
        platform = _checked_platform(platform)
        target = target.strip()
        if not target:
            raise ApexAPIError("请输入玩家名称或 UID")
        if not by_uid and platform == "SWITCH":
            raise ApexAPIError("Switch 玩家请使用 /apex binduid <UID> SWITCH 绑定")
        uid = _checked_uid(target) if by_uid else None
        owner = owner_key(bot, event)
        async with owner_lock(owner):
            _, data = await get_player_stats(target, platform, uid=uid)
            resolved_uid = _checked_uid(str(data["uid"]))
            if _checked_platform(data["platform"]) != platform:
                raise ApexAPIError("绑定失败: API 返回的平台与请求不一致")
            await save_binding(owner, resolved_uid, data["name"], platform)
    except ApexAPIError as exc:
        await matcher.finish(str(exc))
        return
    except SQLAlchemyError:
        logger.exception("Failed to save player binding")
        await matcher.finish("绑定保存失败，请稍后重试，原绑定未更改")
        return
    await matcher.finish(
        f"已绑定玩家\n玩家: {data['name']}\nUID: {resolved_uid}\n平台: {platform}\n发送 /apex 查询，/apex unbind 解绑"
    )


@_bind_matcher.handle()
async def apex_bind(
    bot: Bot, event: Event, bind_name: str | None = None, bind_platform: str = "PC",
) -> None:
    if bind_name is None:
        try:
            binding = await get_binding(owner_key(bot, event))
        except SQLAlchemyError:
            logger.exception("Failed to read player binding")
            await _bind_matcher.finish("读取绑定失败，请稍后重试")
            return
        if binding is None:
            await _bind_matcher.finish("尚未绑定玩家。使用 /apex bind <玩家名称> [平台] 或 /apex binduid <UID> [平台]")
        await _bind_matcher.finish("当前绑定\n" + _binding_text(binding))
        return
    await _bind_account(_bind_matcher, bot, event, bind_name, bind_platform)


@_bind_uid_matcher.handle()
async def apex_bind_uid(
    bot: Bot, event: Event, bind_uid: str | None = None, bind_uid_platform: str = "PC",
) -> None:
    if bind_uid is None:
        await _bind_uid_matcher.finish("请输入 UID，例如 /apex binduid 1014411853046 PC")
        return
    await _bind_account(_bind_uid_matcher, bot, event, bind_uid, bind_uid_platform, by_uid=True)


@_unbind_matcher.handle()
async def apex_unbind(bot: Bot, event: Event) -> None:
    try:
        removed = await delete_binding(owner_key(bot, event))
    except SQLAlchemyError:
        logger.exception("Failed to delete player binding")
        await _unbind_matcher.finish("解绑失败，请稍后重试")
        return
    await _unbind_matcher.finish("已解除玩家绑定" if removed else "尚未绑定玩家")


async def _compare_and_save(  # noqa: PLR0913
    uid: str,
    plat: str,
    player_name: str,
    level: int,
    rank_score: int,
    rank_name: str,
    rank_div: int | None,
    stats_text: str,
    prestige: int | None = None,
    observed_at: datetime | None = None,
) -> tuple[dict[str, str], int | None, str]:
    async with _player_lock(uid, plat):
        changes: dict[str, str] = {}
        score_diff: int | None = None

        if not uid:
            return changes, score_diff, stats_text

        try:
            previous = await get_latest_record(uid, plat)
            if (previous is not None and observed_at is not None
                    and previous.created_at.replace(tzinfo=timezone.utc) >= observed_at):
                return changes, score_diff, stats_text
            current_stats = PlayerStatsData(
                level=level,
                rank_score=rank_score,
                rank_name=rank_name,
                rank_div=rank_div,
                prestige=prestige,
            )
            await save_record(
                uid=uid,
                player_name=player_name,
                platform=plat,
                stats=current_stats,
                observed_at=observed_at,
            )
            if previous is not None:
                score_diff = rank_score - previous.rank_score
                prev_stats = PlayerStatsData(
                    level=previous.level,
                    rank_score=previous.rank_score,
                    rank_name=previous.rank_name,
                    rank_div=previous.rank_div,
                    prestige=previous.prestige,
                )
                changes = format_comparison(current_stats, prev_stats)
                if changes:
                    lines = stats_text.split("\n")
                    for i, line in enumerate(lines):
                        for key, suffix in changes.items():
                            if line.startswith(f"{key}: "):
                                lines[i] = line + " " + suffix
                                break
                    stats_text = "\n".join(lines)
        except Exception:
            logger.exception("Failed to save or compare player stats")

        return changes, score_diff, stats_text


@_player_matcher.handle()
async def apex_player(
    bot: Bot, event: Event, player_name: str | None = None, platform: str = "PC",
) -> None:
    binding = None
    if player_name is None:
        try:
            binding = await get_binding(owner_key(bot, event))
        except SQLAlchemyError:
            logger.exception("Failed to read player binding")
            await _player_matcher.finish("读取绑定失败，请稍后重试；也可使用 /apex <玩家名称> 直接查询")
            return
        if binding is None:
            await _player_matcher.finish("请输入玩家名称，或先使用 /apex bind <玩家名称> [平台] 绑定账号")
            return
        player_name, platform = binding.player_name, binding.platform
    observed_at = datetime.now(timezone.utc)
    try:
        stats_text, raw_data = await get_player_stats(player_name, platform, uid=binding.uid if binding else None)
    except ApexAPIError as e:
        await _player_matcher.finish(str(e))

    if binding is not None and raw_data["name"] != binding.player_name:
        try:
            await refresh_binding_name(owner_key(bot, event), binding.uid, binding.platform, raw_data["name"])
        except SQLAlchemyError:
            logger.warning("Failed to refresh bound player name")

    level = raw_data["level"]
    rank_score = raw_data["rank_score"]
    rank_name = str(raw_data.get("rank_name") or "")
    rank_div_raw = raw_data.get("rank_div")
    rank_div = int(rank_div_raw) if rank_div_raw is not None else None
    uid = str(raw_data.get("uid") or "")
    plat = str(raw_data.get("platform") or platform)

    changes, score_diff, stats_text = await _compare_and_save(
        uid, plat, player_name, level, rank_score, rank_name, rank_div, stats_text,
        prestige=raw_data.get("prestige"), observed_at=observed_at,
    )

    if config.apex_only_text:
        await _player_matcher.finish(stats_text)

    try:
        pic_bytes = await render_player_card(raw_data, changes, score_diff)
    except Exception:
        logger.exception("Failed to render player card, falling back to text")
        await _player_matcher.finish(stats_text)
    await _send_card_or_text(_player_matcher, pic_bytes, stats_text)
