"""Accounts, the money that moves through them, holds on it, fixed deposits and loans.

An account's ledger balance is the sum of its postings: every posting keeps the balance after it. What can be spent
(the available balance) is the ledger less the holds still in place, and nothing at all on an account that is not active.
"""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Money, Rate, Timestamps
from .common import Market, MarketColumn, choice
from .products import Product


class AccountStatus(enum.StrEnum):
    ACTIVE = "active"
    # no customer activity for years: enquiries only, until the customer reactivates it at a branch
    DORMANT = "dormant"
    # stopped by the bank (a court order, a fraud check): nothing moves
    FROZEN = "frozen"
    CLOSED = "closed"


class Account(Timestamps, Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("char_length(currency) = 3", name="currency_is_iso_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    ledger_balance: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[AccountStatus] = mapped_column(choice(AccountStatus, "account_status"), default=AccountStatus.ACTIVE)
    opened_on: Mapped[date] = mapped_column(Date)
    closed_on: Mapped[date | None] = mapped_column(Date)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"))

    customer: Mapped["Customer"] = relationship(back_populates="accounts")  # noqa: F821
    product: Mapped[Product] = relationship(lazy="joined")
    holds: Mapped[list["Hold"]] = relationship(back_populates="account", order_by="Hold.id")
    branch: Mapped["Branch | None"] = relationship()  # noqa: F821

    # what the product says about the account, read as if it were the account's own
    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def cheques_enabled(self) -> bool:
        return self.product.cheques

    @property
    def is_acu(self) -> bool:
        return self.product.is_acu

    @property
    def is_islamic(self) -> bool:
        return self.product.is_islamic

    @property
    def available_balance(self) -> Decimal:
        """The ledger less the holds still in place; nothing on an account that is not active."""
        if self.status is not AccountStatus.ACTIVE:
            return Decimal("0.00")
        held = sum((h.amount for h in self.holds if not h.released), Decimal("0"))
        return self.ledger_balance - held


class Transaction(Timestamps, Base):
    """A posting to an account: positive in, negative out, and the balance it left."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    posted_on: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Money)
    balance_after: Mapped[Decimal] = mapped_column(Money)
    reference: Mapped[str | None] = mapped_column(String(30))


class Hold(Timestamps, Base):
    """Money on an account that cannot be spent yet: a cheque still clearing, a payment earmarked for a date."""

    __tablename__ = "holds"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    reason: Mapped[str] = mapped_column(String(120))
    placed_on: Mapped[date] = mapped_column(Date)
    release_on: Mapped[date | None] = mapped_column(Date)
    released: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    account: Mapped[Account] = relationship(back_populates="holds")


class Maturity(enum.StrEnum):
    RENEW_ALL = "renew_principal_and_interest"
    RENEW_PRINCIPAL = "renew_principal_credit_interest"
    CREDIT_ALL = "credit_principal_and_interest"


class FixedDeposit(Timestamps, Base):
    """The terms of a fixed-deposit account: what was placed, at what rate, for how long, and what happens at maturity."""

    __tablename__ = "fixed_deposits"
    __table_args__ = (CheckConstraint("principal > 0", name="principal_positive"), CheckConstraint("tenor_months > 0", name="tenor_positive"))

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    principal: Mapped[Decimal] = mapped_column(Money)
    rate_pct: Mapped[Decimal] = mapped_column(Rate)
    tenor_months: Mapped[int] = mapped_column(Integer)
    placed_on: Mapped[date] = mapped_column(Date)
    matures_on: Mapped[date] = mapped_column(Date)
    on_maturity: Mapped[Maturity] = mapped_column(choice(Maturity, "maturity"))
    # where interest (or everything) goes at maturity, when not renewed into the deposit
    credit_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))

    account: Mapped[Account] = relationship(foreign_keys=[account_id])
    credit_account: Mapped[Account | None] = relationship(foreign_keys=[credit_account_id])


class IncomingFundStatus(enum.StrEnum):
    CREDITED = "credited"
    PENDING = "pending"


class IncomingFund(Timestamps, Base):
    """Money on its way in (an inward telegraphic transfer). Once credited, it is also a posting on the account."""

    __tablename__ = "incoming_funds"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    received_on: Mapped[date] = mapped_column(Date)
    remitter: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[IncomingFundStatus] = mapped_column(choice(IncomingFundStatus, "incoming_fund_status"))
    reference: Mapped[str] = mapped_column(String(30))


class OwnTransfer(Timestamps, Base):
    """A transfer between two accounts of the same customer."""

    __tablename__ = "own_transfers"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Money)
    # who gave the instruction (the person's reference)
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")


class PaymentKind(enum.StrEnum):
    LOAN = "loan"
    CREDIT_CARD = "credit_card"
    UTILITY = "utility"
    GIRO = "giro"


class Payment(Timestamps, Base):
    """A payment out of an account: a loan instalment, a card bill, a utility bill or an interbank GIRO payment, to one
    of the customer's own loans or cards, a registered bill, or a registered payee."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(30), unique=True)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    kind: Mapped[PaymentKind] = mapped_column(choice(PaymentKind, "payment_kind"))
    payee: Mapped[str] = mapped_column(String(120), default="")
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Money)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("loans.id"))
    card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    bill_id: Mapped[int | None] = mapped_column(ForeignKey("bills.id"))
    payee_id: Mapped[int | None] = mapped_column(ForeignKey("payees.id"))
    instructed_by: Mapped[str] = mapped_column(String(12), default="", server_default="")


class Loan(Timestamps, Base):
    """A loan or financing: what was lent, what is still owed, the instalment and when it is due."""

    __tablename__ = "loans"
    __table_args__ = (CheckConstraint("outstanding >= 0", name="outstanding_not_negative"), CheckConstraint("arrears >= 0", name="arrears_not_negative"))

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    currency: Mapped[str] = mapped_column(String(3))
    principal: Mapped[Decimal] = mapped_column(Money)
    outstanding: Mapped[Decimal] = mapped_column(Money)
    rate_pct: Mapped[Decimal] = mapped_column(Rate)
    tenor_months: Mapped[int] = mapped_column(Integer)
    started_on: Mapped[date] = mapped_column(Date)
    monthly_instalment: Mapped[Decimal] = mapped_column(Money)
    next_due_on: Mapped[date] = mapped_column(Date)
    # instalments due and not paid
    arrears: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    # where the instalment is taken from each month, when the customer set that up
    repayment_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))

    product: Mapped[Product] = relationship(lazy="joined")
