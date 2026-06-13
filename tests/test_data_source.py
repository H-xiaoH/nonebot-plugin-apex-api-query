"""Tests for data_source.py — async API functions with httpx mocking.

Pattern A: _fetch-based functions (api.mozambiquehe.re) raise ApexAPIError.
Pattern B: get_map_rotation_data (api.apexlegendsstatus.com) returns error strings.

All plugin imports happen inside test functions (NOT at module level) because
the plugin's __init__.py has module-level NoneBot side effects.
"""

from __future__ import annotations

import httpx
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern A — _fetch based (mozambiquehe.re domain, raises ApexAPIError)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_fetch_happy_path(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """_fetch returns parsed dict on 200 OK with valid JSON."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/bridge?auth=test-key",
        json={"status": "ok", "data": {"foo": 42}},
    )
    from nonebot_plugin_apex_api_query.data_source import _fetch

    result = await _fetch("bridge")
    assert result == {"status": "ok", "data": {"foo": 42}}


async def test_fetch_http_error(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """_fetch raises ApexAPIError('查询失败: 网络请求错误') on httpx.HTTPError."""
    httpx_mock.add_exception(
        url="https://api.mozambiquehe.re/bridge?auth=test-key",
        exception=httpx.ConnectError("connection refused"),
    )
    from nonebot_plugin_apex_api_query.data_source import ApexAPIError, _fetch

    with pytest.raises(ApexAPIError, match="查询失败: 网络请求错误"):
        await _fetch("bridge")


async def test_fetch_non_200(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """_fetch raises ApexAPIError on non-200 status (response.text as message)."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/bridge?auth=test-key",
        status_code=500,
        text="Internal Server Error",
    )
    from nonebot_plugin_apex_api_query.data_source import ApexAPIError, _fetch

    with pytest.raises(ApexAPIError, match="Internal Server Error"):
        await _fetch("bridge")


