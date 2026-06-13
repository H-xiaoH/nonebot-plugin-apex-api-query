from __future__ import annotations

from datetime import UTC, datetime

import pytest


def test_construct_player_stats_with_valid_fields() -> None:
    """PlayerStats can be constructed with all fields set to valid values."""
    from nonebot_plugin_apex_api_query.models import PlayerStats

    now = datetime.now(UTC)
    record = PlayerStats(
        uid="1234567890",
        player_name="TestPlayer",
        platform="PC",
        level=500,
        rank_score=15000,
        rank_name="Predator",
        rank_div=4,
        created_at=now,
    )

    assert record.uid == "1234567890"
    assert record.player_name == "TestPlayer"
    assert record.platform == "PC"
    assert record.level == 500
    assert record.rank_score == 15000
    assert record.rank_name == "Predator"
    assert record.rank_div == 4
    assert record.created_at == now


def test_rank_div_nullable() -> None:
    """rank_div is nullable (Mapped[int | None]) and accepts None."""
    from nonebot_plugin_apex_api_query.models import PlayerStats

    record = PlayerStats(
        uid="123",
        player_name="Noob",
        platform="PS4",
        level=1,
        rank_score=0,
        rank_name="Rookie",
        rank_div=None,
    )

    assert record.rank_div is None


def test_created_at_explicit() -> None:
    """created_at can be set to an explicit datetime on construction."""
    from nonebot_plugin_apex_api_query.models import PlayerStats

    fixed_date = datetime(2026, 6, 14, 12, 0, 0, tzinfo=UTC)
    record = PlayerStats(
        uid="456",
        player_name="TimeTraveler",
        platform="X1",
        level=200,
        rank_score=8000,
        rank_name="Diamond",
        rank_div=1,
        created_at=fixed_date,
    )

    assert record.created_at == fixed_date
    assert record.created_at.year == 2026


@pytest.mark.parametrize(
    "platform",
    ["PC", "PS4", "X1", "SWITCH"],
)
def test_supported_platforms(platform: str) -> None:
    """PlayerStats accepts all 4 supported platform values."""
    from nonebot_plugin_apex_api_query.models import PlayerStats

    record = PlayerStats(
        uid="789",
        player_name="MultiPlat",
        platform=platform,
        level=100,
        rank_score=5000,
        rank_name="Platinum",
        rank_div=3,
    )

    assert record.platform == platform
