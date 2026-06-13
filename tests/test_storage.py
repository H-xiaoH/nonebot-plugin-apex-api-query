"""Tests for PlayerStatsData, _rank_name, and format_comparison.

All plugin imports are inside test functions — the plugin has module-level
side effects (driver, require, config) that need a running NoneBot runtime.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# PlayerStatsData
# --------------------------------------------------------------------------- #

def test_player_stats_data_construction() -> None:
    """PlayerStatsData should store all fields as given."""
    from nonebot_plugin_apex_api_query.storage import PlayerStatsData

    data = PlayerStatsData(
        level=500,
        rank_score=12000,
        rank_name="Diamond",
        rank_div=2,
    )
    assert data.level == 500
    assert data.rank_score == 12000
    assert data.rank_name == "Diamond"
    assert data.rank_div == 2


def test_player_stats_data_rank_div_none() -> None:
    """rank_div may be None for ranks without divisions (e.g. Apex Predator)."""
    from nonebot_plugin_apex_api_query.storage import PlayerStatsData

    data = PlayerStatsData(
        level=100,
        rank_score=25000,
        rank_name="Apex Predator",
        rank_div=None,
    )
    assert data.rank_div is None
    assert data.rank_name == "Apex Predator"


# --------------------------------------------------------------------------- #
# _rank_name
# --------------------------------------------------------------------------- #

def test_rank_name_with_division() -> None:
    """_rank_name with rank_div=2 should return 'Diamond 2'."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        _rank_name,
    )

    stats = PlayerStatsData(
        level=300, rank_score=8200, rank_name="Diamond", rank_div=2
    )
    assert _rank_name(stats) == "Diamond 2"


def test_rank_name_without_division() -> None:
    """_rank_name with rank_div=None should return the rank name alone."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        _rank_name,
    )

    stats = PlayerStatsData(
        level=500, rank_score=15000, rank_name="Diamond", rank_div=None
    )
    assert _rank_name(stats) == "Diamond"


# --------------------------------------------------------------------------- #
# format_comparison
# --------------------------------------------------------------------------- #

def test_format_comparison_all_same() -> None:
    """No changes when current equals previous."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    assert format_comparison(current, previous) == {}


def test_format_comparison_level_up() -> None:
    """Level increase → '等级' with up arrow and positive delta."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=503, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    assert format_comparison(current, previous) == {"等级": "(↑3)"}


def test_format_comparison_level_down() -> None:
    """Level decrease → '等级' with down arrow and absolute delta."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=498, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    assert format_comparison(current, previous) == {"等级": "(↓2)"}


def test_format_comparison_score_up() -> None:
    """Rank score increase → '大逃杀分数' with up arrow and delta."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=500, rank_score=12500, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    assert format_comparison(current, previous) == {"大逃杀分数": "(↑500)"}


def test_format_comparison_score_down() -> None:
    """Rank score decrease → '大逃杀分数' with down arrow and absolute delta."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=500, rank_score=11900, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    assert format_comparison(current, previous) == {"大逃杀分数": "(↓100)"}


def test_format_comparison_rank_changed() -> None:
    """Rank name change → '大逃杀段位' shows the *previous* rank name."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=500, rank_score=8200, rank_name="Diamond", rank_div=2
    )
    previous = PlayerStatsData(
        level=490, rank_score=7800, rank_name="Platinum", rank_div=3
    )
    assert format_comparison(current, previous) == {
        "等级": "(↑10)",
        "大逃杀分数": "(↑400)",
        "大逃杀段位": "(Platinum 3)",
    }


def test_format_comparison_multiple_changes() -> None:
    """Multiple stat changes should all appear in the result dict."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=510, rank_score=13000, rank_name="Diamond", rank_div=1
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Diamond", rank_div=2
    )
    result = format_comparison(current, previous)
    assert result["等级"] == "(↑10)"
    assert result["大逃杀分数"] == "(↑1000)"
    # rank_name same, but rank_div changed → _rank_name differs
    assert result["大逃杀段位"] == "(Diamond 2)"


def test_format_comparison_zero_diff() -> None:
    """Zero score/level difference should not create an entry (no arrow)."""
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        format_comparison,
    )

    current = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Platinum", rank_div=4
    )
    previous = PlayerStatsData(
        level=500, rank_score=12000, rank_name="Gold", rank_div=1
    )
    result = format_comparison(current, previous)
    assert "等级" not in result
    assert "大逃杀分数" not in result
    assert result == {"大逃杀段位": "(Gold 1)"}


# --------------------------------------------------------------------------- #
# save_record
# --------------------------------------------------------------------------- #


