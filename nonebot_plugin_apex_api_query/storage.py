from datetime import datetime, timezone
from typing import Optional

from nonebot_plugin_orm import get_session
from sqlalchemy import desc, select

from .models import PlayerStats


async def get_latest_record(
    uid: str, platform: str
) -> Optional[PlayerStats]:
    """获取指定玩家最近一次保存的记录。"""
    async with get_session() as session:
        result = await session.execute(
            select(PlayerStats)
            .where(PlayerStats.uid == uid, PlayerStats.platform == platform)
            .order_by(desc(PlayerStats.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()


async def save_record(  # noqa: PLR0913
    uid: str,
    player_name: str,
    platform: str,
    level: int,
    rank_score: int,
    rank_name: str,
    rank_div: Optional[int],
) -> None:
    """保存一次玩家统计数据。"""
    async with get_session() as session:
        record = PlayerStats(
            uid=uid,
            player_name=player_name,
            platform=platform,
            level=level,
            rank_score=rank_score,
            rank_name=rank_name,
            rank_div=rank_div,
            created_at=datetime.now(tz=timezone.utc),
        )
        session.add(record)
        await session.commit()


def format_comparison(  # noqa: PLR0913
    level: int,
    rank_score: int,
    rank_name: str,
    rank_div: Optional[int],
    prev_level: int,
    prev_rank_score: int,
    prev_rank_name: str,
    prev_rank_div: Optional[int],
) -> str:
    """格式化数据变化的比较结果。"""
    lines = ["\n--- 数据变化 ---"]

    level_diff = level - prev_level
    if level_diff > 0:
        lines.append(f"等级: {prev_level} -> {level} (↑{level_diff})")
    elif level_diff < 0:
        lines.append(f"等级: {prev_level} -> {level} (↓{abs(level_diff)})")
    else:
        lines.append(f"等级: 无变化 ({level})")

    score_diff = rank_score - prev_rank_score
    if score_diff > 0:
        lines.append(
            f"大逃杀分数: {prev_rank_score} -> {rank_score} (↑{score_diff})"
        )
    elif score_diff < 0:
        lines.append(
            f"大逃杀分数: {prev_rank_score} -> {rank_score} (↓{abs(score_diff)})"
        )
    else:
        lines.append(f"大逃杀分数: 无变化 ({rank_score})")

    prev_rank = (
        f"{prev_rank_name} {prev_rank_div}"
        if prev_rank_div is not None
        else prev_rank_name
    )
    curr_rank = (
        f"{rank_name} {rank_div}" if rank_div is not None else rank_name
    )
    if prev_rank != curr_rank:
        lines.append(f"大逃杀段位: {prev_rank} -> {curr_rank}")
    else:
        lines.append(f"大逃杀段位: 无变化 ({curr_rank})")

    return "\n".join(lines)
