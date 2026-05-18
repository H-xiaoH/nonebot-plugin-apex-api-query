from typing import Any, Optional

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from . import data_source as ds
from . import storage
from .config import Config

require("nonebot_plugin_orm")
require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Option, on_alconna

# 插件元数据
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

# 注册命令
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


# 注册命令处理函数
@apex.assign("$main")
async def apex_player(player_name: Optional[str] = None, platform: str = "PC") -> None:
    """查询玩家数据。"""
    if player_name is None:
        await apex.finish("请输入玩家名称")
    elif platform not in ["PC", "PS4", "X1", "SWITCH"]:
        await apex.finish("平台参数错误，请输入 PC、PS4、X1 或 SWITCH")
    assert player_name is not None

    stats_text, raw_data = await ds.get_player_stats(player_name, platform)

    if raw_data is not None:
        level = _to_int(raw_data.get("level"), 0)
        rank_score = _to_int(raw_data.get("rank_score"), 0)
        rank_name = str(raw_data.get("rank_name") or "")
        rank_div = _to_int_optional(raw_data.get("rank_div"))
        uid = str(raw_data.get("uid") or "")
        plat = str(raw_data.get("platform") or platform)

        if uid:
            previous = await storage.get_latest_record(uid, plat)
            await storage.save_record(
                uid=uid,
                player_name=player_name,
                platform=plat,
                level=level,
                rank_score=rank_score,
                rank_name=rank_name,
                rank_div=rank_div,
            )
            if previous is not None:
                comparison = storage.format_comparison(
                    level=level,
                    rank_score=rank_score,
                    rank_name=rank_name,
                    rank_div=rank_div,
                    prev_level=previous.level,
                    prev_rank_score=previous.rank_score,
                    prev_rank_name=previous.rank_name,
                    prev_rank_div=previous.rank_div,
                )
                stats_text += comparison

    await apex.finish(stats_text)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_int_optional(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# 处理地图轮换
@apex.assign("map")
async def apex_map() -> None:
    """查询地图轮换信息。"""
    await apex.finish(await ds.get_map_rotation())


# 处理服务器状态
@apex.assign("server")
async def apex_server() -> None:
    """查询服务器状态。"""
    await apex.finish(await ds.get_server_status())


# 处理猎杀者信息
@apex.assign("predator")
async def apex_predator() -> None:
    """查询顶猎分数信息。"""
    await apex.finish(await ds.get_predator())
