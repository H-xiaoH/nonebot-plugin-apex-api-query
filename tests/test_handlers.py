"""Tests for handlers: apex_map, apex_server, apex_predator, apex_player.

All tests call handler functions DIRECTLY with mocked dependencies.
Bypasses nonebug + Alconna routing layer entirely.

Pattern: mock AlconnaMatcher.finish with side_effect=_HandlerFinished to
simulate the real finish() which raises FinishedException to stop execution.
All plugin imports MUST be inside test functions — conftest.py rule.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from nonebot.adapters.onebot.v11 import MessageSegment


# --------------------------------------------------------------------------- #
# Custom exception to simulate apex.finish() stopping handler execution
# --------------------------------------------------------------------------- #

class _HandlerFinished(Exception):
    """Simulate FinishedException raised by real AlconnaMatcher.finish()."""


# --------------------------------------------------------------------------- #
# Shared mock data (no plugin imports at module level except MessageSegment)
# --------------------------------------------------------------------------- #

IMG = b"\x89PNGfake_image"
IMG_SEGMENT = MessageSegment.image(IMG)

MAP_MOCK = {
    "battle_royale": {"current": {"map": "Olympus"}, "next": {"map": "Storm Point"}},
    "ranked": {"current": {"map": "World's Edge"}, "next": {"map": "Kings Canyon"}},
    "ltm": {"current": {"map": "Overflow"}, "next": {"map": "Habitat"}},
}
SERVER_MOCK = [
    {"section_name": "Origin", "section_key": "k", "rows": [{"name": "A", "status": "UP", "response_time": 10}]},
]
PREDATOR_MOCK = {
    "PC": {"name": "PC", "found_rank": 1, "val": 16750, "uid": "u1", "total_masters": 4800},
}
PLAYER_RAW = {
    "uid": "123456", "name": "TestPlayer", "platform": "PC", "level": 500,
    "rank_score": 15000, "rank_name": "钻石", "rank_div": "2",
    "rank_img": "", "avatar": "", "selected_legend": "恶灵",
    "current_state": "在线", "global_rank_pct": "8.3", "to_next_level_pct": 75,
    "lobby_state": "公开", "is_online": "是", "can_join": "是",
    "party_full": "否", "state_as_text": "在大厅",
    "ban_is_active": False, "ban_remaining_secs": 0, "ban_reason": "",
}
PLAYER_TXT = "玩家信息:\n名称: TestPlayer\nUID: 123456"


# =========================================================================== #
# apex_player tests (6)
# =========================================================================== #

async def test_apex_player_happy() -> None:
    """Happy path: API returns data -> image renders -> finish called with image."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_player_stats",
              AsyncMock(return_value=(PLAYER_TXT, PLAYER_RAW))),
        patch("nonebot_plugin_apex_api_query.storage.get_latest_record",
              AsyncMock(return_value=None)),
        patch("nonebot_plugin_apex_api_query.storage.save_record",
              AsyncMock()),
        patch("nonebot_plugin_apex_api_query.image.render_player_card",
              AsyncMock(return_value=IMG)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player(player_name="TestPlayer", platform="PC")

    mock_finish.assert_called_once()
    result = mock_finish.call_args[0][0]
    assert isinstance(result, MessageSegment) and result.type == "image"


async def test_apex_player_text_only() -> None:
    """Text-only mode: config set -> finish called with text string."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.config.config.apex_only_text", True),
        patch("nonebot_plugin_apex_api_query.data_source.get_player_stats",
              AsyncMock(return_value=(PLAYER_TXT, PLAYER_RAW))),
        patch("nonebot_plugin_apex_api_query.storage.get_latest_record",
              AsyncMock(return_value=None)),
        patch("nonebot_plugin_apex_api_query.storage.save_record",
              AsyncMock()),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player(player_name="TestPlayer", platform="PC")

    mock_finish.assert_called_once_with(PLAYER_TXT)


async def test_apex_player_api_error() -> None:
    """API returns error (raw_data=None) -> finish called with error string."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    err = "查询失败: 网络请求错误"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_player_stats",
              AsyncMock(return_value=(err, None))),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player(player_name="TestPlayer", platform="PC")

    mock_finish.assert_called_once_with(err)


