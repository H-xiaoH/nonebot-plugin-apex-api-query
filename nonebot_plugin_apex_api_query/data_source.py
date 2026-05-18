import json
import logging
from typing import Any, Optional

import httpx

from .config import config
from .data import convert

logger = logging.getLogger(__name__)

HTTP_OK: int = 200
API_URL: str = "https://api.mozambiquehe.re"


async def query_apex_api(
    server: str, params: Optional[dict[str, Any]] = None
) -> httpx.Response:
    """向 Apex API 发送 GET 请求。"""
    payload: dict[str, Any] = {"auth": config.apex_api_key}
    if params:
        payload.update(params)
    async with httpx.AsyncClient() as client:
        return await client.get(f"{API_URL}/{server}", params=payload, timeout=30)


async def get_player_stats(
    player_name: str, platform: str = "PC"
) -> tuple[str, Optional[dict[str, Any]]]:
    """获取玩家统计数据并格式化返回。同时返回原始数据用于存储对比。"""
    try:
        response = await query_apex_api(
            "bridge", {"player": player_name, "platform": platform}
        )
    except httpx.HTTPError:
        logger.exception("Failed to query player stats")
        return "查询失败: 网络请求错误", None

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

    global_data: dict[str, Any] = response_data.get("global", {})
    realtime_data: dict[str, Any] = response_data.get("realtime", {})
    bans_data: dict[str, Any] = global_data.get("bans", {})
    rank_data: dict[str, Any] = global_data.get("rank", {})

    # 构建玩家信息
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

    # 如果封禁状态为 True，则追加封禁相关信息
    if bans_data.get("isActive"):
        player_info.update(
            {
                "封禁状态": convert(bans_data.get("isActive")),
                "剩余秒数": bans_data.get("remainingSeconds"),
                "最后封禁原因": convert(bans_data.get("last_banReason")),
            }
        )

    # 处理大逃杀段位信息
    rank_div = rank_data.get("rankDiv")
    rank_name = convert(rank_data.get("rankName"))
    rank_display = f"{rank_name} {rank_div}" if rank_div else rank_name

    # 继续构建其他玩家信息
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
    # 提取原始数据用于存储对比
    raw_data: dict[str, Any] = {
        "uid": global_data.get("uid"),
        "name": global_data.get("name"),
        "platform": global_data.get("platform"),
        "level": global_data.get("level"),
        "rank_score": rank_data.get("rankScore"),
        "rank_name": convert(rank_data.get("rankName")),
        "rank_div": rank_data.get("rankDiv"),
    }

    # 将玩家信息转换为字符串，过滤 None 值
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
    """格式化单个模式的地图数据。"""
    current = map_data.get("current", {})
    next_map = map_data.get("next", {})
    return (
        f"{mode_name}:\n"
        f"当前地图: {convert(current.get('map'))}\n"
        f"下个地图: {convert(next_map.get('map'))}\n"
        f"剩余时间: {convert(current.get('remainingTimer'))}\n\n"
    )


async def get_map_rotation() -> str:
    """获取地图轮换信息并格式化返回。"""
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
    """获取服务器状态并格式化返回。"""
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

    sections = {
        "Origin 登录": "Origin_login",
        "EA 融合": "EA_novafusion",
        "EA 账户": "EA_accounts",
        "Apex 跨平台验证": "ApexOauth_Crossplay",
        "自我核心测试": "selfCoreTest",
        "其他平台": "otherPlatforms",
    }
    regions = {
        "欧盟西部": "EU-West",
        "欧盟东部": "EU-East",
        "美国西部": "US-West",
        "美国中部": "US-Central",
        "美国东部": "US-East",
        "南美洲": "SouthAmerica",
        "亚洲": "Asia",
    }
    self_core_tests = {
        "网站状态": "Status-website",
        "统计 API": "Stats-API",
        "溢出 #1": "Overflow-#1",
        "溢出 #2": "Overflow-#2",
        "Origin API": "Origin-API",
        "Playstation API": "Playstation-API",
        "Xbox API": "Xbox-API",
    }
    other_platforms = {
        "Playstation Network": "Playstation-Network",
        "Xbox Live": "Xbox-Live",
    }

    data = ""
    for section_name, section_key in sections.items():
        data += f"{section_name}:\n"
        section_data = response_data.get(section_key, {})
        if section_key == "selfCoreTest":
            for test_name, test_key in self_core_tests.items():
                status = convert(section_data.get(test_key, {}).get("Status"))
                data += f"{test_name}: {status}\n"
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in other_platforms.items():
                status = convert(section_data.get(platform_key, {}).get("Status"))
                data += f"{platform_name}: {status}\n"
        else:
            for region_name, region_key in regions.items():
                status = convert(section_data.get(region_key, {}).get("Status"))
                data += f"{region_name}: {status}\n"
        data += "\n"

    data += "Data from apexlegendsstatus.com"
    return data


async def get_predator() -> str:
    """查询顶猎分数并格式化返回。"""
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

    rp = response_data.get("RP", {})
    platforms = {
        "PC": "PC 端",
        "PS4": "PS4/5 端",
        "X1": "Xbox 端",
        "SWITCH": "Switch 端",
    }

    data = "大逃杀:\n"
    for platform_key, platform_name in platforms.items():
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