async def test_fetch_invalid_json(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """_fetch raises ApexAPIError('查询失败: API 返回数据格式错误') on bad JSON."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/bridge?auth=test-key",
        text="<html>not json</html>",
    )
    from nonebot_plugin_apex_api_query.data_source import ApexAPIError, _fetch

    with pytest.raises(ApexAPIError, match="查询失败: API 返回数据格式错误"):
        await _fetch("bridge")


async def test_get_player_stats_happy(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_player_stats returns (formatted text, raw dict) on valid response."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/bridge"
        "?auth=test-key&player=TestPlayer&platform=PC",
        json={
            "global": {
                "name": "TestPlayer",
                "uid": "987654321",
                "platform": "PC",
                "level": 500,
                "toNextLevelPercent": 72,
                "avatar": "https://example.com/avatar.jpg",
                "bans": {
                    "isActive": False,
                    "remainingSeconds": 0,
                    "last_banReason": "",
                },
                "rank": {
                    "rankScore": 15200,
                    "rankName": "Diamond",
                    "rankDiv": "2",
                    "rankImg": "https://example.com/diamond.png",
                    "ALStopPercentGlobal": "8.3",
                },
            },
            "realtime": {
                "lobbyState": "open",
                "isOnline": 1,
                "canJoin": 1,
                "partyFull": 0,
                "selectedLegend": "Wraith",
                "currentState": "inLobby",
                "currentStateAsText": "在大厅",
            },
        },
    )
    from nonebot_plugin_apex_api_query.data_source import get_player_stats

    text, raw = await get_player_stats("TestPlayer", "PC")
    assert isinstance(text, str)
    assert "TestPlayer" in text
    assert "玩家信息" in text
    assert raw is not None
    assert raw["name"] == "TestPlayer"
    assert raw["uid"] == "987654321"
    assert raw["level"] == 500
    assert raw["rank_name"] == "钻石"
    assert raw["rank_div"] == "2"


async def test_get_player_stats_api_error(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_player_stats returns (error string, None) when _fetch raises."""
    httpx_mock.add_exception(
        url="https://api.mozambiquehe.re/bridge"
        "?auth=test-key&player=Ghost&platform=PC",
        exception=httpx.ConnectError("timeout"),
    )
    from nonebot_plugin_apex_api_query.data_source import get_player_stats

    text, raw = await get_player_stats("Ghost", "PC")
    assert isinstance(text, str)
    assert "查询失败" in text
    assert raw is None


async def test_get_map_rotation_happy(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_map_rotation returns formatted text covering all three modes."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/maprotation?auth=test-key&version=2",
        json={
            "battle_royale": {
                "current": {"map": "Olympus", "remainingTimer": "01:12:00"},
                "next": {"map": "Storm Point"},
            },
            "ranked": {
                "current": {"map": "Kings Canyon", "remainingTimer": "23:00:00"},
                "next": {"map": "World\\'s Edge"},
            },
            "ltm": {
                "current": {"map": "Gun Run", "remainingTimer": "00:45:00"},
                "next": {"map": "Control"},
            },
        },
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation

    result = await get_map_rotation()
    assert "大逃杀" in result
    assert "排位赛联盟" in result
    assert "混录带" in result
    assert "奥林匹斯" in result
    assert "诸王峡谷" in result
    assert "风暴点" in result
    assert "当前地图" in result
    assert "下个地图" in result
    assert "剩余时间" in result


async def test_get_map_rotation_api_error(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_map_rotation returns the error string on ApexAPIError."""
    httpx_mock.add_exception(
        url="https://api.mozambiquehe.re/maprotation?auth=test-key&version=2",
        exception=httpx.ConnectError("no route to host"),
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation

    result = await get_map_rotation()
    assert isinstance(result, str)
    assert "查询失败" in result


async def test_get_server_status_data_happy(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_server_status_data returns list[dict] with section_name and rows."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/servers?auth=test-key",
        json={
            "Origin_login": {
                "EU-West": {"Status": "UP", "ResponseTime": 52},
                "EU-East": {"Status": "UP", "ResponseTime": 61},
                "US-West": {"Status": "UP", "ResponseTime": 33},
                "US-Central": {"Status": "SLOW", "ResponseTime": 128},
                "US-East": {"Status": "UP", "ResponseTime": 41},
                "SouthAmerica": {"Status": "UP", "ResponseTime": 85},
                "Asia": {"Status": "UP", "ResponseTime": 58},
            },
            "EA_novafusion": {
                "EU-West": {"Status": "UP", "ResponseTime": 47},
                "EU-East": {"Status": "UP", "ResponseTime": 53},
                "US-West": {"Status": "UP", "ResponseTime": 28},
                "US-Central": {"Status": "UP", "ResponseTime": 33},
                "US-East": {"Status": "UP", "ResponseTime": 31},
                "SouthAmerica": {"Status": "UP", "ResponseTime": 72},
                "Asia": {"Status": "UP", "ResponseTime": 51},
            },
            "EA_accounts": {
                "EU-West": {"Status": "UP", "ResponseTime": 42},
                "EU-East": {"Status": "UP", "ResponseTime": 48},
                "US-West": {"Status": "UP", "ResponseTime": 22},
                "US-Central": {"Status": "UP", "ResponseTime": 29},
                "US-East": {"Status": "UP", "ResponseTime": 26},
                "SouthAmerica": {"Status": "UP", "ResponseTime": 67},
                "Asia": {"Status": "UP", "ResponseTime": 46},
            },
            "ApexOauth_Crossplay": {
                "EU-West": {"Status": "UP", "ResponseTime": 38},
                "EU-East": {"Status": "UP", "ResponseTime": 44},
                "US-West": {"Status": "UP", "ResponseTime": 18},
                "US-Central": {"Status": "UP", "ResponseTime": 24},
                "US-East": {"Status": "UP", "ResponseTime": 21},
                "SouthAmerica": {"Status": "UP", "ResponseTime": 62},
                "Asia": {"Status": "UP", "ResponseTime": 41},
            },
            "selfCoreTest": {
                "Status-website": {"Status": "UP", "ResponseTime": 102},
                "Stats-API": {"Status": "UP", "ResponseTime": 81},
                "Overflow-#1": {"Status": "UP", "ResponseTime": 92},
                "Overflow-#2": {"Status": "UP", "ResponseTime": 87},
                "Origin-API": {"Status": "UP", "ResponseTime": 73},
                "Playstation-API": {"Status": "UP", "ResponseTime": 97},
                "Xbox-API": {"Status": "UP", "ResponseTime": 90},
            },
            "otherPlatforms": {
                "Playstation-Network": {"Status": "UP", "ResponseTime": 43},
                "Xbox-Live": {"Status": "UP", "ResponseTime": 52},
            },
        },
    )
    from nonebot_plugin_apex_api_query.data_source import get_server_status_data

    sections = await get_server_status_data()
    assert isinstance(sections, list)
    assert len(sections) == 6

    section_names = {s["section_name"] for s in sections}
    assert "Origin 登录" in section_names
    assert "EA 融合" in section_names
    assert "自我核心测试" in section_names
    assert "其他平台" in section_names

    for section in sections:
        assert "section_name" in section
        assert "section_key" in section
        assert "rows" in section
        assert len(section["rows"]) > 0
        for row in section["rows"]:
            assert "name" in row
            assert "status" in row
            assert "response_time" in row
            assert row["status"] in ("UP", "SLOW")


async def test_get_server_status_data_api_error(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_server_status_data returns error string on API failure."""
    httpx_mock.add_exception(
        url="https://api.mozambiquehe.re/servers?auth=test-key",
        exception=httpx.ConnectError("refused"),
    )
    from nonebot_plugin_apex_api_query.data_source import get_server_status_data

    result = await get_server_status_data()
    assert isinstance(result, str)
    assert "查询失败" in result


async def test_get_predator_data_happy(httpx_mock: pytest_httpx.HTTMXMock) -> None:
    """get_predator_data returns dict with per-platform predator rankings."""
    httpx_mock.add_response(
        url="https://api.mozambiquehe.re/predator?auth=test-key",
        json={
            "RP": {
                "PC": {
                    "foundRank": 1,
                    "val": 16750,
                    "uid": "pc_master_001",
                    "totalMastersAndPreds": 4800,
                },
                "PS4": {
                    "foundRank": 1,
                    "val": 15500,
                    "uid": "ps4_master_001",
                    "totalMastersAndPreds": 2900,
                },
                "X1": {
                    "foundRank": 1,
                    "val": 14800,
                    "uid": "x1_master_001",
                    "totalMastersAndPreds": 1800,
                },
                "SWITCH": {
                    "foundRank": 1,
                    "val": 13900,
                    "uid": "switch_master_001",
                    "totalMastersAndPreds": 800,
                },
            },
        },
    )
    from nonebot_plugin_apex_api_query.data_source import get_predator_data

    result = await get_predator_data()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"PC", "PS4", "X1", "SWITCH"}

    pc = result["PC"]
    assert pc["name"] == "PC 端"
    assert pc["val"] == 16750
    assert pc["uid"] == "pc_master_001"
    assert pc["found_rank"] == 1
    assert pc["total_masters"] == 4800


async def test_get_predator_data_api_error(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_predator_data returns error string when API request fails."""
    httpx_mock.add_exception(
        url="https://api.mozambiquehe.re/predator?auth=test-key",
        exception=httpx.ConnectError("no route"),
    )
    from nonebot_plugin_apex_api_query.data_source import get_predator_data

    result = await get_predator_data()
    assert isinstance(result, str)
    assert "查询失败" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern B — get_map_rotation_data (apexlegendsstatus.com, returns strings)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_get_map_rotation_data_happy(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_map_rotation_data returns parsed dict on 200 OK."""
    httpx_mock.add_response(
        url="https://api.apexlegendsstatus.com/maprotation"
        "?auth=test-key&version=2",
        json={
            "battle_royale": {
                "current": {
                    "map": "Broken Moon",
                    "asset": "https://cdn.example.com/broken_moon.png",
                    "remainingTimer": "02:15:00",
                },
                "next": {
                    "map": "E-District",
                    "asset": "https://cdn.example.com/e_district.png",
                },
            },
            "ranked": {
                "current": {
                    "map": "Olympus",
                    "asset": "https://cdn.example.com/olympus.png",
                    "remainingTimer": "21:30:00",
                },
                "next": {
                    "map": "Kings Canyon",
                    "asset": "https://cdn.example.com/kings_canyon.png",
                },
            },
            "ltm": {
                "current": {
                    "map": "TDM",
                    "asset": "https://cdn.example.com/tdm.png",
                    "remainingTimer": "00:50:00",
                },
                "next": {
                    "map": "Control",
                    "asset": "https://cdn.example.com/control.png",
                },
            },
        },
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation_data

    result = await get_map_rotation_data()
    assert isinstance(result, dict)
    assert "battle_royale" in result
    assert "ranked" in result
    assert "ltm" in result
    assert result["battle_royale"]["current"]["map"] == "Broken Moon"


async def test_get_map_rotation_data_http_error(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_map_rotation_data returns '地图查询失败: 网络请求错误' on HTTPError."""
    httpx_mock.add_exception(
        url="https://api.apexlegendsstatus.com/maprotation"
        "?auth=test-key&version=2",
        exception=httpx.ConnectError("connection refused"),
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation_data

    result = await get_map_rotation_data()
    assert isinstance(result, str)
    assert result == "地图查询失败: 网络请求错误"


async def test_get_map_rotation_data_non_200(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_map_rotation_data returns '地图查询失败: {status_code}' on non-200."""
    httpx_mock.add_response(
        url="https://api.apexlegendsstatus.com/maprotation"
        "?auth=test-key&version=2",
        status_code=503,
        json={"error": "Service Unavailable"},
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation_data

    result = await get_map_rotation_data()
    assert isinstance(result, str)
    assert result == "地图查询失败: 503"


async def test_get_map_rotation_data_invalid_json(
    httpx_mock: pytest_httpx.HTTMXMock,
) -> None:
    """get_map_rotation_data returns correct error string on invalid JSON."""
    httpx_mock.add_response(
        url="https://api.apexlegendsstatus.com/maprotation"
        "?auth=test-key&version=2",
        text="<html>502 Bad Gateway</html>",
    )
    from nonebot_plugin_apex_api_query.data_source import get_map_rotation_data

    result = await get_map_rotation_data()
    assert isinstance(result, str)
    assert result == "地图查询失败: API 返回数据格式错误"