async def test_save_record_adds_and_commits(mock_db_session) -> None:
    """save_record() should call session.add() once and await session.commit()."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        save_record,
    )

    mock_session, mock_cm = mock_db_session()
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        stats = PlayerStatsData(
            level=100, rank_score=5000, rank_name="Gold", rank_div=3
        )
        await save_record(
            uid="123", player_name="TestPlayer", platform="PC", stats=stats
        )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


async def test_save_record_correct_fields(mock_db_session) -> None:
    """save_record() should create a PlayerStats with all fields set correctly."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        save_record,
    )

    mock_session, mock_cm = mock_db_session()
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        stats = PlayerStatsData(
            level=250, rank_score=9000, rank_name="Platinum", rank_div=1
        )
        await save_record(
            uid="abc", player_name="PlayerOne", platform="PS4", stats=stats
        )

    record = mock_session.add.call_args[0][0]
    assert record.uid == "abc"
    assert record.player_name == "PlayerOne"
    assert record.platform == "PS4"
    assert record.level == 250
    assert record.rank_score == 9000
    assert record.rank_name == "Platinum"
    assert record.rank_div == 1


async def test_save_record_rank_div_none(mock_db_session) -> None:
    """save_record() should accept PlayerStatsData with rank_div=None."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        save_record,
    )

    mock_session, mock_cm = mock_db_session()
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        stats = PlayerStatsData(
            level=500,
            rank_score=25000,
            rank_name="Apex Predator",
            rank_div=None,
        )
        await save_record(
            uid="pred", player_name="TopPlayer", platform="PC", stats=stats
        )

    record = mock_session.add.call_args[0][0]
    assert record.rank_div is None
    assert record.rank_name == "Apex Predator"


# --------------------------------------------------------------------------- #
# get_latest_record
# --------------------------------------------------------------------------- #


async def test_get_latest_record_found(mock_db_session) -> None:
    """get_latest_record() returns PlayerStats when a matching record exists."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.models import PlayerStats
    from nonebot_plugin_apex_api_query.storage import get_latest_record

    fake_record = PlayerStats(
        uid="456",
        player_name="ExistingPlayer",
        platform="PC",
        level=300,
        rank_score=10000,
        rank_name="Diamond",
        rank_div=4,
    )
    mock_session, mock_cm = mock_db_session(result=fake_record)
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        result = await get_latest_record(uid="456", platform="PC")

    assert result is fake_record


async def test_get_latest_record_not_found(mock_db_session) -> None:
    """get_latest_record() returns None when no matching record exists."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.storage import get_latest_record

    mock_session, mock_cm = mock_db_session()
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        result = await get_latest_record(uid="nonexistent", platform="PC")

    assert result is None


# --------------------------------------------------------------------------- #
# Roundtrip: save → retrieve → fields match
# --------------------------------------------------------------------------- #


async def test_save_and_get_roundtrip(mock_db_session) -> None:
    """After save_record(), get_latest_record() should return matching fields."""
    from unittest.mock import patch

    from nonebot_plugin_apex_api_query.models import PlayerStats
    from nonebot_plugin_apex_api_query.storage import (
        PlayerStatsData,
        get_latest_record,
        save_record,
    )

    fake_record = PlayerStats(
        uid="789",
        player_name="RoundTrip",
        platform="X1",
        level=420,
        rank_score=15000,
        rank_name="Master",
        rank_div=None,
    )
    mock_session, mock_cm = mock_db_session(result=fake_record)
    with patch(
        "nonebot_plugin_apex_api_query.storage.get_session",
        return_value=mock_cm,
    ):
        stats = PlayerStatsData(
            level=420,
            rank_score=15000,
            rank_name="Master",
            rank_div=None,
        )
        await save_record(
            uid="789",
            player_name="RoundTrip",
            platform="X1",
            stats=stats,
        )

        saved = mock_session.add.call_args[0][0]
        assert saved.uid == "789"
        assert saved.player_name == "RoundTrip"
        assert saved.platform == "X1"
        assert saved.level == 420
        assert saved.rank_score == 15000
        assert saved.rank_name == "Master"
        assert saved.rank_div is None

        retrieved = await get_latest_record(uid="789", platform="X1")

    assert retrieved is fake_record
    assert retrieved.uid == "789"
    assert retrieved.player_name == "RoundTrip"
    assert retrieved.platform == "X1"
    assert retrieved.level == 420
    assert retrieved.rank_score == 15000
    assert retrieved.rank_name == "Master"
    assert retrieved.rank_div is None
