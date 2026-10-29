"""One-time passwords, and the audit log of everything that changed."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, Timestamps
from .common import Market, MarketColumn


class OneTimePassword(Timestamps, Base):
    """An SMS one-time password: hashed like a PIN, with the tries used and when it stops working."""

    __tablename__ = "one_time_passwords"
    __table_args__ = (CheckConstraint("attempts >= 0", name="attempts_not_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # sent to the person's own mobile
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(200))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """Every change made through the API, in order. Rows are only ever added: never changed or deleted.
    Details hold references and the last four digits of numbers, never a PIN, a code or a full ID number."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    market: Mapped[Market | None] = mapped_column(MarketColumn)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
