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

HTTP_OK = 200


class ApexAPIError(Exception):
    """API 请求或解析失败时抛出，携带用户可见的错误信息。"""


async def query_apex_api(
    server: str, params: dict[str, Any] | None = None
) -> httpx.Response:
    """向 Apex API 发起 GET 请求并返回响应。

    Args:
        server: API 端点名称，如 bridge、maprotation、servers、predator。
        params: 额外查询参数，会与认证信息合并传递。

    Returns:
        httpx.Response 对象，超时设置为 30 秒。
    """
    payload: dict[str, Any] = {"auth": config.apex_api_key}
    if params:
        payload.update(params)
    async with httpx.AsyncClient() as client:
        return await client.get(
            f"{config.apex_api_url}/{server}", params=payload, timeout=30
        )


async def _fetch(
    endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """发送 API 请求并返回解析后的 JSON 数据。

    Raises:
        ApexAPIError: 请求失败、非 200 响应或 JSON 解析失败时抛出。
    """
    try:
        response = await query_apex_api(endpoint, params)
    except httpx.HTTPError as e:
        logger.exception(f"Failed to query {endpoint}")
        raise ApexAPIError("查询失败: 网络请求错误") from e  # noqa: TRY003
    if response.status_code != HTTP_OK:
        logger.warning(
            f"API {endpoint} returned {response.status_code}: {response.text}"
        )
        raise ApexAPIError(response.text)
    try:
        return response.json()
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse {endpoint} response")
        raise ApexAPIError("查询失败: API 返回数据格式错误") from e  # noqa: TRY003


async def get_player_stats(
    player_name: str, platform: str = DEFAULT_PLATFORM
) -> tuple[str, dict[str, Any] | None]:
    """查询玩家统计数据，返回格式化文本和原始数据。

    Args:
        player_name: 玩家名称。
        platform: 查询平台，默认为 PC。

    Returns:
        (格式化输出文本, 原始数据字典) 元组。原始数据可能为 None（请求失败时）。
    """
    try:
        response_data = await _fetch(
            "bridge", {"player": player_name, "platform": platform}
        )
    except ApexAPIError as e:
        return str(e), None

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
        player_info.update(
            {
                "封禁状态": convert(bans_data.get("isActive")),
                "剩余秒数": bans_data.get("remainingSeconds"),
                "最后封禁原因": convert(bans_data.get("last_banReason")),
            }
        )

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

    Args:
        map_data: API 返回的单个模式地图数据（含 current/next）。
        mode_name: 模式中文名，如「大逃杀」「排位赛联盟」「混录带」。

    Returns:
        格式化后的地图轮换文本块。
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
    """获取当前地图轮换信息（大逃杀、排位赛联盟、混录带）。

    Returns:
        格式化的地图轮换文本。
    """
    try:
        response_data = await _fetch("maprotation", {"version": "2"})
    except ApexAPIError as e:
        return str(e)

    battle_royale = response_data.get("battle_royale", {})
    ranked = response_data.get("ranked", {})
    ltm = response_data.get("ltm", {})

    data = (
        _format_map_data(battle_royale, "大逃杀")
        + _format_map_data(ranked, "排位赛联盟")
        + _format_map_data(ltm, "混录带")
    )
    return data.strip()


async def get_map_rotation_data() -> dict[str, Any] | str:
    """从 apexlegendsstatus.com 获取地图轮换结构化数据（含图片 asset URL）。

    Returns:
        dict: 含 battle_royale/ranked/ltm 的完整 API 响应数据。
        请求失败时返回错误信息字符串。
    """
    payload: dict[str, Any] = {"auth": config.apex_api_key, "version": "2"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{config.apex_map_api_url}/maprotation",
                params=payload,
                timeout=30,
            )
        if resp.status_code != HTTP_OK:
            logger.warning(
                f"Map API returned {resp.status_code}: {resp.text}"
            )
            return f"地图查询失败: {resp.status_code}"
        return resp.json()
    except httpx.HTTPError:
        logger.exception("Failed to query maprotation API")
        return "地图查询失败: 网络请求错误"
    except json.JSONDecodeError:
        logger.exception("Failed to parse maprotation response")
        return "地图查询失败: API 返回数据格式错误"


async def get_server_status_data() -> list[dict[str, Any]] | str:
    """获取各分区服务器运行状态结构化数据。

    Returns:
        list[dict]: 按 section 分组的数据列表，每项含 section_name, section_key, rows。
        请求失败时返回错误信息字符串。
    """
    try:
        response_data = await _fetch("servers")
    except ApexAPIError as e:
        return str(e)

    sections: list[dict[str, Any]] = []
    for section_name, section_key in SERVER_SECTIONS.items():
        section_rows: list[dict[str, Any]] = []
        section_data = response_data.get(section_key, {})
        if section_key == "selfCoreTest":
            for test_name, test_key in SELF_CORE_TESTS.items():
                entry = section_data.get(test_key, {})
                section_rows.append({
                    "name": test_name,
                    "status": entry.get("Status", ""),
                    "response_time": entry.get("ResponseTime", -1),
                })
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in OTHER_PLATFORMS.items():
                entry = section_data.get(platform_key, {})
                section_rows.append({
                    "name": platform_name,
                    "status": entry.get("Status", ""),
                    "response_time": entry.get("ResponseTime", -1),
                })
        else:
            for region_name, region_key in SERVER_REGIONS.items():
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


async def get_server_status() -> str:
    """获取各分区服务器运行状态。

    Returns:
        按分区和区域组织的服务器状态文本。
    """
    try:
        response_data = await _fetch("servers")
    except ApexAPIError as e:
        return str(e)

    lines: list[str] = []
    for section_name, section_key in SERVER_SECTIONS.items():
        lines.append(f"{section_name}:")
        section_data = response_data.get(section_key, {})
        if section_key == "selfCoreTest":
            for test_name, test_key in SELF_CORE_TESTS.items():
                status = convert(section_data.get(test_key, {}).get("Status"))
                lines.append(f"{test_name}: {status}")
        elif section_key == "otherPlatforms":
            for platform_name, platform_key in OTHER_PLATFORMS.items():
                status = convert(section_data.get(platform_key, {}).get("Status"))
                lines.append(f"{platform_name}: {status}")
        else:
            for region_name, region_key in SERVER_REGIONS.items():
                status = convert(section_data.get(region_key, {}).get("Status"))
                lines.append(f"{region_name}: {status}")
        lines.append("")

    lines.append("Data from apexlegendsstatus.com")
    return "\n".join(lines)


async def get_predator_data() -> dict[str, Any] | str:
    """获取各平台顶尖猎杀者排行结构化数据。

    Returns:
        dict: 按平台分组的排行数据。请求失败时返回错误信息字符串。
    """
    try:
        response_data = await _fetch("predator")
    except ApexAPIError as e:
        return str(e)
    rp = response_data.get("RP", {})
    result: dict[str, Any] = {}
    for platform_key, platform_name in PLATFORM_DISPLAY.items():
        platform_data = rp.get(platform_key, {})
        result[platform_key] = {
            "name": platform_name,
            "found_rank": platform_data.get("foundRank", 0),
            "val": platform_data.get("val", 0),
            "uid": platform_data.get("uid", ""),
            "total_masters": platform_data.get("totalMastersAndPreds", 0),
        }
    return result


async def get_predator() -> str:
    """获取各平台顶尖猎杀者排行数据。

    Returns:
        按平台组织的排行文本，含人数、分数和 UID。
    """
    try:
        response_data = await _fetch("predator")
    except ApexAPIError as e:
        return str(e)

    rp = response_data.get("RP", {})

    lines: list[str] = ["大逃杀:"]
    for platform_key, platform_name in PLATFORM_DISPLAY.items():
        platform_data = rp.get(platform_key, {})
        lines.append(
            f"{platform_name}:\n"
            f"顶尖猎杀者人数: {platform_data.get('foundRank', 'N/A')}\n"
            f"顶尖猎杀者分数: {platform_data.get('val', 'N/A')}\n"
            f"顶尖猎杀者UID: {platform_data.get('uid', 'N/A')}\n"
            "大师和顶尖猎杀者人数: "
            f"{platform_data.get('totalMastersAndPreds', 'N/A')}"
        )
    return "\n\n".join(lines)
