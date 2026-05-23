import logging
from typing import Any

from nonebot import get_driver, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")

from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Option, on_alconna

from . import data_source as ds
from . import image, storage
from .config import Config, config
from .data import DEFAULT_PLATFORM, VALID_PLATFORMS
from .models import PlayerStats

driver = get_driver()


@driver.on_startup
async def _auto_init_apex_tables() -> None:
    """Startup hook: auto-create the PlayerStats table if it does not exist."""
    from nonebot_plugin_orm import _engines

    async with _engines[""].begin() as conn:
        await conn.run_sync(PlayerStats.__table__.create, checkfirst=True)

logger = logging.getLogger(__name__)

__plugin_meta__ = PluginMetadata(
    name="Apex API Query",
    description="Apex Legends API 查询插件",
    usage="/apex",
    type="application",
    homepage="https://github.com/H-xiaoH/nonebot-plugin-apex-api-query",
    config=Config,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra={"author": "H-xiaoH <a412454922@gmail.com>"},
)

apex = on_alconna(
    Alconna(
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
    )
)


@apex.assign("$main")
async def apex_player(  # noqa: C901
    player_name: str | None = None, platform: str = DEFAULT_PLATFORM
) -> None:
    """平台玩家查询：获取玩家统计数据，比对历史变化并追加变化标记。

    Args:
        player_name: 要查询的玩家名称。为 None 时提示用户输入。
        platform: 查询平台，默认为 PC。不在合法平台列表中时提示错误。
    """
    if player_name is None:
        await apex.finish("请输入玩家名称")
    elif platform not in VALID_PLATFORMS:
        await apex.finish(f"平台参数错误，请输入 {'、'.join(VALID_PLATFORMS)}")

    stats_text, raw_data = await ds.get_player_stats(player_name, platform)

    if raw_data is None:
        await apex.finish(stats_text)

    level = _to_int(raw_data.get("level"), 0)
    rank_score = _to_int(raw_data.get("rank_score"), 0)
    rank_name = str(raw_data.get("rank_name") or "")
    rank_div = _to_int_optional(raw_data.get("rank_div"))
    uid = str(raw_data.get("uid") or "")
    plat = str(raw_data.get("platform") or platform)
    changes: dict[str, str] = {}
    score_diff: int | None = None

    if uid:
        try:
            previous = await storage.get_latest_record(uid, plat)
            current_stats = storage.PlayerStatsData(
                level=level,
                rank_score=rank_score,
                rank_name=rank_name,
                rank_div=rank_div,
            )
            await storage.save_record(
                uid=uid,
                player_name=player_name,
                platform=plat,
                stats=current_stats,
            )
            if previous is not None:
                score_diff = rank_score - previous.rank_score
                prev_stats = storage.PlayerStatsData(
                    level=previous.level,
                    rank_score=previous.rank_score,
                    rank_name=previous.rank_name,
                    rank_div=previous.rank_div,
                )
                changes = storage.format_comparison(current_stats, prev_stats)
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

    if config.apex_only_text:
        await apex.finish(stats_text)

    try:
        pic_bytes = await image.render_player_card(
            raw_data, changes or None, score_diff
        )
    except Exception:
        logger.exception("Failed to render player card, falling back to text")
        await apex.finish(stats_text)
    await apex.finish(MessageSegment.image(pic_bytes))


def _to_int(value: Any, default: int = 0) -> int:
    """安全转换为 int，转换失败返回默认值。

    Args:
        value: 待转换的任意值。
        default: 转换失败时的回退值，默认 0。

    Returns:
        转换后的整数。
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_int_optional(value: Any) -> int | None:
    """安全转换为 int，None 保持 None，其他转换失败也返回 None。

    Args:
        value: 待转换的任意值，可为 None。

    Returns:
        转换后的整数或 None。
    """
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@apex.assign("map")
async def apex_map() -> None:
    """地图轮换查询：获取当前地图轮换并渲染图片，失败回退文本。"""
    if config.apex_only_text:
        await apex.finish(await ds.get_map_rotation())
    data = await ds.get_map_rotation_data()
    if isinstance(data, str):
        await apex.finish(data)
    try:
        pic_bytes = await image.render_map_card(data)
    except Exception:
        logger.exception("Failed to render map card, falling back to text")
        await apex.finish(await ds.get_map_rotation())
    await apex.finish(MessageSegment.image(pic_bytes))


@apex.assign("server")
async def apex_server() -> None:
    """服务器状态查询：获取各分区服务器状态并渲染图片，失败回退文本。"""
    if config.apex_only_text:
        await apex.finish(await ds.get_server_status())
    data = await ds.get_server_status_data()
    if isinstance(data, str):
        await apex.finish(data)
    try:
        pic_bytes = await image.render_server_card(data)
    except Exception:
        logger.exception("Failed to render server card, falling back to text")
        await apex.finish(await ds.get_server_status())
    await apex.finish(MessageSegment.image(pic_bytes))


@apex.assign("predator")
async def apex_predator() -> None:
    """顶猎查询：获取各平台顶尖猎杀者排行并渲染图片，失败回退文本。"""
    if config.apex_only_text:
        await apex.finish(await ds.get_predator())
    data = await ds.get_predator_data()
    if isinstance(data, str):
        await apex.finish(data)
    try:
        pic_bytes = await image.render_predator_card(data)
    except Exception:
        logger.exception("Failed to render predator card, falling back to text")
        await apex.finish(await ds.get_predator())
    await apex.finish(MessageSegment.image(pic_bytes))
