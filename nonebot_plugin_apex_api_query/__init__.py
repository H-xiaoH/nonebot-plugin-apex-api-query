from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from nonebot import get_driver, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from PIL import Image, ImageDraw, ImageFont, ImageOps

os.environ.setdefault("ALEMBIC_STARTUP_CHECK", "false")

require("nonebot_plugin_localstore")
require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")

from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Option,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_localstore import get_plugin_data_dir
from nonebot_plugin_orm import get_session
from sqlalchemy import desc, select

from .config import config
from .models import PlayerStats

# ── 模块级常量 ──
_TEXT_WHITE = (255, 255, 255)
_TEXT_GRAY = (170, 178, 190)
_TEXT_LABEL = (140, 148, 160)
_RING_GREEN = (47, 161, 108)
_RING_ORANGE = (194, 137, 24)
_RING_RED = (194, 20, 20)
_TEXT_DIM = (110, 118, 130)

_CARD_BG = (24, 24, 24, 255)
_ACCENT = (218, 49, 52)

_SERVER_SECTIONS: dict[str, str] = {
    "Origin 登录": "Origin_login",
    "EA 融合": "EA_novafusion",
    "EA 账户": "EA_accounts",
    "Apex 跨平台验证": "ApexOauth_Crossplay",
    "自我核心测试": "selfCoreTest",
    "其他平台": "otherPlatforms",
}
_SERVER_REGIONS: dict[str, str] = {
    "欧盟西部": "EU-West",
    "欧盟东部": "EU-East",
    "美国西部": "US-West",
    "美国中部": "US-Central",
    "美国东部": "US-East",
    "南美洲": "SouthAmerica",
    "亚洲": "Asia",
}
_SELF_CORE_TESTS: dict[str, str] = {
    "网站状态": "Status-website",
    "统计 API": "Stats-API",
    "溢出 #1": "Overflow-#1",
    "溢出 #2": "Overflow-#2",
    "Origin API": "Origin-API",
    "Playstation API": "Playstation-API",
    "Xbox API": "Xbox-API",
}
_OTHER_PLATFORMS: dict[str, str] = {
    "Playstation Network": "Playstation-Network",
    "Xbox Live": "Xbox-Live",
}


logger = logging.getLogger(__name__)

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

# ── 模块级状态 ──
_image_cache: dict[str, Image.Image] = {}
_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


@driver.on_shutdown
async def _on_shutdown() -> None:
    await _cleanup_ds()


def convert(name: Any) -> Any:
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

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, val = entry
            if time.time() - ts < self._ttl:
                return val
            del self._store[key]
            return None

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = (time.time(), value)

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


_map_rotation_cache = AsyncTTLCache(ttl=60)
_server_status_cache = AsyncTTLCache(ttl=30)
_predator_cache = AsyncTTLCache(ttl=300)


@dataclass
class PlayerStatsData:
    level: int
    rank_score: int
    rank_name: str
    rank_div: int | None


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
) -> None:
    async with get_session() as session:
        record = PlayerStats(
            uid=uid,
            player_name=player_name,
            platform=platform,
            level=stats.level,
            rank_score=stats.rank_score,
            rank_name=stats.rank_name,
            rank_div=stats.rank_div,
            created_at=datetime.now(tz=timezone.utc),
        )
        session.add(record)
        await session.commit()


def format_comparison(
    current: PlayerStatsData, previous: PlayerStatsData,
) -> dict[str, str]:
    changes: dict[str, str] = {}
    level_diff = current.level - previous.level
    if level_diff > 0:
        changes["等级"] = f"(↑{level_diff})"
    elif level_diff < 0:
        changes["等级"] = f"(↓{abs(level_diff)})"

    score_diff = current.rank_score - previous.rank_score
    if score_diff > 0:
        changes["大逃杀分数"] = f"(↑{score_diff})"
    elif score_diff < 0:
        changes["大逃杀分数"] = f"(↓{abs(score_diff)})"

    prev_rank = (
        f"{previous.rank_name} {previous.rank_div}"
        if previous.rank_div is not None
        else previous.rank_name
    )
    curr_rank = (
        f"{current.rank_name} {current.rank_div}"
        if current.rank_div is not None
        else current.rank_name
    )
    if prev_rank != curr_rank:
        changes["大逃杀段位"] = f"({prev_rank})"

    return changes


def format_map_data(map_data: dict[str, Any], mode_name: str) -> str:
    current = map_data.get("current", {})
    next_map = map_data.get("next", {})
    return (
        f"{mode_name}:\n"
        f"当前地图: {convert(current.get('map'))}\n"
        f"下个地图: {convert(next_map.get('map'))}\n"
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
            f"顶尖猎杀者人数: {info['found_rank']}\n"
            f"顶尖猎杀者分数: {info['val']}\n"
            f"顶尖猎杀者UID: {info['uid']}\n"
            "大师和顶尖猎杀者人数: "
            f"{info['total_masters']}"
        )
    return "\n\n".join(lines)


