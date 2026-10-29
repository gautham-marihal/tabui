"""The customer hub every line uses, in both countries: who is calling, everything a person may use once they have
logged in, choosing one of their accounts, and its balance and recent postings. Anything that changes an account
(payments, cheques, statements) stays with the systems of the account's own country, as at a real bank.

/hub/reference is what the agents are built from: each country's lines and their hours, holidays, price list, settings,
forms and service codes, so nothing in an agent repeats a number the bank keeps.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import (
    AccountStatus,
    BankIdentity,
    ContactPoint,
    Form,
    HolderRole,
    Investigation,
    Market,
    Person,
    PublicHoliday,
    ServiceCode,
    Setting,
    Tariff,
    Vip,
)
from . import lookups, policy
from .common import day, last4, money

router = APIRouter(prefix="/hub", tags=["Customer hub"])


def _person(db: Session, ref: str) -> Person | None:
    return db.scalar(select(Person).where(Person.person_ref == ref))


def _whose(holder) -> str:
    if holder.role is HolderRole.SIGNATORY:
        return f"for {holder.account.customer.name}"
    return "joint" if holder.role is HolderRole.JOINT else "yours"


def _account_item(db: Session, holder) -> dict:
    a = holder.account
    return {
        "last4": last4(a.account_number),
        "type": a.product_name,
        "currency": a.currency,
        "country": policy.country_name(db, a.market),
        "whose": _whose(holder),
        "status": a.status.value,
        "can_transact": holder.can_transact and a.status is AccountStatus.ACTIVE,
    }


def _spoken(items: list[dict], home: str) -> str:
    """The list as an agent reads it out: "a Current Account in SGD ending 7001, for Acme Trading Pte Ltd; …". Only an
    account in the other country says where it is, and only one that is not active says so."""
    parts = []
    for item in items:
        article = "an" if item["type"][:1].upper() in "AEIOU" else "a"
        where = "" if item["country"] == home else f" in {item['country']}"
        whose = "" if item["whose"] == "yours" else f", {item['whose']}"
        status = "" if item["status"] == "active" else f" ({item['status']})"
        parts.append(f"{article} {item['type']} in {item['currency']} ending {item['last4']}{status}{where}{whose}")
    return "; ".join(parts)


@router.get("/callers/{phone}")
def caller(phone: str, db: Session = Depends(get_session)):
    """Who is calling, from the number they call from, before they log in: a name to greet them by, their language,
    what they usually call about, and whether they are a VIP. Nothing private."""
    person = db.scalar(select(Person).where(Person.mobile == policy.normalise_phone(db, phone)))
    if not person:
        return {"found": False}
    return {
        "found": True,
        "person": person.person_ref,
        "name": person.salutation,
        "language": person.language,
        "favourite": person.favourite_transaction,
        "is_vip": bool(db.scalar(select(Vip.id).where(Vip.person_id == person.id))),
    }


@router.get("/people/{ref}")
def person(ref: str, db: Session = Depends(get_session)):
    """A logged-in person: who they are, whom they bank as (their own banking, the companies they act for), open cases."""
    who = _person(db, ref)
    if not who:
        return {"found": False}
    account_ids = [h.account_id for h in who.holdings]
    cases = db.scalars(select(Investigation).where(Investigation.account_id.in_(account_ids)).order_by(Investigation.id))
    return {
        "found": True,
        "person": who.person_ref,
        "name": who.salutation,
        "full_name": who.full_name,
        "language": who.language,
        "banks_as": [
            {"cif": r.customer.cif, "name": r.customer.name, "country": policy.country_name(db, r.customer.market), "role": r.role.value}
            for r in who.relationships
        ],
        "open_cases": [{"case": c.case_reference, "topic": c.topic, "service_manager": c.service_manager.name} for c in cases],
    }


@router.get("/people/{ref}/accounts")
def accounts(ref: str, country: str = "", db: Session = Depends(get_session)):
    """Every account the person may use, in both countries, and the list as the agent reads it out. `country` is the
    line's (sg or my): its accounts come first; without it, the person's own country's do."""
    who = _person(db, ref)
    if not who:
        return {"found": False, "count": 0, "items": [], "spoken": ""}
    markets = {m.value for m in Market}
    home = next((c for c in (country.lower(), who.nationality.lower()) if c in markets), Market.SG.value)
    holdings = sorted(lookups.holdings_of(db, who), key=lambda h: h.account.market.value != home)
    items = [_account_item(db, h) for h in holdings]
    return {"found": True, "count": len(items), "items": items, "spoken": _spoken(items, policy.country_name(db, Market(home)))}


