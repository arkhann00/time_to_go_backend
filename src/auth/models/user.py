from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.believers.models.believer import Believer
    from src.believers.models.method import EvangelismMethod
    from src.outreach.models.outreach_statistics import OutreachStatistics


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    about: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    believers: Mapped[list["Believer"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    methods: Mapped[list["EvangelismMethod"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    outreach_statistics: Mapped["OutreachStatistics | None"] = relationship(
        back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )