from typing import Optional
from .config import config
from .data import convert
import httpx

# 读取插件配置文件
API_KEY = config.apex_api_key
API_URL: str = "https://api.mozambiquehe.re"

# 请求查询API
async def query_apex_api(server: str, params: Optional[dict] = None):
    # 请求参数
    payload = {"auth": API_KEY}
    # 合并请求参数
    if params:
        payload.update(params)
    # 发送请求
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/{server}", params=payload, timeout=None)
        return response

# 获取玩家数据
async def get_player_stats(player_name: str, platform: str = "PC"):
    # 请求参数
    response = await query_apex_api("bridge", {"player": player_name, "platform": platform})
    response_data = response.json()
    
    # 处查API响应状态码
    if response.status_code != 200:
        return response.text

    # 解析数据
    global_data = response_data["global"]
    realtime_data = response_data["realtime"]
    bans_data = global_data.get("bans", {})
    rank_data = global_data.get("rank", {})
    
    # 构建玩家信息
    player_info = {
        "名称": global_data.get("name"),
        "UID": global_data.get("uid"),
        "平台": global_data.get("platform"),
        "等级": global_data.get("level"),
        "距下一级百分比": f"{global_data.get('toNextLevelPercent')}%",
    }

    # 如果封禁状态为 True，则追加封禁相关信息
    if bans_data.get("isActive"):
        player_info.update({
            "封禁状态": convert(bans_data.get("isActive")),
            "剩余秒数": bans_data.get("remainingSeconds"),
            "最后封禁原因": convert(bans_data.get("last_banReason")),
        })

    # 处理大逃杀段位信息
    rank_div = rank_data.get("rankDiv")
    rank_name = convert(rank_data.get("rankName"))
    rank_display = f"{rank_name} {rank_div}" if rank_div != 0 else rank_name

    # 继续构建其他玩家信息
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
    # 将玩家信息转换为字符串
    data = "玩家信息:\n" + "\n".join(f"{key}: {value}" for key, value in player_info.items())
    return data

# 获取地图轮换信息
async def get_map_rotation():
    # 查询API获取地图轮换信息
    response = await query_apex_api("maprotation", {"version": "2"})
    response_data = response.json()

    # 检查API响应状态码
    if response.status_code != 200:
        return response.text

    # 格式化地图轮换信息
    def format_map_data(map_data, mode_name):
        return (
            f'{mode_name}:\n'
            f'当前地图: {convert(map_data["current"]["map"])}\n'
            f'下个地图: {convert(map_data["next"]["map"])}\n'
            f'剩余时间: {convert(map_data["current"]["remainingTimer"])}\n\n'
        )

    # 获取并格式化大逃杀、排位赛联盟和混录带的地图信息
    battle_royale = response_data["battle_royale"]
    ranked = response_data["ranked"]
    ltm = response_data["ltm"]

    # 组合所有模式的地图信息
    data = (
        format_map_data(battle_royale, "大逃杀") +
        format_map_data(ranked, "排位赛联盟") +
        format_map_data(ltm, "混录带")
    )
    return data.strip()

# 获取服务器状态
async def get_server_status():
    # 查询API获取服务器状态
    response = await query_apex_api("servers")
    response_data = response.json()

    # 检查响应状态码
    if response.status_code != 200:
        return response.text

    # 定义部分及其对应的键
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

    # 获取数据
    data = ""
    for section_name, section_key in sections.items():
        data += f"{section_name}:\n"
        # 根据 section_key 获取对应的数据
        if section_key == 'selfCoreTest':
            for test_name, test_key in self_core_tests.items():
                status = convert(response_data.get(section_key, {}).get(test_key, {}).get('Status'))
                data += f"{test_name}: {status}\n"
        elif section_key == 'otherPlatforms':
            for platform_name, platform_key in other_platforms.items():
                status = convert(response_data.get(section_key, {}).get(platform_key, {}).get('Status'))
                data += f"{platform_name}: {status}\n"
        else:
            for region_name, region_key in regions.items():
                status = convert(response_data.get(section_key, {}).get(region_key, {}).get('Status'))
                data += f"{region_name}: {status}\n"
        data += "\n"

    data += "Data from apexlegendsstatus.com"
    return data

# 查询猎杀数据
async def get_predator():
    response = await query_apex_api("predator")
    response_data = response.json()
    
    # 检查响应状态码
    if response.status_code != 200:
        return response.text

    # 解析数据
    rp = response_data.get('RP', {})
    platforms = {
        'PC': 'PC 端',
        'PS4': 'PS4/5 端',
        'X1': 'Xbox 端',
        'SWITCH': 'Switch 端'
    }

    # 构建数据
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

