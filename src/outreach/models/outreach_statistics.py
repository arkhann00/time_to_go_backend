from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.auth.models.user import User


class OutreachStatistics(Base):
    __tablename__ = "outreach_statistics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    gospels_told: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    salvation_prayed_unreachable: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    scriptures_distributed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    healings_deliverances: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="outreach_statistics")
