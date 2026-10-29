"""Branches, the appointment slots they offer, and the bookings made in them."""

from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Timestamps
from .common import Market, MarketColumn


class Branch(Timestamps, Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(200))
    opening_hours: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str] = mapped_column(String(30), default="", server_default="")


class AppointmentSlot(Timestamps, Base):
    """A time a branch can see a customer, for one kind of appointment."""

    __tablename__ = "appointment_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    appointment_type: Mapped[str] = mapped_column(String(40), index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    slot_date: Mapped[date] = mapped_column(Date)
    slot_time: Mapped[time] = mapped_column(Time)
    is_taken: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    branch: Mapped[Branch] = relationship()


class Booking(Timestamps, Base):
    """An appointment a customer booked in a free slot."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("appointment_slots.id"), index=True)
    cif: Mapped[str] = mapped_column(String(20), default="", index=True)
    appointment_type: Mapped[str] = mapped_column(String(40), default="")
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    slot: Mapped[AppointmentSlot] = relationship()
