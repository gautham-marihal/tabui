"""Singapore SOA (core banking): balances, history, statements, incoming funds, cheque deposits and books, fixed-deposit
rates, and SMS one-time passwords. Every account route is for a person who holds the account (`person`)."""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import MOCK_OTP
from ..db import get_session
from ..models import ChequeBook, ChequeBookOrder, ChequeDeposit, Delivery, DepositRate, IncomingFund, Market, OneTimePassword, StatementRequest
from ..security import hash_secret, verify_secret
from . import lookups, policy
from .common import compact, day, json_body, last4, money, record, reference, text

router = APIRouter(prefix="/sg/soa", tags=["Singapore: SOA"])
SG = Market.SG


def _readable(db: Session, number: str, person: str):
    """The account, when the person holds it in Singapore; else (None, the refusal)."""
    account = lookups.account(db, SG, number)
    refusal = policy.may_use(db, person, account, market=SG)
    return (None, refusal) if refusal else (account, None)


@router.get("/accounts/{number}/balance")
def balance(number: str, person: str = "", db: Session = Depends(get_session)):
    account, refusal = _readable(db, number, person)
    if refusal:
        return {"found": False, **refusal}
    return {
        "found": True,
        "account_last4": last4(number),
        "type": account.product_name,
        "currency": account.currency,
        "ledger_balance": money(account.ledger_balance),
        "available_balance": money(account.available_balance),
    }


@router.get("/accounts/{number}/incoming-funds")
def incoming_funds(number: str, person: str = "", db: Session = Depends(get_session)):
    account, refusal = _readable(db, number, person)
    if refusal:
        return {"items": [], **refusal}
    rows = db.scalars(select(IncomingFund).where(IncomingFund.account_id == account.id).order_by(IncomingFund.received_on.desc(), IncomingFund.id))
    return {
        "items": [
            {
                "date": day(f.received_on),
                "from": f.remitter,
                "currency": f.currency,
                "amount": money(f.amount),
                "status": f.status.value,
                "reference": f.reference,
            }
            for f in rows
        ]
    }


@router.get("/accounts/{number}/history")
def history(number: str, person: str = "", limit: str = "", db: Session = Depends(get_session)):
    account, refusal = _readable(db, number, person)
    if refusal:
        return {"items": [], **refusal}
    count = int(limit) if limit.isdigit() and int(limit) > 0 else policy.number_setting(db, "history_items", SG)
    return {"items": lookups.history(db, account.id, count)}