async def test_apex_player_no_name() -> None:
    """No player name provided -> finish called with prompt."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player()

    mock_finish.assert_called_once_with("请输入玩家名称")


async def test_apex_player_invalid_platform() -> None:
    """Invalid platform -> finish called with platform error message."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player(player_name="TestPlayer", platform="BADSYS")

    mock_finish.assert_called_once()
    result = mock_finish.call_args[0][0]
    assert "平台参数错误" in result
    assert "PC" in result


async def test_apex_player_image_render_exception() -> None:
    """Image render throws -> finish called with text fallback."""
    from nonebot_plugin_apex_api_query.__init__ import apex_player

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_player_stats",
              AsyncMock(return_value=(PLAYER_TXT, PLAYER_RAW))),
        patch("nonebot_plugin_apex_api_query.storage.get_latest_record",
              AsyncMock(return_value=None)),
        patch("nonebot_plugin_apex_api_query.storage.save_record",
              AsyncMock()),
        patch("nonebot_plugin_apex_api_query.image.render_player_card",
              AsyncMock(side_effect=RuntimeError("render failed"))),
        pytest.raises(_HandlerFinished),
    ):
        await apex_player(player_name="TestPlayer", platform="PC")

    mock_finish.assert_called_once_with(PLAYER_TXT)


# =========================================================================== #
# apex_map tests (4)
# =========================================================================== #

