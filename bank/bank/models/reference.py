"""What the bank publishes and decides: the bank in each country, its settings, its price list, its phone lines and their
hours, public holidays, interest and exchange rates, promotions and forms. Every rule the systems apply (how many wrong
PINs lock a login, what a stop-cheque costs, when the service centre is open) is read from here, never written in code."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, FxRate, Money, Rate, Timestamps
from .common import Market, MarketColumn


class BankIdentity(Timestamps, Base):
    """The bank in one country: its name, the country's currency, clock and phone numbering, and the codes a customer
    gives to receive payments (GIRO bank code, SWIFT)."""

    __tablename__ = "bank_identity"

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn, unique=True)
    bank_name: Mapped[str] = mapped_column(String(120))
    country_name: Mapped[str] = mapped_column(String(60))
    base_currency: Mapped[str] = mapped_column(String(3))
    # an IANA time zone: "today" and office hours are the country's own
    timezone: Mapped[str] = mapped_column(String(40))
    # how a local phone number becomes E.164: +<dialling code><number without its trunk prefix>
    dialling_code: Mapped[str] = mapped_column(String(4))
    trunk_prefix: Mapped[str] = mapped_column(String(2), default="", server_default="")
    # a regular expression for a local number as it is dialled at home (8 digits in Singapore; 0 and 9 to 10 more in Malaysia)
    local_number_pattern: Mapped[str] = mapped_column(String(40))
    account_number_digits: Mapped[int] = mapped_column(Integer)
    giro_bank_code: Mapped[str] = mapped_column(String(10))
    swift_bic: Mapped[str] = mapped_column(String(11))
    branch_code_note: Mapped[str] = mapped_column(String(200))


class Setting(Timestamps, Base):
    """A rule the bank's systems follow, by name: for one country, or for both when the market is empty."""

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("market", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market | None] = mapped_column(MarketColumn)
    name: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(200))


class Tariff(Timestamps, Base):
    """One service on the bank's price list: what it costs and how many working days it takes."""

    __tablename__ = "tariffs"
    __table_args__ = (
        UniqueConstraint("market", "code"),
        CheckConstraint("fee >= 0", name="fee_not_negative"),
        CheckConstraint("working_days >= 0", name="working_days_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    code: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    fee: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3))
    working_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ContactPoint(Timestamps, Base):
    """A phone line or desk of the bank, and when people answer it. `hours` is a list of {days, start, end}; an empty
    list means around the clock."""

    __tablename__ = "contact_points"
    __table_args__ = (UniqueConstraint("market", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    code: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    # as a customer is told it ("6538 1111") and as it is dialled (+6565381111)
    display_number: Mapped[str] = mapped_column(String(30))
    dial_number: Mapped[str] = mapped_column(String(16))
    hours: Mapped[list] = mapped_column(JSONB, default=list)
    hours_label: Mapped[str] = mapped_column(String(120))


class PublicHoliday(Timestamps, Base):
    """A day the country's branches and service centre are closed."""

    __tablename__ = "public_holidays"
    __table_args__ = (UniqueConstraint("market", "holiday_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    holiday_on: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(80))


class LendingRate(Timestamps, Base):
    """A published lending rate: prime (SG); base rate, BLR and the Islamic base financing rate (MY)."""

    __tablename__ = "lending_rates"
    __table_args__ = (UniqueConstraint("market", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    name: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(80), default="", server_default="")
    rate_pct: Mapped[Decimal] = mapped_column(Rate)


class DepositRate(Timestamps, Base):
    """A fixed-deposit rate by currency and term."""

    __tablename__ = "deposit_rates"
    __table_args__ = (
        UniqueConstraint("market", "currency", "tenor_months"),
        CheckConstraint("tenor_months > 0", name="tenor_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    currency: Mapped[str] = mapped_column(String(3))
    tenor_months: Mapped[int] = mapped_column(Integer)
    rate_pct: Mapped[Decimal] = mapped_column(Rate)


class ExchangeRate(Timestamps, Base):
    """What the bank pays (buys) and charges (sells) in local currency for one unit of a foreign one."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("market", "currency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    currency: Mapped[str] = mapped_column(String(3))
    bank_buys: Mapped[Decimal] = mapped_column(FxRate)
    bank_sells: Mapped[Decimal] = mapped_column(FxRate)


class Promotion(Timestamps, Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    title: Mapped[str] = mapped_column(String(200))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)


class Form(Timestamps, Base):
    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    title: Mapped[str] = mapped_column(String(200))
    # what it is for, so an agent can name the right one ("pin_reset", "velocity_application")
    purpose: Mapped[str] = mapped_column(String(40), default="", server_default="")
    by_fax: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
