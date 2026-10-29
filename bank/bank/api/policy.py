"""The bank's rules, read from its own tables: the country's clock and working days, settings, the price list, phone
numbers, postings to accounts, and who may do what on an account. Nothing here holds a number of its own: change a
setting, a tariff or a holiday in the database and every system follows it."""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    SPENDABLE,
    Account,
    AccountHolder,
    AccountStatus,
    BankIdentity,
    Market,
    Person,
    PublicHoliday,
    Setting,
    Tariff,
    Transaction,
)

WEEKEND = (5, 6)


class MissingReference(LookupError):
    """A setting, tariff or country the bank's tables do not have: the data is incomplete (answered with a 500)."""


def identity(db: Session, market: Market) -> BankIdentity:
    row = db.scalar(select(BankIdentity).where(BankIdentity.market == market))
    if not row:
        raise MissingReference(f"bank_identity for {market.value}")
    return row


def country_name(db: Session, market: Market) -> str:
    return identity(db, market).country_name


def now(db: Session, market: Market) -> datetime:
    return datetime.now(ZoneInfo(identity(db, market).timezone))


def today(db: Session, market: Market) -> date:
    """Today in the country's own time zone."""
    return now(db, market).date()


def setting(db: Session, name: str, market: Market | None = None) -> str:
    """A setting for the country, or the bank-wide one when the country has none of its own."""
    rows = db.scalars(select(Setting).where(Setting.name == name, (Setting.market == market) | Setting.market.is_(None))).all()
    row = next((r for r in rows if r.market is market), None) or next((r for r in rows if r.market is None), None)
    if not row:
        raise MissingReference(f"setting {name}")
    return row.value


def number_setting(db: Session, name: str, market: Market | None = None) -> int:
    return int(setting(db, name, market))


def tariff(db: Session, market: Market, code: str) -> Tariff:
    row = db.scalar(select(Tariff).where(Tariff.market == market, Tariff.code == code))
    if not row:
        raise MissingReference(f"tariff {market.value}/{code}")
    return row


def is_working_day(db: Session, market: Market, day: date) -> bool:
    if day.weekday() in WEEKEND:
        return False
    return not db.scalar(select(PublicHoliday.id).where(PublicHoliday.market == market, PublicHoliday.holiday_on == day))


def working_days_after(db: Session, market: Market, start: date, count: int) -> date:
    """The day `count` working days after `start` (weekends and the country's public holidays skipped)."""
    day = start
    while count > 0:
        day += timedelta(days=1)
        if is_working_day(db, market, day):
            count -= 1
    return day


def normalise_phone(db: Session, raw: Any, market: Market | None = None) -> str:
    """A phone number in E.164. A local number (as dialled in the country) gets the country's code: the line's country
    first, then the others."""
    digits = re.sub(r"[^\d+]", "", str(raw or ""))
    if digits.startswith("+"):
        return digits
    if not digits:
        return ""
    countries = db.scalars(select(BankIdentity).order_by(BankIdentity.id)).all()
    countries.sort(key=lambda c: c.market is not market)
    for country in countries:
        if re.fullmatch(country.local_number_pattern, digits):
            return f"+{country.dialling_code}{digits.removeprefix(country.trunk_prefix)}"
    return f"+{digits}"


def post(db: Session, account: Account, amount: Decimal, description: str, reference: str | None = None, on: date | None = None) -> Transaction:
    """Puts a posting on the account and moves its ledger balance with it. Lock the account (for_update) first."""
    account.ledger_balance += amount
    row = Transaction(
        account_id=account.id,
        posted_on=on or today(db, account.market),
        description=description,
        amount=amount,
        balance_after=account.ledger_balance,
        reference=reference,
    )
    db.add(row)
    return row


def person_by_ref(db: Session, ref: Any) -> Person | None:
    return db.scalar(select(Person).where(Person.person_ref == str(ref or ""))) if ref else None


def holder(db: Session, person: Person, account: Account) -> AccountHolder | None:
    return db.scalar(select(AccountHolder).where(AccountHolder.person_id == person.id, AccountHolder.account_id == account.id))


def may_use(db: Session, person_ref: Any, account: Account | None, *, market: Market | None = None, transact: bool = False, spend: bool = False) -> dict | None:
    """Why the person may not use the account this way (a refusal to answer with), or None when they may.
    transact: a change (a stop order, a statement, a cheque book), which an enquiries-only signatory may not make, on an
    active account only. spend: money leaves it, so it must be an account money can be paid out of."""
    if not account:
        return {"ok": False, "reason": "unknown_account"}
    person = person_by_ref(db, person_ref)
    if not person:
        return {"ok": False, "reason": "caller_not_verified"}
    held = holder(db, person, account)
    if not held:
        return {"ok": False, "reason": "not_one_of_theirs"}
    if market is not None and account.market is not market:
        return {"ok": False, "reason": "account_in_other_country", "country": country_name(db, account.market)}
    if not transact and not spend:
        return None
    if account.status is not AccountStatus.ACTIVE:
        return {"ok": False, "reason": f"account_{account.status.value}"}
    if not held.can_transact:
        return {"ok": False, "reason": "enquiries_only"}
    if spend and account.product.category not in SPENDABLE:
        return {"ok": False, "reason": "cannot_pay_from_this_account", "type": account.product_name}
    return None
