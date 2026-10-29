"""The CRM: what other apps (the TAB showcase, Weave Studio's Integrations, agents' tools) read and do with the bank's
customers. Every route asks for the key (BANK_API_KEY) as "Authorization: Bearer <key>".

What is shown is masked: an account or card number as ****1234, a phone number with only its last four digits, and
never a PIN, code or full ID number. A PIN or TPIN is checked here (verify), never handed out.
"""

import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import MOCK_OTP, settings
from ..db import get_session
from ..models import (
    Account,
    AuditEvent,
    Booking,
    Callback,
    CallbackStatus,
    Card,
    CredentialKind,
    Customer,
    DirectDebit,
    DocumentType,
    HandOver,
    HandOverOutcome,
    IdentifierKind,
    Investigation,
    Loan,
    Market,
    OneTimePassword,
    Person,
    Relationship,
    ServiceRequest,
    Transaction,
    Vip,
)
from ..security import hash_secret, verify_secret
from . import lookups, policy
from .common import day, json_body, last4, money, open_callback, record, reference, text


def require_key(authorization: str = Header(default="")) -> None:
    """The caller must send the CRM key. With no key set on the bank, the CRM answers no one (it is not left open)."""
    if not settings.crm_api_key:
        raise HTTPException(503, "crm_key_not_set")
    given = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(given.encode(), settings.crm_api_key.encode()):
        raise HTTPException(401, "missing_or_wrong_key")


router = APIRouter(prefix="/crm", tags=["CRM"], dependencies=[Depends(require_key)])


# ---- how records are shown
def masked_number(number: str | None) -> str:
    return f"****{last4(number)}" if number else ""


def masked_phone(phone: str | None) -> str:
    return f"{phone[:3]} ****{last4(phone)}" if phone and len(phone) > 7 else ("****" if phone else "")


def customer_row(customer: Customer, accounts: int = 0, cards: int = 0) -> dict:
    contact = customer.contact
    return {
        "cif": customer.cif,
        "market": customer.market.value,
        "name": customer.name,
        "contact": contact.full_name if contact else "",
        "type": customer.customer_type.value,
        "segment": customer.segment.value if customer.segment else "",
        "access_level": customer.access_level.value if customer.access_level else "",
        "mobile": masked_phone(contact.mobile if contact else None),
        "accounts": accounts,
        "cards": cards,
    }


def account_row(account: Account) -> dict:
    return {
        "number": masked_number(account.account_number),
        "last4": last4(account.account_number),
        "product": account.product_name,
        "currency": account.currency,
        "ledger_balance": money(account.ledger_balance),
        "available_balance": money(account.available_balance),
        "status": account.status.value,
        "opened_on": day(account.opened_on),
        "cheques": account.cheques_enabled,
        "islamic": account.is_islamic,
    }


def _customer_or_404(db: Session, cif: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.cif == cif))
    if not customer:
        raise HTTPException(404, "no_such_customer")
    return customer


# ---- reading
@router.get("/health")
def health(db: Session = Depends(get_session)):
    """Whether the CRM and its database answer: what a connection check calls."""
    return {"ok": True, "database": "up", "customers": db.scalar(select(func.count(Customer.id)))}


@router.get("/summary")
def summary(db: Session = Depends(get_session)):
    count = lambda model, *where: db.scalar(select(func.count(model.id)).where(*where))  # noqa: E731
    return {
        "people": count(Person),
        "customers": count(Customer),
        "accounts": count(Account),
        "cards": count(Card),
        "open_callbacks": count(Callback, Callback.status == CallbackStatus.OPEN),
        "bookings": count(Booking, Booking.cancelled.is_(False)),
        "hand_overs": count(HandOver),
        "service_requests": count(ServiceRequest),
    }


@router.get("/customers")
def customers(q: str = "", market: str = "", limit: int = 50, db: Session = Depends(get_session)):
    """Customers, newest first: by name, the name of someone who acts for them, CIF, or the last digits of a mobile or
    an account."""
    query = select(Customer).order_by(Customer.id.desc()).limit(max(1, min(limit, 200)))
    if market in {m.value for m in Market}:
        query = query.where(Customer.market == Market(market))
    words = q.strip()
    if words:
        like = f"%{words}%"
        digits = "".join(ch for ch in words if ch.isdigit())
        linked = select(Relationship.customer_id).join(Person, Person.id == Relationship.person_id)
        conditions = [Customer.name.ilike(like), Customer.cif.ilike(like), Customer.id.in_(linked.where(Person.full_name.ilike(like)))]
        if len(digits) >= 4:
            conditions.append(Customer.id.in_(linked.where(Person.mobile.like(f"%{digits}"))))
            conditions.append(Customer.id.in_(select(Account.customer_id).where(Account.account_number.like(f"%{digits}"))))
        query = query.where(or_(*conditions))
    rows = list(db.scalars(query))
    ids = [c.id for c in rows]
    accounts = dict(db.execute(select(Account.customer_id, func.count()).where(Account.customer_id.in_(ids)).group_by(Account.customer_id)).all())
    cards = dict(db.execute(select(Card.customer_id, func.count()).where(Card.customer_id.in_(ids)).group_by(Card.customer_id)).all())
    return {"items": [customer_row(c, accounts.get(c.id, 0), cards.get(c.id, 0)) for c in rows]}


