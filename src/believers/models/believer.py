from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.auth.models.user import User
    from src.believers.models.method import EvangelismMethod


class ChristianStage(str, Enum):
    INTERESTED_IN_FAITH = "Интересуется верой"
    ACCEPTED_JESUS = "Принял Иисуса"
    CAME_TO_CHURCH = "Пришел в церковь"
    BAPTIZED = "Крестился"
    PREACHES_GOSPEL = "Проповедует Евангелие"


class Believer(Base):
    __tablename__ = "believers"
    __table_args__ = (
        CheckConstraint(
            "telegram IS NOT NULL OR phone_number IS NOT NULL",
            name="ck_believers_contact_exists",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    telegram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    met_at: Mapped[date] = mapped_column(Date)
    stage: Mapped[ChristianStage] = mapped_column(SqlEnum(ChristianStage))
    method_id: Mapped[int] = mapped_column(ForeignKey("evangelism_methods.id"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="believers")
    method: Mapped["EvangelismMethod"] = relationship(back_populates="believers")

