"""Apex Legends Status API 数据获取层。

封装对 https://api.mozambiquehe.re 的 HTTP 请求与响应解析，
将所有 API 返回值转换为用户可读的中文格式化文本。
"""

import json
import logging
from typing import Any

import httpx

from .config import config
from .data import (
    DEFAULT_PLATFORM,
    OTHER_PLATFORMS,
    PLATFORM_DISPLAY,
    SELF_CORE_TESTS,
    SERVER_REGIONS,
    SERVER_SECTIONS,
    convert,
)

logger = logging.getLogger(__name__)

# Apex API 正常响应的 HTTP 状态码
HTTP_OK: int = 200


async def query_apex_api(
    server: str, params: dict[str, Any] | None = None
) -> httpx.Response:
    """向 Apex API 发送经过认证的 GET 请求。

    Args:
        server: API 端点路径（如 bridge、maprotation）
        params: 额外的查询参数（如 player、platform）

    Returns:
        原始 httpx.Response 对象

    超时设置为 30 秒，auth 参数自动携带 API Key。
    """
    payload: dict[str, Any] = {"auth": config.apex_api_key}
    if params:
        payload.update(params)
    async with httpx.AsyncClient() as client:
        return await client.get(
            f"{config.apex_api_url}/{server}", params=payload, timeout=30
        )


async def get_player_stats(
    player_name: str, platform: str = DEFAULT_PLATFORM
) -> tuple[str, dict[str, Any] | None]:
    """获取玩家统计数据并格式化返回。

    返回二元组：
    - 第一个元素：格式化的中文统计文本（失败时为错误提示）
    - 第二个元素：原始数据字典（用于数据库存储和历史对比），失败时为 None

    数据结构说明（来自 bridge 端点）：
    - global:     玩家基础信息（名称、UID、等级、段位、封禁状态）
    - realtime:   实时状态（大厅在线、可选传奇、当前模式等）
    """
    try:
        response = await query_apex_api(
            "bridge", {"player": player_name, "platform": platform}
        )
    except httpx.HTTPError:
        logger.exception("Failed to query player stats")
        return "查询失败: 网络请求错误", None

    # 非 200 响应直接透传原始内容，便于排查 API 侧问题
    if response.status_code != HTTP_OK:
        logger.warning(
            f"Player stats API returned {response.status_code}: {response.text}"
        )
        return response.text, None

    try:
        response_data: dict[str, Any] = response.json()
    except json.JSONDecodeError:
        logger.exception("Failed to parse player stats response")
        return "查询失败: API 返回数据格式错误", None

    # 从嵌套结构中提取各子模块，使用 get 和默认值防御 KeyError
    global_data: dict[str, Any] = response_data.get("global", {})
    realtime_data: dict[str, Any] = response_data.get("realtime", {})
    bans_data: dict[str, Any] = global_data.get("bans", {})
    rank_data: dict[str, Any] = global_data.get("rank", {})

    # 构建面向用户的 Key-Value 显示信息
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

    # 仅在玩家处于封禁状态时追加封禁信息
    if bans_data.get("isActive"):
        player_info.update(
            {
                "封禁状态": convert(bans_data.get("isActive")),
                "剩余秒数": bans_data.get("remainingSeconds"),
                "最后封禁原因": convert(bans_data.get("last_banReason")),
            }
        )

    # 拼接段位显示："大师 2" 或 "青铜"
    rank_div = rank_data.get("rankDiv")
    rank_name = convert(rank_data.get("rankName"))
    rank_display = f"{rank_name} {rank_div}" if rank_div else rank_name

    player_info.update(
        {
            "大逃杀分数": rank_data.get("rankScore"),
            "大逃杀段位": rank_display,
            "大厅状态": convert(realtime_data.get("lobbyState")),
            "在线": convert(realtime_data.get("isOnline")),
            "可加入": convert(realtime_data.get("canJoin")),
            "群满员": convert(realtime_data.get("partyFull")),
            "已选传奇": convert(realtime_data.get("selectedLegend")),
            "当前状态": convert(realtime_data.get("currentState")),
            "状态": convert(realtime_data.get("currentStateAsText")),
        }
    )

    # 提取精简的原始数据，用于持久化和历史对比
    raw_data: dict[str, Any] = {
        "uid": global_data.get("uid"),
        "name": global_data.get("name"),
        "platform": global_data.get("platform"),
        "level": global_data.get("level"),
        "rank_score": rank_data.get("rankScore"),
        # rank_name 提前翻译便于持久化存储为中文
        "rank_name": convert(rank_data.get("rankName")),
        "rank_div": rank_data.get("rankDiv"),
    }

    # 拼装输出文本，过滤值为 None 的字段避免显示空值
    return (
        "玩家信息:\n"
        + "\n".join(
            f"{key}: {value}"
            for key, value in player_info.items()
            if value is not None
        ),
        raw_data,
    )


