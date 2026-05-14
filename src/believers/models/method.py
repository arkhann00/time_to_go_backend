from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.auth.models.user import User
    from src.believers.models.believer import Believer


class EvangelismMethod(Base):
    __tablename__ = "evangelism_methods"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_method_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    owner: Mapped["User | None"] = relationship(back_populates="methods")
    believers: Mapped[list["Believer"]] = relationship(back_populates="method")

