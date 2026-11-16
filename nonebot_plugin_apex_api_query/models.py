from datetime import datetime  # noqa: TC003

from nonebot_plugin_orm import Model
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class PlayerStats(Model):
    __tablename__ = "apex_player_stats"
    __table_args__ = (
        Index("idx_uid_platform", "uid", "platform"),
        {"info": {"bind_key": ""}},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(32))
    player_name: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(16))
    level: Mapped[int]
    prestige: Mapped[int | None] = mapped_column(nullable=True)
    rank_score: Mapped[int]
    rank_name: Mapped[str] = mapped_column(String(64))
    rank_div: Mapped[int | None]
    created_at: Mapped[datetime]


class PlayerBinding(Model):
    __tablename__ = "apex_player_bindings"
    __table_args__ = {"info": {"bind_key": ""}}

    scope: Mapped[str] = mapped_column(String(512), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    uid: Mapped[str] = mapped_column(String(32))
    player_name: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime]
