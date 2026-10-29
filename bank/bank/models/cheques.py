"""Cheques: books issued, cheques written and their status, stop-payment orders, and cheques paid in."""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Money, Timestamps
from .common import Market, MarketColumn, choice


class ChequeBook(Timestamps, Base):
    """A cheque book the bank has sent: its range of cheque numbers and how it went out."""

    __tablename__ = "cheque_books"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    first_cheque_no: Mapped[str] = mapped_column(String(6))
    last_cheque_no: Mapped[str] = mapped_column(String(6))
    sent_on: Mapped[date] = mapped_column(Date)
    delivery: Mapped[str] = mapped_column(String(80))


class Delivery(enum.StrEnum):
    NORMAL = "normal"
    EXPRESS = "express"
    SAME_DAY = "same_day"


class ChequeBookOrder(Timestamps, Base):
    """A request for a new cheque book, for an account that writes cheques."""

    __tablename__ = "cheque_book_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    account_number: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    delivery: Mapped[Delivery] = mapped_column(choice(Delivery, "delivery"), default=Delivery.NORMAL)
    fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    ready_in_working_days: Mapped[int] = mapped_column(Integer)
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")


class ChequeStatus(enum.StrEnum):
    PAID = "paid"
    NOT_PRESENTED = "not presented"
    STOPPED = "stopped"


class IssuedCheque(Timestamps, Base):
    """A cheque the customer wrote, by account and cheque number. A stop order on a cheque the bank has not seen yet
    adds it here, as stopped."""

    __tablename__ = "issued_cheques"
    __table_args__ = (UniqueConstraint("account_number", "cheque_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    account_number: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    cheque_no: Mapped[str] = mapped_column(String(10))
    status: Mapped[ChequeStatus] = mapped_column(choice(ChequeStatus, "cheque_status"))
    amount: Mapped[Decimal | None] = mapped_column(Money)
    paid_on: Mapped[date | None] = mapped_column(Date)
    stopped_on: Mapped[date | None] = mapped_column(Date)

    stop_orders: Mapped[list["StopPayment"]] = relationship(back_populates="cheque")


class StopPayment(Timestamps, Base):
    """A stop-payment instruction, with its fee."""

    __tablename__ = "stop_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    issued_cheque_id: Mapped[int] = mapped_column(ForeignKey("issued_cheques.id"), index=True)
    reason: Mapped[str] = mapped_column(String(200), default="")
    fee: Mapped[Decimal] = mapped_column(Money)
    fee_currency: Mapped[str] = mapped_column(String(3))
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")

    cheque: Mapped[IssuedCheque] = relationship(back_populates="stop_orders")


class DepositStatus(enum.StrEnum):
    CLEARED = "cleared"
    CLEARING = "clearing"
    RETURNED = "returned"


class ChequeDeposit(Timestamps, Base):
    """A cheque paid into the account, and where it is in clearing."""

    __tablename__ = "cheque_deposits"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    deposited_on: Mapped[date] = mapped_column(Date)
    cheque_no: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[DepositStatus] = mapped_column(choice(DepositStatus, "deposit_status"))
    value_date: Mapped[date | None] = mapped_column(Date)
    return_reason: Mapped[str | None] = mapped_column(String(120))
