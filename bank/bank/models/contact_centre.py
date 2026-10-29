"""The contact centre's own records: VIPs and their service managers, cases, and everything a call leaves behind
(hand-overs, call-backs, surveys, service requests, statement requests, faxes). Who a caller is comes from people."""

import enum
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Timestamps
from .common import Market, MarketColumn, choice


class ServiceManager(Timestamps, Base):
    """A member of staff customers are put through to: a relationship manager, or a service manager on a case."""

    __tablename__ = "service_managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    name: Mapped[str] = mapped_column(String(120))
    team: Mapped[str] = mapped_column(String(60))
    available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class VipCheck(enum.StrEnum):
    # how a VIP proves who they are on the VIP line
    ACCOUNT = "account"
    PHONE_CODE = "phone_code"
    NONE = "default"


class Vip(Timestamps, Base):
    """A person on the VIP line: how they are checked there, the customer they call about, and their service manager.
    Their name, mobile and language are the person's own."""

    __tablename__ = "vips"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), unique=True)
    vip_check: Mapped[VipCheck] = mapped_column(choice(VipCheck, "vip_check"))
    # the account they are checked by (vip_check "account")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    service_manager_id: Mapped[int] = mapped_column(ForeignKey("service_managers.id"))

    person: Mapped["Person"] = relationship(lazy="joined")  # noqa: F821
    account: Mapped["Account | None"] = relationship()  # noqa: F821
    customer: Mapped["Customer | None"] = relationship()  # noqa: F821
    service_manager: Mapped[ServiceManager] = relationship()


class Investigation(Timestamps, Base):
    """An open case on an account, and the service manager handling it."""

    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_reference: Mapped[str] = mapped_column(String(20), unique=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    topic: Mapped[str] = mapped_column(String(120))
    opened_on: Mapped[date] = mapped_column(Date)
    service_manager_id: Mapped[int] = mapped_column(ForeignKey("service_managers.id"))

    service_manager: Mapped[ServiceManager] = relationship()


class ServiceCode(Timestamps, Base):
    """A code a caller keys to reach a desk directly (e.g. 328 for fixed deposits, loans and FX dealing)."""

    __tablename__ = "service_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    route: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))


class HandOverOutcome(enum.StrEnum):
    TRANSFERRED = "transferred"
    UNAVAILABLE = "unavailable"


class HandOver(Timestamps, Base):
    """A call passed to people: the queue, its priority and what the agent screen showed them."""

    __tablename__ = "hand_overs"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    # the customer it was about, when known, and what the person taking over should know (the agent's summary)
    cif: Mapped[str] = mapped_column(String(20), default="", server_default="", index=True)
    summary: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    skillset: Mapped[str] = mapped_column(String(60), default="")
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    intent: Mapped[str] = mapped_column(String(120), default="")
    service_manager_id: Mapped[int | None] = mapped_column(ForeignKey("service_managers.id"))
    outcome: Mapped[HandOverOutcome] = mapped_column(choice(HandOverOutcome, "hand_over_outcome"))
    screen_pop: Mapped[dict] = mapped_column(JSONB, default=dict)


class CallbackStatus(enum.StrEnum):
    OPEN = "open"
    DONE = "done"


class Callback(Timestamps, Base):
    __tablename__ = "callbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    cif: Mapped[str] = mapped_column(String(20), default="", server_default="", index=True)
    caller_phone: Mapped[str] = mapped_column(String(16), index=True)
    callback_number: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[CallbackStatus] = mapped_column(choice(CallbackStatus, "callback_status"), default=CallbackStatus.OPEN)


class Survey(Timestamps, Base):
    """Three ratings from 1 to 5 at the end of a call."""

    __tablename__ = "surveys"
    __table_args__ = tuple(CheckConstraint(f"{q} BETWEEN 1 AND 5", name=f"{q}_is_1_to_5") for q in ("q1", "q2", "q3"))

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    profile: Mapped[str] = mapped_column(String(20), default="ivr")
    q1: Mapped[int] = mapped_column(SmallInteger)
    q2: Mapped[int] = mapped_column(SmallInteger)
    q3: Mapped[int] = mapped_column(SmallInteger)


class ServiceRequest(Timestamps, Base):
    """A service request raised for the back office (Siebel)."""

    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    sr_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    cif: Mapped[str] = mapped_column(String(20), default="")
    account_number: Mapped[str] = mapped_column(String(20), default="")
    request_type: Mapped[str] = mapped_column(String(60), default="")
    category: Mapped[str] = mapped_column(String(60), default="")
    subcategory: Mapped[str] = mapped_column(String(60), default="")
    notes: Mapped[str] = mapped_column(String(500), default="")


class StatementRequest(Timestamps, Base):
    __tablename__ = "statement_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    account_number: Mapped[str] = mapped_column(String(20))
    month: Mapped[str] = mapped_column(String(20), default="latest")
    delivery: Mapped[str] = mapped_column(String(10), default="mail")
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")


class FaxJob(Timestamps, Base):
    """A form or promotion sent to the caller's fax."""

    __tablename__ = "fax_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    fax_number: Mapped[str] = mapped_column(String(20))
    document: Mapped[str] = mapped_column(String(120), default="")


class CallRegistration(Timestamps, Base):
    """A call noted against a customer before it is passed on (what it was about, which queue)."""

    __tablename__ = "call_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    cif: Mapped[str] = mapped_column(String(20), default="")
    intent: Mapped[str] = mapped_column(String(120), default="")
    skillset: Mapped[str] = mapped_column(String(60), default="")
