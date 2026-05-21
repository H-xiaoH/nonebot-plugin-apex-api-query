from dataclasses import dataclass
from datetime import datetime, timezone

from nonebot_plugin_orm import get_session
from sqlalchemy import desc, select

from .models import PlayerStats


@dataclass
class PlayerStatsData:
    """玩家统计数据值对象，用于在 storage 与 data_source 之间传递数据。"""
    level: int
    rank_score: int
    rank_name: str
    rank_div: int | None


async def get_latest_record(
    uid: str, platform: str
) -> PlayerStats | None:
    """查询指定玩家在指定平台的最新一条历史记录。

    Args:
        uid: 玩家 UID。
        platform: 平台代码。

    Returns:
        最近一条 PlayerStats 记录；无记录时返回 None。
    """
    async with get_session() as session:
        result = await session.execute(
            select(PlayerStats)
            .where(PlayerStats.uid == uid, PlayerStats.platform == platform)
            .order_by(desc(PlayerStats.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


async def save_record(
    uid: str,
    player_name: str,
    platform: str,
    stats: PlayerStatsData,
) -> None:
    """保存一条玩家统计记录到数据库。

    Args:
        uid: 玩家 UID。
        player_name: 玩家名称。
        platform: 平台代码。
        stats: 要保存的统计数据值对象。
    """
    async with get_session() as session:
        record = PlayerStats(
            uid=uid,
            player_name=player_name,
            platform=platform,
            level=stats.level,
            rank_score=stats.rank_score,
            rank_name=stats.rank_name,
            rank_div=stats.rank_div,
            created_at=datetime.now(tz=timezone.utc),
        )
        session.add(record)
        await session.commit()


def _rank_name(stats: PlayerStatsData) -> str:
    if stats.rank_div is not None:
        return f"{stats.rank_name} {stats.rank_div}"
    return stats.rank_name


def format_comparison(
    current: PlayerStatsData, previous: PlayerStatsData
) -> dict[str, str]:
    """对比当前与历史统计数据，生成变化描述映射。

    Args:
        current: 当前统计数据。
        previous: 历史统计数据。

    Returns:
        {显示字段名: 变化描述} 映射，如 {"等级": "(↑3)", "大逃杀段位": "(黄金 2)"}。
        无变化时返回空字典。
    """
    changes: dict[str, str] = {}

    level_diff = current.level - previous.level
    if level_diff > 0:
        changes["等级"] = f"(↑{level_diff})"
    elif level_diff < 0:
        changes["等级"] = f"(↓{abs(level_diff)})"

    score_diff = current.rank_score - previous.rank_score
    if score_diff > 0:
        changes["大逃杀分数"] = f"(↑{score_diff})"
    elif score_diff < 0:
        changes["大逃杀分数"] = f"(↓{abs(score_diff)})"

    prev_rank = _rank_name(previous)
    curr_rank = _rank_name(current)
    if prev_rank != curr_rank:
        changes["大逃杀段位"] = f"({prev_rank})"

    return changes
