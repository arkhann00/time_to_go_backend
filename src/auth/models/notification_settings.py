from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.auth.models.user import User


class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_settings_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    believers_friday_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )
    believers_friday_reminder_time: Mapped[time] = mapped_column(
        Time,
        default=time(18, 0),
        server_default="18:00",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="notification_settings")