def _format_map_data(map_data: dict[str, Any], mode_name: str) -> str:
    """格式化单个游戏模式的地图轮换信息。

    每个模式包含 current（当前地图）和 next（下张地图）两部分。
    """
    current = map_data.get("current", {})
    next_map = map_data.get("next", {})
    return (
        f"{mode_name}:\n"
        f"当前地图: {convert(current.get('map'))}\n"
        f"下个地图: {convert(next_map.get('map'))}\n"
        f"剩余时间: {convert(current.get('remainingTimer'))}\n\n"
    )


async def get_map_rotation() -> str:
    """获取当前地图轮换信息（大逃杀、排位赛、混录带）。

    使用 maprotation API v2 版本，返回三种模式的当前/下张地图及倒计时。
    """
    try:
        response = await query_apex_api("maprotation", {"version": "2"})
    except httpx.HTTPError:
        logger.exception("Failed to query map rotation")
        return "查询失败: 网络请求错误"

    if response.status_code != HTTP_OK:
        logger.warning(
            f"Map rotation API returned {response.status_code}: {response.text}"
        )
        return response.text

    try:
        response_data: dict[str, Any] = response.json()
    except json.JSONDecodeError:
        logger.exception("Failed to parse map rotation response")
        return "查询失败: API 返回数据格式错误"

    battle_royale = response_data.get("battle_royale", {})
    ranked = response_data.get("ranked", {})
    ltm = response_data.get("ltm", {})

    data = (
        _format_map_data(battle_royale, "大逃杀")
        + _format_map_data(ranked, "排位赛联盟")
        + _format_map_data(ltm, "混录带")
    )
    return data.strip()


async def get_server_status() -> str:
    """获取 Apex 各区域服务器运行状态。

    查询结果按分区展示（Origin 登录、EA 服务、平台 API 等），
    每个分区下按区域或服务名列出 UP/DOWN/SLOW/OVERLOADED 状态。
    """
    try:
        response = await query_apex_api("servers")
    except httpx.HTTPError:
        logger.exception("Failed to query server status")
        return "查询失败: 网络请求错误"

    if response.status_code != HTTP_OK:
        logger.warning(
            f"Server status API returned {response.status_code}: {response.text}"
        )
        return response.text

    try:
        response_data: dict[str, Any] = response.json()
    except json.JSONDecodeError:
        logger.exception("Failed to parse server status response")
        return "查询失败: API 返回数据格式错误"

    data = ""
    # 遍历顶级分区，按分区类型选用对应的子项映射
    for section_name, section_key in SERVER_SECTIONS.items():
        data += f"{section_name}:\n"
        section_data = response_data.get(section_key, {})
        if section_key == "selfCoreTest":
            for test_name, test_key in SELF_CORE_TESTS.items():
                status = convert(section_data.get(test_key, {}).get("Status"))
                data += f"{test_name}: {status}\n"
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in OTHER_PLATFORMS.items():
                status = convert(section_data.get(platform_key, {}).get("Status"))
                data += f"{platform_name}: {status}\n"
        else:
            for region_name, region_key in SERVER_REGIONS.items():
                status = convert(section_data.get(region_key, {}).get("Status"))
                data += f"{region_name}: {status}\n"
        data += "\n"

    data += "Data from apexlegendsstatus.com"
    return data


async def get_predator() -> str:
    """查询顶尖猎杀者分数（各平台大师/猎杀者排名数据）。

    返回各平台（PC/PS4/X1/Switch）的猎杀者人数、最低分数及大师人数。
    """
    try:
        response = await query_apex_api("predator")
    except httpx.HTTPError:
        logger.exception("Failed to query predator")
        return "查询失败: 网络请求错误"

    if response.status_code != HTTP_OK:
        logger.warning(f"Predator API returned {response.status_code}: {response.text}")
        return response.text

    try:
        response_data: dict[str, Any] = response.json()
    except json.JSONDecodeError:
        logger.exception("Failed to parse predator response")
        return "查询失败: API 返回数据格式错误"

    # RP 字段包含各平台排位数据
    rp = response_data.get("RP", {})

    data = "大逃杀:\n"
    for platform_key, platform_name in PLATFORM_DISPLAY.items():
        platform_data = rp.get(platform_key, {})
        data += (
            f"{platform_name}:\n"
            f"顶尖猎杀者人数: {platform_data.get('foundRank', 'N/A')}\n"
            f"顶尖猎杀者分数: {platform_data.get('val', 'N/A')}\n"
            f"顶尖猎杀者UID: {platform_data.get('uid', 'N/A')}\n"
            "大师和顶尖猎杀者人数: "
            f"{platform_data.get('totalMastersAndPreds', 'N/A')}\n\n"
        )
    return data.strip()
