from datetime import datetime
from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class PlayerStats(Model):
    __tablename__ = "apex_player_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str]
    player_name: Mapped[str]
    platform: Mapped[str]
    level: Mapped[int]
    rank_score: Mapped[int]
    rank_name: Mapped[str]
    rank_div: Mapped[Optional[int]]
    created_at: Mapped[datetime]
