import json
import logging
from typing import Optional, Tuple, Any

from .config import config
from .data import convert
import httpx

logger = logging.getLogger(__name__)

API_URL: str = "https://api.mozambiquehe.re"


# 请求查询API
async def query_apex_api(server: str, params: Optional[dict] = None):
    payload = {"auth": config.apex_api_key}
    if params:
        payload.update(params)
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/{server}", params=payload, timeout=30)
        return response


async def _fetch_api(endpoint: str, params: Optional[dict] = None,
                     error_hint: str = "") -> Tuple[Optional[Any], Optional[str]]:
    """统一 API 请求封装，返回 (data, error)。"""
    try:
        response = await query_apex_api(endpoint, params)
    except httpx.HTTPError as e:
        logger.error(f"Failed to query {error_hint}: {e}")
        return None, "查询失败: 网络请求错误"

    if response.status_code != 200:
        logger.warning(f"{error_hint} API returned {response.status_code}: {response.text}")
        try:
            error_data = response.json()
            error_msg = error_data.get("Error", str(error_data))
        except (json.JSONDecodeError, AttributeError):
            error_msg = f"HTTP {response.status_code}"
        return None, f"查询失败: {error_msg}"

    try:
        return response.json(), None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {error_hint} response: {e}")
        return None, "查询失败: API 返回数据格式错误"


# 获取玩家数据
async def get_player_stats(player_name: str, platform: str = "PC"):
    response_data, error = await _fetch_api(
        "bridge", {"player": player_name, "platform": platform}, "player stats"
    )
    if error:
        return error

    global_data = response_data.get("global", {})
    realtime_data = response_data.get("realtime", {})
    bans_data = global_data.get("bans", {})
    rank_data = global_data.get("rank", {})

    player_info = {
        "名称": global_data.get("name"),
        "UID": global_data.get("uid"),
        "平台": global_data.get("platform"),
        "等级": global_data.get("level"),
        "距下一级百分比": f"{global_data.get('toNextLevelPercent', 0)}%",
    }

    if bans_data.get("isActive"):
        player_info.update({
            "封禁状态": convert(bans_data.get("isActive")),
            "剩余秒数": bans_data.get("remainingSeconds"),
            "最后封禁原因": convert(bans_data.get("last_banReason")),
        })

    rank_div = rank_data.get("rankDiv")
    rank_name = convert(rank_data.get("rankName"))
    rank_display = f"{rank_name} {rank_div}" if rank_div not in (None, 0) else rank_name

    player_info.update({
        "大逃杀分数": rank_data.get("rankScore"),
        "大逃杀段位": rank_display,
        "大厅状态": convert(realtime_data.get("lobbyState")),
        "在线": convert(realtime_data.get("isOnline")),
        "可加入": convert(realtime_data.get("canJoin")),
        "群满员": convert(realtime_data.get("partyFull")),
        "已选传奇": convert(realtime_data.get("selectedLegend")),
        "当前状态": convert(realtime_data.get("currentState")),
        "状态": realtime_data.get("currentStateAsText")
    })
    return "玩家信息:\n" + "\n".join(f"{key}: {value}" for key, value in player_info.items())


# 获取地图轮换信息
async def get_map_rotation():
    response_data, error = await _fetch_api(
        "maprotation", {"version": "2"}, "map rotation"
    )
    if error:
        return error

    def format_map_data(map_data, mode_name):
        current = map_data.get("current", {})
        next_map = map_data.get("next", {})
        return (
            f'{mode_name}:\n'
            f'当前地图: {convert(current.get("map"))}\n'
            f'下个地图: {convert(next_map.get("map"))}\n'
            f'剩余时间: {convert(current.get("remainingTimer"))}\n\n'
        )

    battle_royale = response_data.get("battle_royale", {})
    ranked = response_data.get("ranked", {})
    ltm = response_data.get("ltm", {})

    data = (
        format_map_data(battle_royale, "大逃杀") +
        format_map_data(ranked, "排位赛联盟") +
        format_map_data(ltm, "混录带")
    )
    return data.strip()


# 获取服务器状态
async def get_server_status():
    response_data, error = await _fetch_api("servers", error_hint="server status")
    if error:
        return error

    sections = {
        'Origin 登录': 'Origin_login',
        'EA 融合': 'EA_novafusion',
        'EA 账户': 'EA_accounts',
        'Apex 跨平台验证': 'ApexOauth_Crossplay',
        '自我核心测试': 'selfCoreTest',
        '其他平台': 'otherPlatforms'
    }
    regions = {
        '欧盟西部': 'EU-West',
        '欧盟东部': 'EU-East',
        '美国西部': 'US-West',
        '美国中部': 'US-Central',
        '美国东部': 'US-East',
        '南美洲': 'SouthAmerica',
        '亚洲': 'Asia'
    }
    self_core_tests = {
        '网站状态': 'Status-website',
        '统计 API': 'Stats-API',
        '溢出 #1': 'Overflow-#1',
        '溢出 #2': 'Overflow-#2',
        'Origin API': 'Origin-API',
        'Playstation API': 'Playstation-API',
        'Xbox API': 'Xbox-API'
    }
    other_platforms = {
        'Playstation Network': 'Playstation-Network',
        'Xbox Live': 'Xbox-Live'
    }

    data = ""
    for section_name, section_key in sections.items():
        data += f"{section_name}:\n"
        section_data = response_data.get(section_key, {})
        if section_key == 'selfCoreTest':
            for test_name, test_key in self_core_tests.items():
                status = convert(section_data.get(test_key, {}).get('Status'))
                data += f"{test_name}: {status}\n"
        elif section_key == 'otherPlatforms':
            for platform_name, platform_key in other_platforms.items():
                status = convert(section_data.get(platform_key, {}).get('Status'))
                data += f"{platform_name}: {status}\n"
        else:
            for region_name, region_key in regions.items():
                status = convert(section_data.get(region_key, {}).get('Status'))
                data += f"{region_name}: {status}\n"
        data += "\n"

    data += "Data from apexlegendsstatus.com"
    return data


# 查询猎杀数据
async def get_predator():
    response_data, error = await _fetch_api("predator", error_hint="predator")
    if error:
        return error

    rp = response_data.get('RP', {})
    platforms = {
        'PC': 'PC 端',
        'PS4': 'PS4/5 端',
        'X1': 'Xbox 端',
        'SWITCH': 'Switch 端'
    }

    data = "大逃杀:\n"
    for platform_key, platform_name in platforms.items():
        platform_data = rp.get(platform_key, {})
        data += (
            f"{platform_name}:\n"
            f"顶尖猎杀者人数: {platform_data.get('foundRank', 'N/A')}\n"
            f"顶尖猎杀者分数: {platform_data.get('val', 'N/A')}\n"
            f"顶尖猎杀者UID: {platform_data.get('uid', 'N/A')}\n"
            f"大师和顶尖猎杀者人数: {platform_data.get('totalMastersAndPreds', 'N/A')}\n\n"
        )
    return data.strip()
