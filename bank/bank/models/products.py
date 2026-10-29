"""The bank's product list: every account, fixed deposit, loan and card is one of these, so what it is called, what it
pays or charges and what it allows (cheques, ACU, Islamic) is kept once, not on each account."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, Money, Rate, Timestamps
from .common import Market, MarketColumn, choice


class ProductCategory(enum.StrEnum):
    CURRENT = "current"
    SAVINGS = "savings"
    FIXED_DEPOSIT = "fixed_deposit"
    FOREIGN_CURRENCY = "foreign_currency"
    LOAN = "loan"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"


# what money can be paid out of: anything but a deposit, a loan or a card
SPENDABLE = (ProductCategory.CURRENT, ProductCategory.SAVINGS, ProductCategory.FOREIGN_CURRENCY)


class Product(Timestamps, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("market", "code"),
        CheckConstraint("minimum_balance >= 0", name="minimum_balance_not_negative"),
        CheckConstraint("monthly_fee >= 0 AND fall_below_fee >= 0 AND annual_fee >= 0", name="fees_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(60))
    category: Mapped[ProductCategory] = mapped_column(choice(ProductCategory, "product_category"))
    for_business: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # an account in this product may write cheques
    cheques: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # an Asian Currency Unit account (Singapore, foreign currency)
    is_acu: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_islamic: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # the interest it pays (deposits) or charges (loans, cards), per annum; empty when it pays none
    interest_rate_pct: Mapped[Decimal | None] = mapped_column(Rate)
    minimum_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    fall_below_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    monthly_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    annual_fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
