"""Unit tests for pure helper functions in nonebot_plugin_apex_api_query.image.

Tests cover three helpers:
- ``_fmt_remaining``   — seconds → HH:MM:SS / MM:SS
- ``_fmt_num``         — integer → "暂无" or comma-separated string
- ``_parse_time_str``  — datetime string → "HH:MM"

All plugin imports happen *inside* test functions, consistent with the
conftest.py rule that the plugin must not be imported at module level.
"""

from __future__ import annotations

import pytest


# --------------------------------------------------------------------------- #
# _fmt_remaining
# --------------------------------------------------------------------------- #

class TestFmtRemaining:
    """Tests for ``_fmt_remaining(seconds: int) -> str``."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0, "00:00"),
            (-1, "00:00"),
            (59, "00:59"),
            (60, "01:00"),
            (3599, "59:59"),
            (3600, "01:00:00"),
            (3661, "01:01:01"),
        ],
    )
    def test_fmt_remaining(self, seconds: int, expected: str) -> None:
        from nonebot_plugin_apex_api_query.image import _fmt_remaining

        assert _fmt_remaining(seconds) == expected


# --------------------------------------------------------------------------- #
# _fmt_num
# --------------------------------------------------------------------------- #

class TestFmtNum:
    """Tests for ``_fmt_num(value: int) -> str``."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "暂无"),
            (-1, "暂无"),
            (100, "100"),
            (1000, "1,000"),
            (1000000, "1,000,000"),
        ],
    )
    def test_fmt_num(self, value: int, expected: str) -> None:
        from nonebot_plugin_apex_api_query.image import _fmt_num

        assert _fmt_num(value) == expected


# --------------------------------------------------------------------------- #
# _parse_time_str
# --------------------------------------------------------------------------- #

class TestParseTimeStr:
    """Tests for ``_parse_time_str(readable: str) -> str``."""

    @pytest.mark.parametrize(
        ("readable", "expected"),
        [
            ("2026-06-14 12:30:45", "12:30"),
            ("12:30", "12:30"),
        ],
    )
    def test_parse_time_str(self, readable: str, expected: str) -> None:
        from nonebot_plugin_apex_api_query.image import _parse_time_str

        assert _parse_time_str(readable) == expected


# --------------------------------------------------------------------------- #
# render_* cards — integration tests (no HTTP, no pixel assertions)
# --------------------------------------------------------------------------- #

PNG_MAGIC = b"\x89PNG"


def _dummy_rgba() -> "Image.Image":
    from PIL import Image

    return Image.new("RGBA", (10, 10), (255, 0, 0, 255))


class TestRenderCards:
    """Smoke tests for the 4 public ``render_*`` functions in image.py.

    Every test asserts that the output is non-empty bytes starting with the
    PNG magic header.  Image caches are seeded with tiny dummy images so
    **no real HTTP calls happen**.  The ``reset_image_caches`` autouse fixture
    guarantees clean state between tests.
    """

    # -- render_map_card --------------------------------------------------------

    async def test_render_map_card_returns_png(self) -> None:
        from nonebot_plugin_apex_api_query.image import _image_cache, render_map_card

        map_urls = {
            "https://example.com/storm_point.png",
            "https://example.com/olympus.png",
        }
        for u in map_urls:
            _image_cache[u] = _dummy_rgba()

        data: dict = {
            "battle_royale": {
                "current": {
                    "map": "Storm Point",
                    "asset": "https://example.com/storm_point.png",
                    "start": 1718366400,
                    "end": 1718370000,
                    "remainingSecs": 1200,
                    "DurationInSecs": 3600,
                },
                "next": {
                    "map": "World's Edge",
                    "start": 1718370000,
                    "end": 1718373600,
                },
            },
            "ranked": {
                "current": {
                    "map": "Olympus",
                    "asset": "https://example.com/olympus.png",
                    "remainingSecs": 2400,
                    "DurationInSecs": 3600,
                },
            },
            "ltm": {
                "current": {
                    "map": "Arena",
                    "eventName": "Control",
                    "remainingSecs": 600,
                    "DurationInSecs": 1800,
                },
            },
        }

        result = await render_map_card(data)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(PNG_MAGIC)

    # -- render_server_card -----------------------------------------------------

    async def test_render_server_card_returns_png(self) -> None:
        from nonebot_plugin_apex_api_query.image import render_server_card

        sections: list[dict] = [
            {
                "section_name": "Origin",
                "rows": [
                    {"name": "登录服务", "status": "UP", "response_time": 120},
                    {"name": "游戏服务", "status": "SLOW", "response_time": 500},
                    {"name": "匹配系统", "status": "DOWN"},
                ],
            },
            {
                "section_name": "EA 融合",
                "rows": [
                    {"name": "融合服务", "status": "UP", "response_time": 80},
                ],
            },
        ]

        result = await render_server_card(sections)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(PNG_MAGIC)

    # -- render_predator_card ---------------------------------------------------

    async def test_render_predator_card_returns_png(self) -> None:
        from nonebot_plugin_apex_api_query.image import render_predator_card

        data: dict = {
            "PC": {"name": "PC", "val": 15000, "total_masters": 5000},
            "PS4": {"name": "PS4", "val": 12000, "total_masters": 3000},
            "X1": {"name": "X1", "val": 10000, "total_masters": 0},
        }

        result = await render_predator_card(data)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(PNG_MAGIC)

    # -- render_player_card -----------------------------------------------------

    async def test_render_player_card_returns_png(self) -> None:
        from nonebot_plugin_apex_api_query.image import _image_cache, render_player_card

        rank_url = "https://example.com/rank_badge.png"
        _image_cache[rank_url] = _dummy_rgba()

        player: dict = {
            "name": "TestPlayer",
            "uid": "123456789",
            "platform": "PC",
            "rank_img": rank_url,
            "rank_name": "钻石",
            "rank_div": "II",
            "rank_score": 8500,
            "level": 500,
            "to_next_level_pct": 75,
            "selected_legend": "Wraith",
            "current_state": "在线",
            "state_as_text": "在大厅",
            "lobby_state": "公开",
            "is_online": "是",
            "can_join": "是",
            "party_full": "否",
        }

        result = await render_player_card(player)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(PNG_MAGIC)

    # -- edge cases -------------------------------------------------------------

    @pytest.mark.parametrize(
        "func_name, kwargs",
        [
            ("render_map_card", {"data": {}}),
            ("render_server_card", {"sections": []}),
            ("render_server_card", {"sections": [{"section_name": "空", "rows": []}]}),
            ("render_predator_card", {"data": {}}),
            ("render_player_card", {"player": {}}),
            ("render_player_card", {"player": {"name": None}}),
        ],
    )
    async def test_render_edge_input_no_crash(
        self, func_name: str, kwargs: dict,
    ) -> None:
        import nonebot_plugin_apex_api_query.image as img_mod

        func = getattr(img_mod, func_name)
        result = await func(**kwargs)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(PNG_MAGIC)
