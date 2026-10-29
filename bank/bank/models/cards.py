"""Cards and what was done to them, card applications, billers and the bills customers pay them, registered payees, and
direct debits."""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Money, Timestamps
from .common import Market, MarketColumn, choice
from .products import Product


class CardStatus(enum.StrEnum):
    INACTIVE = "inactive"  # sent, not activated yet
    ACTIVE = "active"
    BLOCKED = "blocked"  # stopped (reported lost or stolen, or by the bank): see block_reason


class Card(Timestamps, Base):
    """A credit or debit card, held by one person on one customer record. The bank keeps only the last four digits
    here: the full number lives with the card processor. A debit card draws on its linked account; a credit card has
    its own limit and bill."""

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("customer_id", "last4"),
        CheckConstraint("credit_limit >= 0", name="limit_not_negative"),
        CheckConstraint("outstanding_balance >= 0", name="outstanding_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    holder_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # a debit card's account
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    last4: Mapped[str] = mapped_column(String(4))
    expires_on: Mapped[date] = mapped_column(Date)
    status: Mapped[CardStatus] = mapped_column(choice(CardStatus, "card_status"))
    block_reason: Mapped[str] = mapped_column(String(60), default="", server_default="")
    credit_limit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    outstanding_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    minimum_due: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    due_on: Mapped[date | None] = mapped_column(Date)
    # this year's annual fee is waived until this day (the fee itself is the product's)
    fee_waived_until: Mapped[date | None] = mapped_column(Date)

    product: Mapped[Product] = relationship(lazy="joined")
    holder: Mapped["Person"] = relationship()  # noqa: F821
    account: Mapped["Account | None"] = relationship()  # noqa: F821

    @property
    def available_credit(self) -> Decimal:
        return max(self.credit_limit - self.outstanding_balance, Decimal("0"))


class CardAction(Timestamps, Base):
    """Something done to a card on a call: activation, a block, a fee waiver, a limit change, a balance transfer."""

    __tablename__ = "card_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    action: Mapped[str] = mapped_column(String(30))
    outcome: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")


class ApplicationStatus(enum.StrEnum):
    RECEIVED = "received"
    APPROVED = "approved"
    DECLINED = "declined"


class CardApplication(Timestamps, Base):
    """A card applied for, found by the applicant's ID number (kept as a fingerprint)."""

    __tablename__ = "card_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    status: Mapped[ApplicationStatus] = mapped_column(choice(ApplicationStatus, "application_status"))
    applied_on: Mapped[date] = mapped_column(Date)
    sent_on: Mapped[date | None] = mapped_column(Date)

    product: Mapped[Product] = relationship(lazy="joined")


class Biller(Timestamps, Base):
    """A company customers pay bills to from phone banking (electricity, water, broadband)."""

    __tablename__ = "billers"
    __table_args__ = (UniqueConstraint("market", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))


class Bill(Timestamps, Base):
    """A biller account a customer has registered to pay: the biller, and the customer's account number with them."""

    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("customer_id", "biller_id", "biller_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    biller_id: Mapped[int] = mapped_column(ForeignKey("billers.id"))
    biller_reference: Mapped[str] = mapped_column(String(30))
    nickname: Mapped[str] = mapped_column(String(60), default="", server_default="")

    biller: Mapped[Biller] = relationship(lazy="joined")


class Payee(Timestamps, Base):
    """Someone a customer has registered to pay at another bank (Interbank GIRO). Only the last four digits of their
    account are shown; the full number stays with the payment system."""

    __tablename__ = "payees"
    __table_args__ = (UniqueConstraint("customer_id", "nickname"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    nickname: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(120))
    bank_name: Mapped[str] = mapped_column(String(60))
    account_last4: Mapped[str] = mapped_column(String(4))


class MandateStatus(enum.StrEnum):
    ACTIVE = "active"
    TERMINATED = "terminated"


class DirectDebit(Timestamps, Base):
    """An FPX direct-debit mandate (Malaysia): a merchant takes a set amount from an account each month."""

    __tablename__ = "direct_debits"

    id: Mapped[int] = mapped_column(primary_key=True)
    mandate_reference: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    merchant: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[MandateStatus] = mapped_column(choice(MandateStatus, "mandate_status"))