@router.post("/accounts/{number}/statements")
def request_statement(number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """A copy of a statement, by post or fax, for one of the months still kept for the phone (older ones need a service
    manager). The fee and the time it takes are the price list's."""
    person = text(body.get("person"))
    account = lookups.account(db, SG, number, for_update=True)
    refusal = policy.may_use(db, person, account, market=SG, transact=True)
    if refusal:
        return refusal
    delivery = text(body.get("delivery")) or "mail"
    if delivery not in ("mail", "fax"):
        return {"ok": False, "reason": "delivery_must_be_mail_or_fax"}
    month = text(body.get("month")) or "latest"
    today = policy.today(db, SG)
    oldest = (today.replace(day=1) - timedelta(days=31 * (policy.number_setting(db, "statement_months_by_phone", SG) - 1))).strftime("%Y-%m")
    if month != "latest" and not (oldest <= month <= today.strftime("%Y-%m")):
        return {"ok": False, "reason": "month_not_available_by_phone", "oldest_month": oldest}
    price = policy.tariff(db, SG, f"statement_{delivery}")
    row = StatementRequest(market=SG, account_id=account.id, account_number=number, month=month, delivery=delivery, instructed_by=person)
    db.add(row)
    db.flush()
    row.reference = reference("STM", row.id)
    if price.fee:
        policy.post(db, account, -price.fee, f"Statement copy fee ({month})", row.reference)
    record(db, "statement_requested", SG, account=last4(number), month=month, delivery=delivery, reference=row.reference, by=person)
    return {
        "ok": True,
        "reference": row.reference,
        "month": month,
        "delivery": delivery,
        "fee": money(price.fee),
        "currency": price.currency,
        "arrives_in_days": price.working_days,
        "arrives_by": day(policy.working_days_after(db, SG, today, price.working_days)),
    }


@router.get("/accounts/{number}/cheque-deposits")
def cheque_deposits(number: str, person: str = "", db: Session = Depends(get_session)):
    account, refusal = _readable(db, number, person)
    if refusal:
        return {"items": [], **refusal}
    rows = db.scalars(select(ChequeDeposit).where(ChequeDeposit.account_id == account.id).order_by(ChequeDeposit.deposited_on.desc(), ChequeDeposit.id))
    return {
        "items": [
            compact(
                {
                    "date": day(d.deposited_on),
                    "cheque_no": d.cheque_no,
                    "amount": money(d.amount),
                    "status": d.status.value,
                    "value_date": day(d.value_date),
                    "reason": d.return_reason,
                }
            )
            for d in rows
        ]
    }


@router.get("/accounts/{number}/cheque-book")
def cheque_book(number: str, person: str = "", db: Session = Depends(get_session)):
    account, refusal = _readable(db, number, person)
    if refusal:
        return {"found": False, **refusal}
    book = db.scalar(select(ChequeBook).where(ChequeBook.account_id == account.id).order_by(ChequeBook.sent_on.desc()))
    if not book:
        return {"found": False}
    return {"found": True, "from": book.first_cheque_no, "to": book.last_cheque_no, "sent_on": day(book.sent_on), "delivery": book.delivery}


@router.post("/accounts/{number}/cheque-book")
def order_cheque_book(number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person = text(body.get("person"))
    account = lookups.account(db, SG, number, for_update=True)
    refusal = policy.may_use(db, person, account, market=SG, transact=True)
    if refusal:
        return refusal
    if not account.cheques_enabled:
        return {"ok": False, "reason": "account_has_no_cheques"}
    wanted = text(body.get("delivery")) or Delivery.NORMAL.value
    if wanted not in {d.value for d in Delivery}:
        return {"ok": False, "reason": "delivery_must_be_normal_express_or_same_day"}
    delivery = Delivery(wanted)
    price = policy.tariff(db, SG, f"cheque_book_{delivery.value}")
    if account.available_balance < price.fee:
        return {"ok": False, "reason": "insufficient_funds_for_fee", "fee": money(price.fee), "currency": price.currency}
    row = ChequeBookOrder(
        market=SG,
        account_number=number,
        account_id=account.id,
        delivery=delivery,
        fee=price.fee,
        ready_in_working_days=price.working_days,
        instructed_by=person,
    )
    db.add(row)
    db.flush()
    row.reference = reference("CBR", row.id)
    if price.fee:
        policy.post(db, account, -price.fee, f"Cheque book fee ({delivery.value.replace('_', ' ')})", row.reference)
    record(db, "cheque_book_requested", SG, account=last4(number), delivery=delivery.value, reference=row.reference, by=person)
    return {
        "ok": True,
        "reference": row.reference,
        "delivery": delivery.value,
        "fee": money(price.fee),
        "currency": price.currency,
        "ready_in_working_days": price.working_days,
        "ready_by": day(policy.working_days_after(db, SG, policy.today(db, SG), price.working_days)),
    }


@router.get("/rates/sgd-td")
def fixed_deposit_rates(db: Session = Depends(get_session)):
    home = policy.identity(db, SG).base_currency
    rows = db.scalars(select(DepositRate).where(DepositRate.market == SG, DepositRate.currency == home).order_by(DepositRate.tenor_months))
    return {"currency": home, "items": [{"tenor_months": r.tenor_months, "rate": money(r.rate_pct)} for r in rows]}


def _otp_person(db: Session, body: dict):
    """Who the one-time password is for: the person who was checked (by their NRIC), else the customer's contact."""
    person = policy.person_by_ref(db, text(body.get("person")))
    if person:
        return person
    customer = lookups.customer(db, SG, text(body.get("cif")))
    return customer.contact if customer else None


@router.post("/otp/send")
def send_otp(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person = _otp_person(db, body)
    if not person:
        return {"sent": False, "reason": "unknown_customer"}
    if not person.mobile:
        return {"sent": False, "reason": "no_mobile_on_file"}
    if person.otp_suspended:
        return {"sent": False, "reason": "otp_suspended"}
    now = policy.now(db, SG)
    # a new password replaces any still waiting
    for waiting in db.scalars(select(OneTimePassword).where(OneTimePassword.person_id == person.id, OneTimePassword.used_at.is_(None))):
        waiting.used_at = now
    lifetime = policy.number_setting(db, "otp_lifetime_minutes")
    db.add(OneTimePassword(person_id=person.id, code_hash=hash_secret(MOCK_OTP), expires_at=now + timedelta(minutes=lifetime)))
    return {"sent": True, "to_mobile_ending": last4(person.mobile), "valid_for_minutes": lifetime}


@router.post("/otp/verify")
def verify_otp(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person = _otp_person(db, body)
    now = policy.now(db, SG)
    pending = (
        db.scalar(
            select(OneTimePassword)
            .where(OneTimePassword.person_id == person.id, OneTimePassword.used_at.is_(None))
            .order_by(OneTimePassword.id.desc())
            .with_for_update()
        )
        if person
        else None
    )
    if not pending:
        return {"valid": False, "reason": "no_otp_sent"}
    if pending.expires_at <= now:
        pending.used_at = now
        return {"valid": False, "reason": "otp_expired"}
    if verify_secret(text(body.get("otp")), pending.code_hash):
        pending.used_at = now
        return {"valid": True}
    pending.attempts += 1
    limit = policy.number_setting(db, "max_wrong_otps")
    if pending.attempts >= limit:
        pending.used_at = now
        person.otp_suspended = True
        record(db, "otp_suspended", SG, person=person.person_ref)
        return {"valid": False, "reason": "otp_suspended"}
    return {"valid": False, "reason": "wrong_otp", "tries_left": limit - pending.attempts}