async def test_apex_map_happy() -> None:
    """Happy path: API returns data -> image renders -> finish called with image."""
    from nonebot_plugin_apex_api_query.__init__ import apex_map

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_map_rotation_data",
              AsyncMock(return_value=MAP_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_map_card",
              AsyncMock(return_value=IMG)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_map()

    mock_finish.assert_called_once()
    result = mock_finish.call_args[0][0]
    assert isinstance(result, MessageSegment) and result.type == "image"


async def test_apex_map_text_only() -> None:
    """Text-only mode: finish called with text from get_map_rotation."""
    from nonebot_plugin_apex_api_query.__init__ import apex_map

    txt = "大逃杀:\n当前地图: 奥林匹斯"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.config.config.apex_only_text", True),
        patch("nonebot_plugin_apex_api_query.data_source.get_map_rotation",
              AsyncMock(return_value=txt)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_map()

    mock_finish.assert_called_once_with(txt)


async def test_apex_map_api_error() -> None:
    """API returns error string -> finish called with that error."""
    from nonebot_plugin_apex_api_query.__init__ import apex_map

    err = "地图查询失败: 网络请求错误"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_map_rotation_data",
              AsyncMock(return_value=err)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_map()

    mock_finish.assert_called_once_with(err)


async def test_apex_map_image_render_exception() -> None:
    """Image render throws -> finish called with text fallback."""
    from nonebot_plugin_apex_api_query.__init__ import apex_map

    fallback = "大逃杀:\n当前地图: 奥林匹斯"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_map_rotation_data",
              AsyncMock(return_value=MAP_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_map_card",
              AsyncMock(side_effect=RuntimeError("render failed"))),
        patch("nonebot_plugin_apex_api_query.data_source.get_map_rotation",
              AsyncMock(return_value=fallback)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_map()

    mock_finish.assert_called_once_with(fallback)


# =========================================================================== #
# apex_server tests (4)
# =========================================================================== #

async def test_apex_server_happy() -> None:
    """Happy path: API returns data -> image renders -> finish called with image."""
    from nonebot_plugin_apex_api_query.__init__ import apex_server

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_server_status_data",
              AsyncMock(return_value=SERVER_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_server_card",
              AsyncMock(return_value=IMG)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_server()

    mock_finish.assert_called_once()
    result = mock_finish.call_args[0][0]
    assert isinstance(result, MessageSegment) and result.type == "image"


async def test_apex_server_text_only() -> None:
    """Text-only mode: finish called with text from get_server_status."""
    from nonebot_plugin_apex_api_query.__init__ import apex_server

    txt = "Origin 登录:\nEU-West: 正常"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.config.config.apex_only_text", True),
        patch("nonebot_plugin_apex_api_query.data_source.get_server_status",
              AsyncMock(return_value=txt)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_server()

    mock_finish.assert_called_once_with(txt)


async def test_apex_server_api_error() -> None:
    """API returns error string -> finish called with that error."""
    from nonebot_plugin_apex_api_query.__init__ import apex_server

    err = "查询失败: 网络请求错误"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_server_status_data",
              AsyncMock(return_value=err)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_server()

    mock_finish.assert_called_once_with(err)


async def test_apex_server_image_render_exception() -> None:
    """Image render throws -> finish called with text fallback."""
    from nonebot_plugin_apex_api_query.__init__ import apex_server

    fallback = "Origin 登录:\nEU-West: 正常"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_server_status_data",
              AsyncMock(return_value=SERVER_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_server_card",
              AsyncMock(side_effect=RuntimeError("render failed"))),
        patch("nonebot_plugin_apex_api_query.data_source.get_server_status",
              AsyncMock(return_value=fallback)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_server()

    mock_finish.assert_called_once_with(fallback)


# =========================================================================== #
# apex_predator tests (4)
# =========================================================================== #

async def test_apex_predator_happy() -> None:
    """Happy path: API returns data -> image renders -> finish called with image."""
    from nonebot_plugin_apex_api_query.__init__ import apex_predator

    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_predator_data",
              AsyncMock(return_value=PREDATOR_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_predator_card",
              AsyncMock(return_value=IMG)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_predator()

    mock_finish.assert_called_once()
    result = mock_finish.call_args[0][0]
    assert isinstance(result, MessageSegment) and result.type == "image"


async def test_apex_predator_text_only() -> None:
    """Text-only mode: finish called with text from get_predator."""
    from nonebot_plugin_apex_api_query.__init__ import apex_predator

    txt = "大逃杀:\nPC 端:\n顶尖猎杀者分数: 16750"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.config.config.apex_only_text", True),
        patch("nonebot_plugin_apex_api_query.data_source.get_predator",
              AsyncMock(return_value=txt)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_predator()

    mock_finish.assert_called_once_with(txt)


async def test_apex_predator_api_error() -> None:
    """API returns error string -> finish called with that error."""
    from nonebot_plugin_apex_api_query.__init__ import apex_predator

    err = "查询失败: 网络请求错误"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_predator_data",
              AsyncMock(return_value=err)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_predator()

    mock_finish.assert_called_once_with(err)


async def test_apex_predator_image_render_exception() -> None:
    """Image render throws -> finish called with text fallback."""
    from nonebot_plugin_apex_api_query.__init__ import apex_predator

    fallback = "大逃杀:\nPC 端:\n顶尖猎杀者分数: 16750"
    mock_finish = AsyncMock(side_effect=_HandlerFinished())
    with (
        patch("nonebot_plugin_alconna.matcher.AlconnaMatcher.finish", mock_finish),
        patch("nonebot_plugin_apex_api_query.data_source.get_predator_data",
              AsyncMock(return_value=PREDATOR_MOCK)),
        patch("nonebot_plugin_apex_api_query.image.render_predator_card",
              AsyncMock(side_effect=RuntimeError("render failed"))),
        patch("nonebot_plugin_apex_api_query.data_source.get_predator",
              AsyncMock(return_value=fallback)),
        pytest.raises(_HandlerFinished),
    ):
        await apex_predator()

    mock_finish.assert_called_once_with(fallback)
