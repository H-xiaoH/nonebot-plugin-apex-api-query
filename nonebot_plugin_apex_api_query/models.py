from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column


class PlayerStats(Model):
    __tablename__ = "apex_player_stats"
    __table_args__ = (
        Index("ix_apex_player_stats_uid_platform", "uid", "platform"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str]
    player_name: Mapped[str]
    platform: Mapped[str]
    level: Mapped[int]
    rank_score: Mapped[int]
    rank_name: Mapped[str]
    rank_div: Mapped[int | None]
    created_at: Mapped[datetime]