@router.get("/people/{ref}/accounts/{digits}")
def choose(ref: str, digits: str, db: Session = Depends(get_session)):
    """The account the caller chose, by its last digits: the full number goes to the agent's state, never to its words."""
    who = _person(db, ref)
    wanted = "".join(ch for ch in digits if ch.isdigit())
    holdings = [h for h in lookups.holdings_of(db, who) if h.account.account_number.endswith(wanted)] if who and len(wanted) >= 3 else []
    if len(holdings) != 1:
        return {"found": False, "reason": "ambiguous" if holdings else "not_one_of_theirs"}
    holder = holdings[0]
    a = holder.account
    return {
        "found": True,
        **_account_item(db, holder),
        "number": a.account_number,
        "market": a.market.value,
        "cif": a.customer.cif,
        "cheques": a.cheques_enabled,
    }


@router.get("/accounts/{number}/balance")
def balance(number: str, person: str = "", db: Session = Depends(get_session)):
    """The balance of an account the person holds, in either country."""
    a = lookups.account(db, None, number)
    refusal = policy.may_use(db, person, a)
    if refusal:
        return {"found": False, **refusal}
    held = sum((h.amount for h in a.holds if not h.released), 0)
    return {
        "found": True,
        "account_last4": last4(number),
        "type": a.product_name,
        "currency": a.currency,
        "country": policy.country_name(db, a.market),
        "status": a.status.value,
        "ledger_balance": money(a.ledger_balance),
        "available_balance": money(a.available_balance),
        **({"on_hold": money(held), "holds": [h.reason for h in a.holds if not h.released]} if held else {}),
    }


@router.get("/accounts/{number}/history")
def history(number: str, person: str = "", limit: str = "", db: Session = Depends(get_session)):
    a = lookups.account(db, None, number)
    refusal = policy.may_use(db, person, a)
    if refusal:
        return {"found": False, "items": [], **refusal}
    count = int(limit) if limit.isdigit() and int(limit) > 0 else policy.number_setting(db, "history_items", a.market)
    return {"found": True, "items": lookups.history(db, a.id, count)}


@router.get("/reference")
def reference_data(db: Session = Depends(get_session)):
    """What the agents are built from, per country: the bank, its lines and their hours, public holidays from today,
    the price list, settings, forms and service codes."""
    out = {}
    for country in db.scalars(select(BankIdentity).order_by(BankIdentity.id)):
        m = country.market
        today = policy.today(db, m)
        out[m.value] = {
            "bank": country.bank_name,
            "country": country.country_name,
            "currency": country.base_currency,
            "timezone": country.timezone,
            "today": day(today),
            "account_number_digits": country.account_number_digits,
            "lines": {
                p.code: {"label": p.label, "number": p.display_number, "dial": p.dial_number, "hours": p.hours, "hours_label": p.hours_label}
                for p in db.scalars(select(ContactPoint).where(ContactPoint.market == m).order_by(ContactPoint.id))
            },
            "holidays": [
                {"date": day(h.holiday_on), "name": h.name}
                for h in db.scalars(
                    select(PublicHoliday).where(PublicHoliday.market == m, PublicHoliday.holiday_on >= today).order_by(PublicHoliday.holiday_on)
                )
            ],
            "tariffs": {
                t.code: {"label": t.label, "fee": money(t.fee), "currency": t.currency, "working_days": t.working_days}
                for t in db.scalars(select(Tariff).where(Tariff.market == m).order_by(Tariff.id))
            },
            "settings": {
                s.name: s.value
                for s in sorted(db.scalars(select(Setting).where((Setting.market == m) | Setting.market.is_(None))), key=lambda s: s.market is not None)
            },
            "forms": [{"id": f.code, "title": f.title, "purpose": f.purpose} for f in db.scalars(select(Form).where(Form.market == m).order_by(Form.id))],
        }
    out["service_codes"] = [{"code": s.code, "route": s.route, "label": s.label} for s in db.scalars(select(ServiceCode).order_by(ServiceCode.id))]
    return out