def format_player_stats(player_info: dict[str, Any]) -> str:
    return "玩家信息:\n" + "\n".join(
        f"{key}: {value}"
        for key, value in player_info.items()
        if value is not None
    )


def _get_client() -> httpx.AsyncClient:
    if _get_client._client is None:  # type: ignore[union-attr]
        _get_client._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://apexlegendsstatus.com/",
            }
        )  # type: ignore[union-attr]
    return _get_client._client  # type: ignore[union-attr]


_get_client._client: httpx.AsyncClient | None = None  # type: ignore[union-attr]


async def _cleanup_ds() -> None:
    if _get_client._client is not None:  # type: ignore[union-attr]
        await _get_client._client.aclose()  # type: ignore[union-attr]
        _get_client._client = None  # type: ignore[union-attr]


class ApexAPIError(Exception):
    pass


async def query_apex_api(
    server: str,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> httpx.Response:
    payload: dict[str, Any] = {"auth": config.apex_api_key}
    if params:
        payload.update(params)
    base = base_url or config.apex_api_url
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    ) as client:
        return await client.get(f"{base}/{server}", params=payload, timeout=30)


async def _fetch(
    endpoint: str,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    try:
        response = await query_apex_api(endpoint, params, base_url)
    except httpx.HTTPError as e:
        logger.exception("Failed to query %s", endpoint)
        raise ApexAPIError("查询失败: 网络请求错误") from e  # noqa: TRY003
    if response.status_code != 200:  # noqa: PLR2004
        logger.warning(
            "API %s returned %d: %s", endpoint, response.status_code, response.text
        )
        raise ApexAPIError(response.text)
    try:
        return response.json()
    except json.JSONDecodeError as e:
        logger.exception("Failed to parse %s response", endpoint)
        raise ApexAPIError("查询失败: API 返回数据格式错误") from e  # noqa: TRY003


async def get_player_stats(
    player_name: str, platform: str = "PC",
) -> tuple[str, dict[str, Any]]:
    response_data = await _fetch(
        "bridge", {"player": player_name, "platform": platform}
    )

    global_data: dict[str, Any] = response_data.get("global", {})
    realtime_data: dict[str, Any] = response_data.get("realtime", {})
    bans_data: dict[str, Any] = global_data.get("bans", {})
    rank_data: dict[str, Any] = global_data.get("rank", {})

    player_info: dict[str, Any] = {
        "名称": global_data.get("name"),
        "UID": global_data.get("uid"),
        "平台": global_data.get("platform"),
        "等级": global_data.get("level"),
        "距下一级百分比": (
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
    rank_display = f"{rank_name} {rank_div}" if rank_div else rank_name

    player_info.update({
        "大逃杀分数": rank_data.get("rankScore"),
        "大逃杀段位": rank_display,
        "大厅状态": convert(realtime_data.get("lobbyState")),
        "在线": convert(realtime_data.get("isOnline")),
        "可加入": convert(realtime_data.get("canJoin")),
        "群满员": convert(realtime_data.get("partyFull")),
        "已选传奇": convert(realtime_data.get("selectedLegend")),
        "当前状态": convert(realtime_data.get("currentState")),
        "状态": convert(realtime_data.get("currentStateAsText")),
    })

    raw_data: dict[str, Any] = {
        "uid": global_data.get("uid"),
        "name": global_data.get("name"),
        "platform": global_data.get("platform"),
        "level": global_data.get("level"),
        "rank_score": rank_data.get("rankScore"),
        "rank_name": convert(rank_data.get("rankName")),
        "rank_div": rank_data.get("rankDiv"),
        "rank_img": rank_data.get("rankImg", ""),
        "avatar": global_data.get("avatar", ""),
        "selected_legend": convert(realtime_data.get("selectedLegend", "")),
        "current_state": convert(realtime_data.get("currentState", "")),
        "global_rank_pct": str(rank_data.get("ALStopPercentGlobal", "")),
        "to_next_level_pct": global_data.get("toNextLevelPercent"),
        "lobby_state": convert(realtime_data.get("lobbyState", "")),
        "is_online": convert(realtime_data.get("isOnline")),
        "can_join": convert(realtime_data.get("canJoin")),
        "party_full": convert(realtime_data.get("partyFull")),
        "state_as_text": convert(realtime_data.get("currentStateAsText", "")),
        "ban_is_active": bans_data.get("isActive"),
        "ban_remaining_secs": bans_data.get("remainingSeconds"),
        "ban_reason": convert(bans_data.get("last_banReason", "")),
    }

    return format_player_stats(player_info), raw_data


async def get_map_rotation_data() -> dict[str, Any]:
    return await _fetch("maprotation", {"version": "2"})


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
        + format_map_data(ranked, "排位赛联盟")
        + format_map_data(ltm, "混录带")
    ).strip()
    return text, response_data


async def _traverse_server_sections(
    raw_data: dict[str, Any],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_name, section_key in _SERVER_SECTIONS.items():
        section_rows: list[dict[str, Any]] = []
        section_data = raw_data.get(section_key, {})
        if section_key == "selfCoreTest":
            for test_name, test_key in _SELF_CORE_TESTS.items():
                entry = section_data.get(test_key, {})
                section_rows.append({
                    "name": test_name,
                    "status": entry.get("Status", ""),
                    "response_time": entry.get("ResponseTime", -1),
                })
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in _OTHER_PLATFORMS.items():
                entry = section_data.get(platform_key, {})
                section_rows.append({
                    "name": platform_name,
                    "status": entry.get("Status", ""),
                    "response_time": entry.get("ResponseTime", -1),
                })
        else:
            for region_name, region_key in _SERVER_REGIONS.items():
                entry = section_data.get(region_key, {})
                section_rows.append({
                    "name": region_name,
                    "status": entry.get("Status", ""),
                    "response_time": entry.get("ResponseTime", -1),
                })
        if section_rows:
            sections.append({
                "section_name": section_name,
                "section_key": section_key,
                "rows": section_rows,
            })
    return sections


async def get_server_status_data() -> list[dict[str, Any]]:
    response_data = await _fetch("servers")
    sections = await _traverse_server_sections(response_data)
    return sections


async def get_server_status() -> tuple[str, list[dict[str, Any]]]:
    try:
        sections = await get_server_status_data()
    except ApexAPIError as e:
        return str(e), []
    return format_server_status(sections), sections


async def get_predator_data() -> dict[str, Any]:
    platform_display: dict[str, str] = {
        "PC": "PC 端",
        "PS4": "PS4/5 端",
        "X1": "Xbox 端",
        "SWITCH": "Switch 端",
    }
    response_data = await _fetch("predator")
    rp = response_data.get("RP", {})
    result: dict[str, Any] = {}
    for pk, pn in platform_display.items():
        platform_data = rp.get(pk, {})
        result[pk] = {
            "name": pn,
            "found_rank": platform_data.get("foundRank", 0),
            "val": platform_data.get("val", 0),
            "uid": platform_data.get("uid", ""),
            "total_masters": platform_data.get("totalMastersAndPreds", 0),
        }
    return result


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


# ── PIL rendering ──

def _get_map_cache_dir() -> Path:
    if _get_map_cache_dir._dir is None:  # type: ignore[union-attr]
        try:
            _get_map_cache_dir._dir = get_plugin_data_dir() / "map_images"  # type: ignore[union-attr]
        except RuntimeError:
            _get_map_cache_dir._dir = (  # type: ignore[union-attr]
                Path(os.environ.get("TMPDIR", "/tmp")) / "apex_map_images"
            )
        _get_map_cache_dir._dir.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
    return _get_map_cache_dir._dir  # type: ignore[union-attr]


_get_map_cache_dir._dir: Path | None = None  # type: ignore[union-attr]


def _load_font(
    size: int, weight: int = 600,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    cache_key = (size, weight)
    if cache_key in _font_cache:
        return _font_cache[cache_key]
    font_paths = [
        str(Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"),
    ]
    for path in font_paths:
        if Path(path).exists():
            f = ImageFont.truetype(path, size)
            with suppress(Exception):
                f.font.setvaraxes([weight])
            _font_cache[cache_key] = f
            return f
    _font_cache[cache_key] = ImageFont.load_default()
    return _font_cache[cache_key]


def _fmt_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "00:00"
    mins, secs = divmod(seconds, 60)
    if mins >= 60:  # noqa: PLR2004
        hours, mins = divmod(mins, 60)
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


async def _download_image(url: str) -> Image.Image | None:
    if url in _image_cache:
        return _image_cache[url]
    cache_key = url.rsplit("/", 1)[-1]
    disk_path = _get_map_cache_dir() / cache_key
    try:
        if disk_path.exists():
            img = Image.open(disk_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            img.load()
            _image_cache[url] = img
            return img
    except Exception:
        logger.exception("Failed to load cached map image: %s", disk_path)
    try:
        client = _get_client()
        resp = await client.get(url)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.load()
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP %d for image: %s", e.response.status_code, url)
        return None
    except Exception:
        logger.exception("Failed to download image: %s", url)
        return None
    else:
        _image_cache[url] = img
        with suppress(OSError):
            img.save(disk_path, format="PNG")
        return img


def _load_and_paste(
    canvas: Image.Image,
    url: str,
    dest_x: int,
    dest_y: int,
    size: int,
) -> None:
    if not url:
        return
    img = _image_cache.get(url)
    if img:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        canvas.paste(resized, (dest_x, dest_y), resized)


def _draw_shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    _text_shadow = (0, 0, 0)
    draw.text((xy[0] + 2, xy[1] + 2), text, font=font, fill=_text_shadow)
    draw.text(xy, text, font=font, fill=fill)


def _draw_progress_ring(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    remaining_secs: int,
    duration_secs: int,
) -> None:
    """绘制圆环进度条：半径 56px，颜色随剩余时间变化，中央显示倒计时。"""
    _five_minutes_s = 300
    _fifteen_minutes_s = 900

    radius = 56
    stroke = 7
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.pieslice(bbox, 0, 360, fill=(0, 0, 0))
    if duration_secs <= 0:
        return
    fraction = max(0, min(1, remaining_secs / duration_secs))
    if remaining_secs <= _five_minutes_s:
        color = _RING_RED
    elif remaining_secs <= _fifteen_minutes_s:
        color = _RING_ORANGE
    else:
        color = _RING_GREEN
    start = 90
    end = 90 + int(360 * fraction)
    arc_bbox = [
        bbox[0] + stroke,
        bbox[1] + stroke,
        bbox[2] - stroke + 1,
        bbox[3] - stroke + 1,
    ]
    draw.arc(arc_bbox, start=start, end=end, fill=color, width=stroke)
    time_text = _fmt_remaining(remaining_secs)
    max_w = (radius - stroke) * 2 - 12
    for size in range(26, 10, -2):
        font = _load_font(size)
        if draw.textbbox((0, 0), time_text, font=font)[2] <= max_w:
            break
    else:
        font = _load_font(12)
    bb = draw.textbbox((0, 0), time_text, font=font)
    tw, th = int(bb[2] - bb[0]), int(bb[3] - bb[1])
    ty = int(cy - th)
    _draw_shadow_text(draw, (cx - tw // 2, ty), time_text, font, _TEXT_WHITE)


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    card_w: int,
    card_h: int,
    footer_h: int,
    offset: int = 4,
) -> None:
    text = "Data from apexlegendsstatus.com"
    font = _load_font(18)
    w = draw.textbbox((0, 0), text, font=font)[2]
    draw.text(
        ((card_w - w) // 2, card_h - footer_h + offset),
        text, font=font, fill=_TEXT_DIM,
    )


def _draw_panel_bg(  # noqa: PLR0913
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    accent_color: tuple[int, int, int] | None = None,
    outline_color: tuple[int, int, int, int] = (60, 64, 72, 120),
) -> None:
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=8,
        fill=(18, 20, 24, 255),
        outline=outline_color,
        width=1,
    )
    if accent_color is None:
        accent_color = _ACCENT
    draw.rectangle([x, y, x + 4, y + h], fill=accent_color)


def _cover_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return ImageOps.fit(img, (target_w, target_h), Image.Resampling.LANCZOS)


def _parse_time_str(readable: str) -> str:
    parts = readable.split(" ")
    return parts[1][:5] if len(parts) > 1 else readable


def _draw_mode_section(  # noqa: PLR0915
    canvas: Image.Image,
    y: int,
    mode_key: str,
    mode_data: dict[str, Any],
    card_w: int,
) -> int:
    """渲染一个模式区域（背景/渐变/倒计时/下次预告），返回更新后的 y 坐标。"""
    _utc_plus_8 = timezone(timedelta(hours=8))

    mode_labels: dict[str, str] = {
        "battle_royale": "大逃杀",
        "ranked": "排位赛",
        "ltm": "混录带",
    }

    current = mode_data.get("current", {})
    next_data = mode_data.get("next", {})

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, y, card_w, y + 4], fill=_ACCENT)
    y += 4
    section_y = y

    asset_url = current.get("asset", "")
    map_img = _image_cache.get(asset_url) if asset_url else None
    if map_img:
        map_bg = _cover_fit(map_img, card_w, 200)
        canvas.paste(map_bg, (0, section_y), map_bg)

    _draw_shadow_text(
        draw, (24, section_y + 24),
        mode_labels.get(mode_key, mode_key), _load_font(22), _ACCENT,
    )

    map_name = current.get("map", "未知")
    map_name_zh = convert(map_name)
    if mode_key == "ltm" and current.get("eventName"):
        map_name_zh = f"{map_name_zh} · {convert(current['eventName'])}"
    name_font = _load_font(48)
    _draw_shadow_text(
        draw, (24, section_y + 52), map_name_zh, name_font, _TEXT_WHITE,
    )

    if current.get("start") and current.get("end"):
        dt_start = datetime.fromtimestamp(int(current["start"]), tz=_utc_plus_8)
        dt_end = datetime.fromtimestamp(int(current["end"]), tz=_utc_plus_8)
        time_text = f"从 {dt_start:%H:%M} 到 {dt_end:%H:%M}"
    elif (
        (s := current.get("readableDate_start", ""))
        and (e := current.get("readableDate_end", ""))
    ):
        time_text = f"从 {_parse_time_str(s)} 到 {_parse_time_str(e)}"
    else:
        time_text = current.get("remainingTimer", "")
    time_font = _load_font(22)
    _draw_shadow_text(
        draw, (24, section_y + 126), time_text, time_font, (200, 208, 220),
    )

    remaining = int(current.get("remainingSecs", 0))
    duration = int(current.get("DurationInSecs", 0))
    _draw_progress_ring(draw, card_w - 80, section_y + 100, remaining, duration)

    y += 200

    if next_data:
        draw.rectangle([0, y, card_w, y + 60], fill=(12, 14, 18, 255))
        next_map = next_data.get("map", "未知")
        next_map_zh = convert(next_map)
        if mode_key == "ltm" and next_data.get("eventName"):
            next_map_zh = f"{next_map_zh} · {convert(next_data['eventName'])}"
        next_text = f"▶  下次: {next_map_zh}"
        next_font = _load_font(24)
        _draw_shadow_text(draw, (24, y + 12), next_text, next_font, _TEXT_WHITE)

        if next_data.get("start") and next_data.get("end"):
            ns = datetime.fromtimestamp(int(next_data["start"]), tz=_utc_plus_8)
            ne = datetime.fromtimestamp(int(next_data["end"]), tz=_utc_plus_8)
            time_str = f"{ns:%H:%M}  -  {ne:%H:%M}"
        elif (
            (s := next_data.get("readableDate_start", ""))
            and (e := next_data.get("readableDate_end", ""))
        ):
            time_str = f"{_parse_time_str(s)}  -  {_parse_time_str(e)}"
        else:
            time_str = ""
        if time_str:
            time_small = _load_font(20)
            tw = draw.textbbox((0, 0), time_str, font=time_small)[2]
            draw.text(
                (card_w - tw - 24, y + 12),
                time_str, font=time_small, fill=_TEXT_GRAY,
            )

    y += 66
    return y


def render_map_card(data: dict[str, Any]) -> bytes:
    card_w = 900
    card_h = 840
    canvas = Image.new("RGBA", (card_w, card_h), _CARD_BG)

    y = 0
    for mode_key in ("battle_royale", "ranked", "ltm"):
        mode_data = data.get(mode_key, {})
        if not mode_data.get("current"):
            continue
        y = _draw_mode_section(canvas, y, mode_key, mode_data, card_w)

    draw = ImageDraw.Draw(canvas)
    _draw_footer(draw, card_w, card_h, 36)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def _draw_status_pill(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    status: str,
    row_h: int,
) -> None:
    status_colors: dict[str, tuple[int, int, int]] = {
        "UP": (47, 161, 108),
        "DOWN": (194, 20, 20),
        "SLOW": (194, 137, 24),
        "OVERLOADED": (194, 20, 20),
    }
    status_zh = convert(status)
    color = status_colors.get(status, _TEXT_DIM)
    font = _load_font(20)
    bb = draw.textbbox((0, 0), status_zh, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw = tw + 24
    ph = th + 10
    pill_x = x
    pill_y = y + (row_h - ph) // 2 + 4
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pw, pill_y + ph],
        radius=6, fill=(*color, 40), outline=(*color, 180), width=1,
    )
    draw.text(
        (pill_x + 12, pill_y + (ph - th) // 2 - 6),
        status_zh, font=font, fill=color,
    )


def _compute_server_card_height(
    sections: list[dict[str, Any]], cols: int, row_h: int,
) -> int:
    height = 82
    for sec in sections:
        if not (rows := sec.get("rows", [])):
            continue
        height += (len(rows) + cols - 1) // cols * row_h + 32
    return max(height, 200)


def render_server_card(sections: list[dict[str, Any]]) -> bytes:
    cols = 2
    col_w = 310
    row_h = 42
    serv_card_w = 700

    card_h = _compute_server_card_height(sections, cols, row_h)
    canvas = Image.new("RGBA", (serv_card_w, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    draw.text((24, 8), "Apex 服务器状态", font=_load_font(38), fill=_TEXT_WHITE)
    _draw_footer(draw, serv_card_w, card_h, 26, 0)

    y = 56
    for sec in sections:
        rows = sec.get("rows", [])
        if not rows:
            continue
        sec_name = sec["section_name"]
        draw.rectangle([0, y, 4, y + 28 + 12], fill=_ACCENT)
        draw.text((20, y + 4), sec_name, font=_load_font(28), fill=_TEXT_WHITE)
        y += 28
        for row_idx in range(0, len(rows), cols):
            row_y = y
            for col in range(cols):
                idx = row_idx + col
                if idx >= len(rows):
                    break
                item = rows[idx]
                col_x = 28 + col * col_w
                draw.text(
                    (col_x, row_y + 11), item["name"],
                    font=_load_font(20), fill=_TEXT_WHITE,
                )
                sfont = _load_font(20)
                sw = int(draw.textbbox((0, 0), convert(item["status"]), font=sfont)[2])
                pill_w = sw + 24
                pill_x = col_x + col_w - pill_w - 12
                _draw_status_pill(draw, pill_x, row_y, str(item["status"]), row_h)
                rt = item.get("response_time", -1)
                if rt is not None and rt >= 0:
                    rt_text = f"{rt}ms"
                    rt_font = _load_font(18)
                    rtw = draw.textbbox((0, 0), rt_text, font=rt_font)[2]
                    draw.text(
                        (pill_x - rtw - 8, row_y + 10),
                        rt_text, font=rt_font, fill=(140, 150, 165),
                    )
            y += row_h
        y += 4

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def _fmt_num(value: int) -> str:
    return f"{value:,}" if value > 0 else "暂无"


def _draw_pred_cell(  # noqa: PLR0913
    canvas: Image.Image,
    x: int,
    y: int,
    platform: dict[str, Any],
    cell_w: int,
    row_h: int,
) -> None:
    _pred_score_low = 15000

    draw = ImageDraw.Draw(canvas)
    panel_w = cell_w
    panel_h = row_h * 3 + 20 * 2
    _draw_panel_bg(draw, x, y, panel_w, panel_h)
    draw.text(
        (x + 18, y + 16), platform["name"], font=_load_font(28), fill=_TEXT_WHITE,
    )

    row_y = y + 20 + row_h
    rows = [
        ("猎杀底分", f"{_fmt_num(platform.get('val', 0))} RP"),
        ("大师人数", _fmt_num(platform.get("total_masters", 0))),
    ]
    label_font = _load_font(20)
    val_font = _load_font(22)
    for label, value in rows:
        draw.text((x + 18, row_y + 3), label, font=label_font, fill=_TEXT_LABEL)
        if label == "猎杀底分" and platform.get("val", 0) > 0:
            vc = (
                _RING_GREEN
                if platform["val"] <= _pred_score_low
                else _TEXT_WHITE
            )
        elif label == "大师人数" and platform.get("total_masters", 0) <= 0:
            vc = _TEXT_LABEL
        else:
            vc = _TEXT_WHITE
        vw = draw.textbbox((0, 0), value, font=val_font)[2]
        draw.text((x + panel_w - vw - 18, row_y + 4), value, font=val_font, fill=vc)
        row_y += row_h


def render_predator_card(data: dict[str, Any]) -> bytes:
    pred_card_w = 350
    pred_cell_w = 294
    pred_row_h = 34
    pred_header_h = 56
    pred_footer_h = 26

    platforms = [
        data.get("PC", {}),
        data.get("PS4", {}),
        data.get("X1", {}),
        data.get("SWITCH", {}),
    ]
    active = [p for p in platforms if p]
    cell_h = pred_row_h * 3 + 20 * 2
    card_h = pred_header_h + len(active) * (cell_h + 14) + pred_footer_h

    canvas = Image.new("RGBA", (pred_card_w, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)
    draw.text((24, 8), "Apex 猎杀者", font=_load_font(38), fill=_TEXT_WHITE)

    start_x = (pred_card_w - pred_cell_w) // 2
    y = pred_header_h + 16
    for idx, platform in enumerate(active):
        cy = y + idx * (cell_h + 14)
        _draw_pred_cell(canvas, start_x, cy, platform, pred_cell_w, pred_row_h)

    _draw_footer(draw, pred_card_w, card_h, pred_footer_h)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def render_player_card(  # noqa: PLR0915
    player: dict[str, Any],
    changes: dict[str, str] | None = None,
    score_diff: int | None = None,
) -> bytes:
    player_card_w = 400
    player_header_h = 48
    player_row_h = 34
    player_section_gap = 14

    ban_active = player.get("ban_is_active")
    rank_h = 140
    data_rows = 7
    num_sections = 3 + (1 if ban_active else 0) + (1 if changes else 0)
    base_h = 110 + rank_h + 28 + data_rows * player_row_h + 24
    changes_h = (2 if changes else 0) * player_row_h + (20 if not changes else -28)
    ban_h = (2 * player_row_h + 20 if ban_active else 0)
    card_h = (
        base_h + changes_h + ban_h
        + num_sections * player_section_gap + 26
    )

    canvas = Image.new("RGBA", (player_card_w, card_h), _CARD_BG)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)

    draw.text((24, 8), "Apex 玩家信息", font=_load_font(38), fill=_TEXT_WHITE)

    name = str(player.get("name", "未知"))
    draw.text(
        (28, player_header_h + 10),
        name, font=_load_font(36), fill=_TEXT_WHITE,
    )
    sub_font = _load_font(20)
    uid = str(player.get("uid", ""))
    draw.text(
        (32, player_header_h + 50),
        f"UID: {uid or '未知'}",
        font=sub_font, fill=_TEXT_GRAY,
    )
    plat = str(player.get("platform", ""))
    draw.text(
        (32, player_header_h + 76),
        f"平台: {plat or '未知'}", font=sub_font, fill=_TEXT_GRAY,
    )

    y = player_header_h + 110

    _draw_panel_bg(draw, 28, y, player_card_w - 56, rank_h + 28)
    rank_img_url = str(player.get("rank_img", ""))
    if rank_img_url:
        img = _image_cache.get(rank_img_url)
        if img:
            resized = img.resize((150, 150), Image.Resampling.LANCZOS)
            canvas.paste(resized, (44, y + 10), resized)

    rank_name = str(player.get("rank_name", ""))
    rank_div = player.get("rank_div")
    rank_disp = f"{rank_name} {rank_div}" if rank_div else rank_name
    score = _fmt_num(int(player.get("rank_score", 0)))
    score_text = f"{score} 分"
    rn_font = _load_font(30)
    sf_font = _load_font(22)
    rn_w = draw.textbbox((0, 0), rank_disp, font=rn_font)[2]
    sf_w = draw.textbbox((0, 0), score_text, font=sf_font)[2]
    right_x = player_card_w - 48
    draw.text((right_x - rn_w, y + 40), rank_disp, font=rn_font, fill=_TEXT_WHITE)
    draw.text((right_x - sf_w, y + 78), score_text, font=sf_font, fill=_RING_GREEN)
    if score_diff is not None and score_diff != 0:
        diff_sign = "+" if score_diff > 0 else ""
        diff_text = f"{diff_sign}{score_diff}"
        diff_color = _RING_GREEN if score_diff > 0 else _RING_RED
        diff_font = _load_font(22)
        dw = draw.textbbox((0, 0), diff_text, font=diff_font)[2]
        draw.text(
            (right_x - dw, y + 78 + 26),
            diff_text, font=diff_font, fill=diff_color,
        )
    y += rank_h + 28 + player_section_gap

    level = player.get("level", 0)
    to_next = player.get("to_next_level_pct")
    lvl_text = f"{level}{f'  ({to_next}%)' if to_next is not None else ''}"
    legend = str(player.get("selected_legend", "")) or "未知"
    state = str(player.get("current_state", "")) or "离线"
    state_text = str(player.get("state_as_text", ""))
    lobby = str(player.get("lobby_state", "")) or "未知"
    is_online = str(player.get("is_online", "")) or "否"
    can_join = str(player.get("can_join", "")) or "否"
    party_full = str(player.get("party_full", "")) or "否"

    _draw_panel_bg(draw, 28, y, player_card_w - 56, data_rows * player_row_h + 24)
    data_y = y + 20
    lfont = _load_font(20)
    vfont = _load_font(22)
    for label, value in [
        ("等级", lvl_text),
        ("传奇", legend),
        ("大厅", lobby),
        ("在线", is_online),
        ("可加入", can_join),
        ("群满员", party_full),
        ("状态", state_text or state),
    ]:
        draw.text((48, data_y), label, font=lfont, fill=_TEXT_LABEL)
        vw = draw.textbbox((0, 0), value, font=vfont)[2]
        vx = player_card_w - 28 - vw - 18
        if label == "状态":
            vc = (
                _RING_GREEN
                if state in ("在线", "在大厅", "比赛中")
                else _RING_RED
            )
        elif label in ("在线", "可加入", "群满员"):
            vc = _RING_GREEN if value == "是" else _TEXT_LABEL
        else:
            vc = _TEXT_WHITE
        draw.text((vx, data_y), value, font=vfont, fill=vc)
        data_y += player_row_h
    y += data_rows * player_row_h + 24 + player_section_gap

    if ban_active:
        _draw_panel_bg(
            draw, 28, y, player_card_w - 56, ban_h,
            accent_color=_RING_RED, outline_color=(120, 30, 30, 120),
        )
        draw.text((48, y + 10), "封禁", font=_load_font(22), fill=(194, 130, 130))
        ban_secs = player.get("ban_remaining_secs", 0)
        ban_reason = str(player.get("ban_reason", ""))
        draw.text((48, y + 38), "状态: 是", font=vfont, fill=(255, 200, 200))
        ban_line2 = "剩余: " + (_fmt_remaining(int(ban_secs)) if ban_secs else "未知")
        if ban_reason:
            ban_line2 += f" · 原因: {ban_reason}"
        draw.text((48, y + 58), ban_line2, font=vfont, fill=(255, 200, 200))
        y += ban_h + player_section_gap

    _draw_footer(draw, player_card_w, card_h, 26)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# ── Handlers ──

async def _render_or_fallback(
    matcher: Any,
    get_both: Any,
    render: Any,
    preload: Any = None,
) -> None:
    if config.apex_only_text:
        text, _ = await get_both()
        await matcher.finish(text)
        return
    text, data = await get_both()
    if not data:
        await matcher.finish(text)
        return
    if preload is not None:
        await preload(data)
    try:
        pic = await asyncio.to_thread(render, data)
    except Exception:
        logger.exception("Failed to render, falling back to text")
        await matcher.finish(text)
        return
    await matcher.finish(UniMessage.image(raw=pic))


async def _preload_map_images(data: dict[str, Any]) -> None:
    for mode_key in ("battle_royale", "ranked", "ltm"):
        mode_data = data.get(mode_key, {})
        for entry in (mode_data.get("current", {}), mode_data.get("next", {})):
            asset_url = entry.get("asset", "")
            if asset_url and asset_url not in _image_cache:
                await _download_image(asset_url)


@_map_matcher.handle()
async def apex_map() -> None:
    await _render_or_fallback(
        matcher=_map_matcher,
        get_both=get_map_rotation,
        render=render_map_card,
        preload=_preload_map_images,
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


async def _validate_player_input(
    player_name: str | None, platform: str,
) -> str:
    valid_platforms: list[str] = ["PC", "PS4", "X1", "SWITCH"]
    if player_name is None:
        await _player_matcher.finish("请输入玩家名称")
    elif platform not in valid_platforms:
        await _player_matcher.finish(
            f"平台参数错误，请输入 {'、'.join(valid_platforms)}"
        )
    return player_name


async def _compare_and_save(  # noqa: PLR0913
    uid: str,
    plat: str,
    player_name: str,
    level: int,
    rank_score: int,
    rank_name: str,
    rank_div: int | None,
    stats_text: str,
) -> tuple[dict[str, str], int | None, str]:
    changes: dict[str, str] = {}
    score_diff: int | None = None

    if not uid:
        return changes, score_diff, stats_text

    try:
        previous = await get_latest_record(uid, plat)
        current_stats = PlayerStatsData(
            level=level,
            rank_score=rank_score,
            rank_name=rank_name,
            rank_div=rank_div,
        )
        await save_record(
            uid=uid,
            player_name=player_name,
            platform=plat,
            stats=current_stats,
        )
        if previous is not None:
            score_diff = rank_score - previous.rank_score
            prev_stats = PlayerStatsData(
                level=previous.level,
                rank_score=previous.rank_score,
                rank_name=previous.rank_name,
                rank_div=previous.rank_div,
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
    player_name: str | None = None, platform: str = "PC",
) -> None:
    player_name = await _validate_player_input(player_name, platform)

    try:
        stats_text, raw_data = await get_player_stats(player_name, platform)
    except ApexAPIError as e:
        await _player_matcher.finish(str(e))

    # 内联 _extract_player_stats
    level = int(raw_data.get("level") or 0)
    rank_score = int(raw_data.get("rank_score") or 0)
    rank_name = str(raw_data.get("rank_name") or "")
    rank_div_raw = raw_data.get("rank_div")
    rank_div = int(rank_div_raw) if rank_div_raw is not None else None
    uid = str(raw_data.get("uid") or "")
    plat = str(raw_data.get("platform") or platform)

    changes, score_diff, stats_text = await _compare_and_save(
        uid, plat, player_name, level, rank_score, rank_name, rank_div, stats_text,
    )

    if config.apex_only_text:
        await _player_matcher.finish(stats_text)

    rank_img_url = str(raw_data.get("rank_img", ""))
    if rank_img_url and rank_img_url not in _image_cache:
        await _download_image(rank_img_url)

    try:
        pic_bytes = await asyncio.to_thread(
            render_player_card, raw_data, changes, score_diff,
        )
    except Exception:
        logger.exception("Failed to render player card, falling back to text")
        await _player_matcher.finish(stats_text)
    await _player_matcher.finish(UniMessage.image(raw=pic_bytes))
