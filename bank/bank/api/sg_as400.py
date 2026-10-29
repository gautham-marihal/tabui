"""Singapore AS400: phone-code logins, the CIF profile, PIN changes, cheque status and stop-payment, and published rates."""

import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import CredentialKind, CustomerType, ExchangeRate, IdentifierKind, LendingRate, Market, ProductCategory
from ..security import hash_secret, verify_secret
from . import cheques, lookups, policy
from .common import json_body, money, record, text

router = APIRouter(prefix="/sg/as400", tags=["Singapore: AS400"])
SG = Market.SG

# the business line serves the companies a person acts for; someone with only personal banking is told the personal line
LINE_TYPES = (CustomerType.BUSINESS, CustomerType.PERSONAL)


def wrong_secret(db: Session, credential, market: Market, kind: str, person_ref: str) -> dict:
    """Counts a wrong PIN; the last allowed one locks the login. Says how many tries are left."""
    limit = policy.number_setting(db, "max_wrong_pins", market)
    credential.failed_attempts += 1
    if credential.failed_attempts >= limit:
        credential.locked = True
        record(db, f"{kind}_locked", market, person=person_ref)
        return {"ok": False, "code": 62, "reason": "locked"}
    return {"ok": False, "code": 53, "reason": f"invalid_{kind}", "tries_left": limit - credential.failed_attempts}


@router.post("/login")
def login(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Phone code, then PIN. code: 0 ok, 83 phone code unknown, 53 wrong PIN, 62 locked (too many wrong PINs).
    The person is served as the company they act for (or as themselves); `person` names them for every account they hold."""
    person = lookups.by_login_code(db, SG, IdentifierKind.PHONE_CODE, text(body.get("phone_code")))
    credential = lookups.credential(db, person, CredentialKind.PIN) if person else None
    customer = lookups.line_customer(db, person, SG, LINE_TYPES) if person else None
    if not person or not credential or not customer:
        return {"ok": False, "code": 83, "reason": "invalid_phone_code"}
    if credential.locked:
        return {"ok": False, "code": 62, "reason": "locked"}
    if "pin" not in body:
        return {"ok": True, "code": 0, "phone_code_valid": True}
    if not verify_secret(text(body["pin"]), credential.secret_hash):
        return wrong_secret(db, credential, SG, "pin", person.person_ref)
    credential.failed_attempts = 0
    return {
        "ok": True,
        "code": 0,
        "cif": customer.cif,
        "user_type": customer.customer_type.value,
        "access_level": customer.access_level.value,
        "person": person.person_ref,
        "name": person.salutation,
    }


@router.get("/cif/{cif}")
def profile(cif: str, db: Session = Depends(get_session)):
    """Who the customer is, what access they have, and their accounts with what each allows."""
    customer = lookups.customer(db, SG, cif)
    if not customer:
        return {"found": False}
    accounts = lookups.accounts_of(db, customer)
    contact = customer.contact
    return {
        "found": True,
        "cif": customer.cif,
        "name": customer.name,
        "contact": contact.full_name if contact else None,
        "user_type": customer.customer_type.value,
        "access_level": customer.access_level.value if customer.access_level else None,
        "segment": customer.segment.value if customer.segment else None,
        "service_manager": customer.service_manager.name if customer.service_manager else None,
        "accounts": [lookups.account_summary(a, ("acu", "dormant")) for a in accounts],
        "has_ca": any(a.product.category is ProductCategory.CURRENT and not a.is_acu for a in accounts),
        "has_acu": any(a.is_acu for a in accounts),
        "has_acu_chq": any(a.is_acu and a.cheques_enabled for a in accounts),
        "bizconn": customer.business_internet_banking,
    }


@router.get("/cif/{cif}/accounts/{digits}")
def account_by_last4(cif: str, digits: str, db: Session = Depends(get_session)):
    return lookups.find_by_last4(db, SG, cif, digits)


@router.post("/pin")
def change_pin(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """A new 6-digit phone PIN, given the current one. A wrong current PIN counts towards the lock, as at login."""
    person = lookups.by_login_code(db, SG, IdentifierKind.PHONE_CODE, text(body.get("phone_code")))
    credential = lookups.credential(db, person, CredentialKind.PIN) if person else None
    old, new = text(body.get("old_pin")), text(body.get("new_pin"))
    if not credential:
        return {"ok": False, "reason": "invalid_phone_code"}
    if credential.locked:
        return {"ok": False, "reason": "locked"}
    if not verify_secret(old, credential.secret_hash):
        answer = wrong_secret(db, credential, SG, "pin", person.person_ref)
        return {"ok": False, "reason": answer["reason"], **({"tries_left": answer["tries_left"]} if "tries_left" in answer else {})}
    if "confirm" in body and text(body.get("confirm")) != new:
        return {"ok": False, "reason": "pins_do_not_match"}
    if not re.fullmatch(r"\d{6}", new):
        return {"ok": False, "reason": "new_pin_must_be_6_digits"}
    if new == old:
        return {"ok": False, "reason": "same_as_old"}
    credential.secret_hash = hash_secret(new)
    credential.failed_attempts = 0
    record(db, "pin_changed", SG, person=person.person_ref)
    return {"ok": True}


@router.get("/cheques/{account_number}/{cheque_no}")
def cheque_status(account_number: str, cheque_no: str, person: str = "", db: Session = Depends(get_session)):
    return cheques.status(db, SG, account_number, cheque_no, person)


@router.post("/cheques/{account_number}/stop")
def stop_payment(account_number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return cheques.stop(db, SG, account_number, body, "STP")


@router.get("/rates/prime")
def prime_rate(db: Session = Depends(get_session)):
    rate = db.scalar(select(LendingRate).where(LendingRate.market == SG, LendingRate.name == "prime"))
    return {"prime_rate_pct": money(rate.rate_pct) if rate else None, "label": rate.label if rate else ""}


@router.get("/rates/fx/{currency}")
def fx_rate(currency: str, db: Session = Depends(get_session)):
    code = currency.upper()
    rate = db.scalar(select(ExchangeRate).where(ExchangeRate.market == SG, ExchangeRate.currency == code))
    if not rate:
        return {"found": False}
    home = policy.identity(db, SG).base_currency
    limit = policy.number_setting(db, "fx_indicative_limit", SG)
    return {
        "found": True,
        "currency": code,
        "bank_buys_sgd_per_unit": float(rate.bank_buys),
        "bank_sells_sgd_per_unit": float(rate.bank_sells),
        "note": f"Indicative, for amounts below {home} {limit:,}",
    }