@router.get("/customers/{cif}")
def customer(cif: str, db: Session = Depends(get_session)):
    """One customer's whole picture: the people behind it, accounts, cards, loans, direct debits, open cases and recent
    dealings."""
    owner = _customer_or_404(db, cif)
    accounts = lookups.accounts_of(db, owner)
    account_ids = [a.id for a in accounts]
    cards = list(db.scalars(select(Card).where(Card.customer_id == owner.id).order_by(Card.id)))
    loans = db.scalars(select(Loan).where(Loan.customer_id == owner.id).order_by(Loan.id))
    debits = db.scalars(select(DirectDebit).where(DirectDebit.customer_id == owner.id).order_by(DirectDebit.id))
    cases = db.scalars(select(Investigation).where(Investigation.account_id.in_(account_ids)).order_by(Investigation.id))
    callbacks = db.scalars(select(Callback).where(Callback.cif == cif).order_by(Callback.id.desc()).limit(10))
    hand_overs = db.scalars(select(HandOver).where(HandOver.cif == cif).order_by(HandOver.id.desc()).limit(10))
    requests = db.scalars(select(ServiceRequest).where(ServiceRequest.cif == cif).order_by(ServiceRequest.id.desc()).limit(10))
    by_id = {a.id: a for a in accounts}
    return {
        **customer_row(owner, len(accounts), len(cards)),
        "iq_member": owner.iq_member,
        "registration_number": owner.registration_number or "",
        "customer_since": day(owner.customer_since),
        "risk_rating": owner.risk_rating.value,
        "home_branch": owner.home_branch.name if owner.home_branch else "",
        "service_manager": owner.service_manager.name if owner.service_manager else "",
        "people": [{"person": p.person_ref, "name": p.full_name, "role": role.value} for p, role in lookups.people_of(db, owner)],
        "accounts": [account_row(a) for a in accounts],
        "cards": [
            {
                "number": masked_number(c.last4),
                "last4": c.last4,
                "product": c.product.name,
                "kind": c.product.category.value,
                "holder": c.holder.full_name,
                "status": c.status.value,
                "limit": money(c.credit_limit),
                "balance": money(c.outstanding_balance),
                "minimum_due": money(c.minimum_due),
                "due": day(c.due_on),
            }
            for c in cards
        ],
        "loans": [
            {
                "id": loan.loan_number,
                "product": loan.product.name,
                "monthly": money(loan.monthly_instalment),
                "outstanding": money(loan.outstanding),
                "due": day(loan.next_due_on),
            }
            for loan in loans
        ],
        "direct_debits": [{"id": d.mandate_reference, "merchant": d.merchant, "amount": money(d.amount), "status": d.status.value} for d in debits],
        "cases": [
            {"id": c.case_reference, "topic": c.topic, "service_manager": c.service_manager.name, "account": masked_number(by_id[c.account_id].account_number)}
            for c in cases
        ],
        "callbacks": [
            {"id": c.reference, "number": masked_phone(c.callback_number), "reason": c.reason, "status": c.status.value, "at": c.created_at.isoformat()}
            for c in callbacks
        ],
        "hand_overs": [
            {"id": h.reference, "queue": h.skillset or "general", "reason": h.intent, "summary": h.summary, "at": h.created_at.isoformat()} for h in hand_overs
        ],
        "service_requests": [{"id": r.sr_number, "type": r.request_type, "notes": r.notes, "at": r.created_at.isoformat()} for r in requests],
    }


@router.get("/customers/{cif}/transactions")
def transactions(cif: str, account: str = "", limit: int = 10, db: Session = Depends(get_session)):
    """Recent postings, newest first: on one account (by its last four digits) or all of the customer's."""
    owner = _customer_or_404(db, cif)
    accounts = [a for a in lookups.accounts_of(db, owner) if not account or a.account_number.endswith(account)]
    by_id = {a.id: a for a in accounts}
    rows = db.scalars(
        select(Transaction)
        .where(Transaction.account_id.in_(by_id))
        .order_by(Transaction.posted_on.desc(), Transaction.id.desc())
        .limit(max(1, min(limit, 100)))
    )
    return {
        "items": [
            {
                "date": day(t.posted_on),
                "account": masked_number(by_id[t.account_id].account_number),
                "description": t.description,
                "amount": money(t.amount),
                "balance": money(t.balance_after),
            }
            for t in rows
        ]
    }


