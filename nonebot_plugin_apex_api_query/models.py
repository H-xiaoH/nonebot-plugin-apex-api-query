"""玩家统计数据 ORM 模型。

用于持久化存储每次查询的玩家信息，支持历史对比功能。
通过 nonebot_plugin_orm 提供的 Model 基类自动集成 SQLAlchemy 和 Alembic。
"""

from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column


class PlayerStats(Model):
    """Apex 玩家统计数据表。

    每次查询都会新增一条记录（非覆盖），通过 uid + platform 联合索引
    可高效查询该玩家在不同平台上的历史数据。
    """

    __tablename__ = "apex_player_stats"
    __table_args__ = (
        # uid + platform 联合索引，加速按玩家查询最新记录
        Index("ix_apex_player_stats_uid_platform", "uid", "platform"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str]
    player_name: Mapped[str]
    platform: Mapped[str]
    level: Mapped[int]
    rank_score: Mapped[int]
    rank_name: Mapped[str]
    rank_div: Mapped[int | None]  # 可空：无段位玩家无段位分区
    created_at: Mapped[datetime]  # 记录时间，用于排序取最新记录
