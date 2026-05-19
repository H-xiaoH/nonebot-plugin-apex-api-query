"""玩家数据持久化与对比模块。

提供：
- PlayerStatsData: 数据传输对象，封装单次查询统计的核心字段
- get_latest_record: 查询指定玩家最近一次记录
- save_record: 持久化当前统计数据
- format_comparison: 对比本次与上次数据的差异
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from nonebot_plugin_orm import get_session
from sqlalchemy import desc, select

from .models import PlayerStats


@dataclass
class PlayerStatsData:
    """单次查询统计数据的纯数据结构。

    用于在各模块间传递数据，避免函数参数过多。
    """

    level: int
    rank_score: int
    rank_name: str
    rank_div: int | None


async def get_latest_record(
    uid: str, platform: str
) -> PlayerStats | None:
    """获取指定玩家最近一次保存的统计记录。

    按 created_at 降序排列取第一条，无记录时返回 None。
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
    """保存一次玩家统计数据到数据库。

    每次查询都会新增一条记录（而非更新），时间戳使用 UTC。
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


def format_comparison(current: PlayerStatsData, previous: PlayerStatsData) -> str:
    """生成本次与上次统计数据的差异对比文本。

    对比三项指标：等级、大逃杀分数、大逃杀段位。
    每项显示上升/下降/无变化三种状态，箭头符号表示方向。
    """
    lines = ["\n--- 数据变化 ---"]

    # 等级对比
    level_diff = current.level - previous.level
    if level_diff > 0:
        lines.append(f"等级: {previous.level} -> {current.level} (↑{level_diff})")
    elif level_diff < 0:
        lines.append(f"等级: {previous.level} -> {current.level} (↓{abs(level_diff)})")
    else:
        lines.append(f"等级: 无变化 ({current.level})")

    # 排位分数对比
    score_diff = current.rank_score - previous.rank_score
    if score_diff > 0:
        lines.append(
            f"大逃杀分数: {previous.rank_score} -> "
            f"{current.rank_score} (↑{score_diff})"
        )
    elif score_diff < 0:
        lines.append(
            f"大逃杀分数: {previous.rank_score} -> "
            f"{current.rank_score} (↓{abs(score_diff)})"
        )
    else:
        lines.append(f"大逃杀分数: 无变化 ({current.rank_score})")

    # 段位对比（含分区，如"钻石 3"）
    prev_rank = (
        f"{previous.rank_name} {previous.rank_div}"
        if previous.rank_div is not None
        else previous.rank_name
    )
    curr_rank = (
        f"{current.rank_name} {current.rank_div}"
        if current.rank_div is not None
        else current.rank_name
    )
    if prev_rank != curr_rank:
        lines.append(f"大逃杀段位: {prev_rank} -> {curr_rank}")
    else:
        lines.append(f"大逃杀段位: 无变化 ({curr_rank})")

    return "\n".join(lines)
