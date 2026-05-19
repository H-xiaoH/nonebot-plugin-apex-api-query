"""Apex Legends API 查询插件。

通过 Apex Legends Status API 获取玩家数据、地图轮换、服务器状态和顶尖猎杀者分数，
支持数据持久化和历史对比。
"""

import logging
from typing import Any

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

# NoneBot 的 require() 必须在 import 之前调用，用于加载依赖插件
require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")

from . import data_source as ds
from . import storage
from .config import Config
from .data import DEFAULT_PLATFORM, VALID_PLATFORMS

logger = logging.getLogger(__name__)

from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Option, on_alconna

__plugin_meta__ = PluginMetadata(
    name="Apex API Query",
    description="Apex Legends API 查询插件",
    usage="/apex",
    type="application",
    homepage="https://github.com/H-xiaoH/nonebot-plugin-apex-api-query",
    config=Config,
    # 继承 Alconna 插件支持的适配器，无需显式声明 OneBot/Console 等
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra={"author": "H-xiaoH <a412454922@gmail.com>"},
)

# 注册 /apex 命令，支持子命令（-m/-s/-p）和位置参数（玩家名、平台）
# Args 中 ? 表示可选参数，# 后面为参数标签（显示在帮助信息中）
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
async def apex_player(
    player_name: str | None = None, platform: str = DEFAULT_PLATFORM
) -> None:
    """处理玩家数据查询（$main 表示无子命令时触发的默认处理函数）。

    流程：
    1. 校验参数（玩家名必填、平台在允许范围内）
    2. 调用 API 获取玩家统计信息
    3. 提取关键字段（等级、段位、分数等）
    4. 存入数据库并与上次记录对比，附加变化信息
    5. 返回格式化的统计文本
    """
    if player_name is None:
        await apex.finish("请输入玩家名称")
    elif platform not in VALID_PLATFORMS:
        await apex.finish(f"平台参数错误，请输入 {'、'.join(VALID_PLATFORMS)}")

    # 返回值为 (格式化文本, 原始数据字典)，原始数据为 None 表示请求失败
    stats_text, raw_data = await ds.get_player_stats(player_name, platform)

    if raw_data is not None:
        # 从原始数据中提取需要持久化的字段，做类型安全转换
        level = _to_int(raw_data.get("level"), 0)
        rank_score = _to_int(raw_data.get("rank_score"), 0)
        rank_name = str(raw_data.get("rank_name") or "")
        rank_div = _to_int_optional(raw_data.get("rank_div"))
        uid = str(raw_data.get("uid") or "")
        plat = str(raw_data.get("platform") or platform)

        # 仅当 UID 有效时才进行数据库操作（部分玩家可能无 UID）
        if uid:
            try:
                # 查询该玩家上一次的统计数据
                previous = await storage.get_latest_record(uid, plat)
                current_stats = storage.PlayerStatsData(
                    level=level,
                    rank_score=rank_score,
                    rank_name=rank_name,
                    rank_div=rank_div,
                )
                # 将本次数据持久化到数据库
                await storage.save_record(
                    uid=uid,
                    player_name=player_name,
                    platform=plat,
                    stats=current_stats,
                )
                # 如果存在历史记录，生成数据变化对比并追加到输出文本
                if previous is not None:
                    prev_stats = storage.PlayerStatsData(
                        level=previous.level,
                        rank_score=previous.rank_score,
                        rank_name=previous.rank_name,
                        rank_div=previous.rank_div,
                    )
                    comparison = storage.format_comparison(current_stats, prev_stats)
                    stats_text += comparison
            except Exception:
                # 数据库异常不应阻断主流程，记录日志后仍返回 API 数据
                logger.exception("Failed to save or compare player stats")

    await apex.finish(stats_text)


def _to_int(value: Any, default: int = 0) -> int:
    """安全转换为 int，失败时返回默认值 0。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_int_optional(value: Any) -> int | None:
    """安全转换为 int，None 保持 None，转换失败返回 None。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@apex.assign("map")
async def apex_map() -> None:
    """处理 /apex -m 查询地图轮换。"""
    await apex.finish(await ds.get_map_rotation())


@apex.assign("server")
async def apex_server() -> None:
    """处理 /apex -s 查询服务器状态。"""
    await apex.finish(await ds.get_server_status())


@apex.assign("predator")
async def apex_predator() -> None:
    """处理 /apex -p 查询顶猎分数。"""
    await apex.finish(await ds.get_predator())
