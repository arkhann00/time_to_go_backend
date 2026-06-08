from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.outreach.models.outreach_statistics import OutreachStatistics


class Testimony(Base):
    __tablename__ = "testimonies"

    id: Mapped[int] = mapped_column(primary_key=True)
    outreach_statistics_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_statistics.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    statistics: Mapped["OutreachStatistics"] = relationship(back_populates="testimonies")