@router.get("/lookup")
def lookup_caller(phone: str, db: Session = Depends(get_session)):
    """Who is calling, from the number they call from: the person, the customer they bank as, their language, whether
    they are a VIP and their service manager."""
    person = db.scalar(select(Person).where(Person.mobile == policy.normalise_phone(db, phone)))
    if not person:
        return {"found": False}
    vip = db.scalar(select(Vip).where(Vip.person_id == person.id))
    first = person.relationships[0].customer if person.relationships else None
    manager = vip.service_manager if vip else (first.service_manager if first else None)
    return {
        "found": True,
        "person": person.person_ref,
        "cif": first.cif if first else "",
        "name": person.full_name,
        "language": person.language,
        "is_vip": bool(vip),
        "service_manager": manager.name if manager else "",
        "open_callback": open_callback(db, first.market, person.mobile)["open"] if first else False,
    }


@router.get("/activity")
def activity(limit: int = 50, db: Session = Depends(get_session)):
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(max(1, min(limit, 500))))
    return {"items": [{"at": e.at.isoformat(), "kind": e.kind, **({"market": e.market.value} if e.market else {}), **e.details} for e in rows]}


# ---- verifying who is calling
@router.post("/verify")
def verify(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Checks a caller: their login code (phone code or key code, or a Malaysian IC), or a CIF and the person (else the
    customer's contact), and their PIN (Singapore) or TPIN (Malaysia). Too many wrong tries lock it, as the bank's own
    lines do."""
    person, owner, market = None, None, None
    if body.get("cif"):
        owner = db.scalar(select(Customer).where(Customer.cif == text(body["cif"])))
        linked = [p for p, _ in lookups.people_of(db, owner)] if owner else []
        wanted = text(body.get("person"))
        person = next((p for p in linked if p.person_ref == wanted), None) if wanted else (owner.contact if owner else None)
        market = owner.market if owner else None
    elif body.get("code"):
        code = text(body["code"])
        for each_market in Market:
            for kind in IdentifierKind:
                found = lookups.by_login_code(db, each_market, kind, code)
                if found and not person:
                    person, market = found, each_market
        if not person:
            person, market = lookups.by_id_number(db, DocumentType.MYKAD, code), Market.MY
        if person:
            owner = next((r.customer for r in person.relationships if r.customer.market is market), None)
    if not person or not owner:
        return {"verified": False, "reason": "unknown_customer"}
    kind = CredentialKind.PIN if market is Market.SG else CredentialKind.TPIN
    credential = lookups.credential(db, person, kind)
    if not credential:
        return {"verified": False, "reason": "no_pin_on_file"}
    if credential.locked:
        return {"verified": False, "reason": "locked"}
    limit = policy.number_setting(db, "max_wrong_pins", market)
    if not verify_secret(text(body.get("secret")), credential.secret_hash):
        credential.failed_attempts += 1
        if credential.failed_attempts >= limit:
            credential.locked = True
            record(db, f"{kind.value}_locked", market, person=person.person_ref, via="crm")
            return {"verified": False, "reason": "locked"}
        return {"verified": False, "reason": f"wrong_{kind.value}", "tries_left": limit - credential.failed_attempts}
    credential.failed_attempts = 0
    record(db, "customer_verified", market, person=person.person_ref, cif=owner.cif, via="crm")
    return {
        "verified": True,
        "cif": owner.cif,
        "name": owner.name,
        "market": owner.market.value,
        "type": owner.customer_type.value,
        "person": person.person_ref,
        "person_name": person.full_name,
    }


def _otp_person(db: Session, body: dict) -> tuple[Person | None, Customer | None]:
    owner = db.scalar(select(Customer).where(Customer.cif == text(body.get("cif"))))
    wanted = text(body.get("person"))
    if owner and wanted:
        return next((p for p, _ in lookups.people_of(db, owner) if p.person_ref == wanted), None), owner
    return (owner.contact if owner else None), owner


@router.post("/otp/send")
def send_otp(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person, owner = _otp_person(db, body)
    if not person:
        return {"sent": False, "reason": "unknown_customer"}
    if not person.mobile:
        return {"sent": False, "reason": "no_mobile_on_file"}
    if person.otp_suspended:
        return {"sent": False, "reason": "otp_suspended"}
    now = policy.now(db, owner.market)
    for waiting in db.scalars(select(OneTimePassword).where(OneTimePassword.person_id == person.id, OneTimePassword.used_at.is_(None))):
        waiting.used_at = now
    lifetime = policy.number_setting(db, "otp_lifetime_minutes")
    db.add(OneTimePassword(person_id=person.id, code_hash=hash_secret(MOCK_OTP), expires_at=now + timedelta(minutes=lifetime)))
    return {"sent": True, "to_mobile_ending": last4(person.mobile), "valid_for_minutes": lifetime}


@router.post("/otp/verify")
def verify_otp(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person, owner = _otp_person(db, body)
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
    now = policy.now(db, owner.market)
    if pending.expires_at <= now:
        pending.used_at = now
        return {"valid": False, "reason": "otp_expired"}
    if verify_secret(text(body.get("code")), pending.code_hash):
        pending.used_at = now
        record(db, "otp_verified", owner.market, cif=owner.cif, person=person.person_ref, via="crm")
        return {"valid": True}
    pending.attempts += 1
    limit = policy.number_setting(db, "max_wrong_otps")
    if pending.attempts >= limit:
        pending.used_at = now
        person.otp_suspended = True
        record(db, "otp_suspended", owner.market, cif=owner.cif, person=person.person_ref, via="crm")
        return {"valid": False, "reason": "otp_suspended"}
    return {"valid": False, "reason": "wrong_otp", "tries_left": limit - pending.attempts}


# ---- what a call leaves behind
def _market_of(db: Session, body: dict) -> tuple[Market | None, str]:
    """The market from the customer, else from the body ('sg' or 'my')."""
    cif = text(body.get("cif"))
    owner = db.scalar(select(Customer).where(Customer.cif == cif)) if cif else None
    if owner:
        return owner.market, owner.cif
    wanted = text(body.get("market")).lower()
    return (Market(wanted) if wanted in {m.value for m in Market} else None), ""


@router.post("/hand-overs")
def hand_over(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """The agent passes the caller to people: the queue, why, and a summary so nobody asks the caller again."""
    market, cif = _market_of(db, body)
    if not market:
        return {"ok": False, "reason": "customer_or_market_required"}
    priority = "high" if text(body.get("priority")) == "high" else "normal"
    row = HandOver(
        market=market,
        cif=cif,
        skillset=text(body.get("queue")) or "general",
        priority=priority,
        intent=text(body.get("reason"))[:120],
        summary=text(body.get("summary"))[:1000],
        outcome=HandOverOutcome.TRANSFERRED,
        screen_pop={},
    )
    db.add(row)
    db.flush()
    row.reference = reference("HO", row.id)
    record(db, "hand_over", market, id=row.reference, cif=cif, queue=row.skillset, priority=priority, reason=row.intent, via="crm")
    wait = policy.number_setting(db, f"queue_wait_{priority}_s", market)
    return {"ok": True, "reference": row.reference, "queue": row.skillset, "estimated_wait_s": wait}


@router.post("/callbacks")
def callback(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    market, cif = _market_of(db, body)
    number = text(body.get("number"))
    digits = "".join(ch for ch in number if ch.isdigit())
    if not market:
        return {"ok": False, "reason": "customer_or_market_required"}
    shortest, longest = policy.number_setting(db, "callback_number_min_digits"), policy.number_setting(db, "callback_number_max_digits")
    if not shortest <= len(digits) <= longest:
        return {"ok": False, "reason": f"number_must_be_{shortest}_to_{longest}_digits"}
    phone = policy.normalise_phone(db, number, market)
    existing = open_callback(db, market, phone)
    if existing["open"]:
        return {"ok": True, "already_requested": True, "reference": existing["request_id"]}
    row = Callback(market=market, cif=cif, caller_phone=phone, callback_number=number, reason=text(body.get("reason"))[:200])
    db.add(row)
    db.flush()
    row.reference = reference("CB", row.id)
    record(db, "callback_requested", market, id=row.reference, cif=cif, number=masked_phone(row.caller_phone), via="crm")
    return {"ok": True, "reference": row.reference}


@router.post("/service-requests")
def service_request(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    market, cif = _market_of(db, body)
    if not cif:
        return {"ok": False, "reason": "unknown_customer"}
    row = ServiceRequest(
        cif=cif,
        account_number=text(body.get("account_last4"))[-4:],
        request_type=text(body.get("type"))[:60],
        category=text(body.get("category"))[:60],
        notes=text(body.get("notes"))[:500],
    )
    db.add(row)
    db.flush()
    row.sr_number = reference("SR", row.id, digits=7)
    record(db, "service_request", market, sr=row.sr_number, cif=cif, type=row.request_type, via="crm")
    return {"ok": True, "sr_number": row.sr_number}
