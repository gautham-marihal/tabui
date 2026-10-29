"""What every bank system's routes share: reading the request body, turning stored values into answers, references,
the audit log, and what several systems do alike (branch search, hand-overs, call-backs, surveys, faxes)."""

import json
import math
import re
from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent, Branch, Callback, CallbackStatus, Customer, FaxJob, HandOver, HandOverOutcome, Market, ServiceManager, Survey
from . import policy

CENT = Decimal("0.01")


class BodyNotJson(Exception):
    """A request body that cannot be read as JSON (answered with a 400)."""


async def json_body(request: Request) -> dict:
    """The request's JSON object; an empty body is {}, and anything but an object is treated as {}."""
    raw = await request.body()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise BodyNotJson from error
    return value if isinstance(value, dict) else {}


def text(value: Any) -> str:
    """A body field as text, the way the agents send it: missing, null, false or 0 read as ''."""
    if value is None or value is False or value == "" or value == 0:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def amount_of(value: Any) -> Decimal | None:
    """An amount above zero, rounded to cents; None for anything else (text, null, zero, negative, not finite)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None
    if not number.is_finite() or number <= 0:
        return None
    return number.quantize(CENT)


def money(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def day(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def clock(value: time) -> str:
    return value.strftime("%H:%M")


def compact(answer: dict) -> dict:
    """Leaves out what has no value, as the bank's systems do (a cheque not paid has no paid_on)."""
    return {key: value for key, value in answer.items() if value is not None}


def last4(value: str) -> str:
    return str(value)[-4:]


def reference(prefix: str, row_id: int, digits: int = 6) -> str:
    """A reference a caller can read back: the kind of record and its number (STP-000012)."""
    return f"{prefix}-{row_id:0{digits}d}"


def record(db: Session, kind: str, market: Market | None = None, **details: Any) -> None:
    """Adds a line to the audit log. Details are references and last-four digits only, never a PIN or code."""
    db.add(AuditEvent(kind=kind, market=market, details=_plain(details)))


def _plain(details: dict) -> dict:
    out = {}
    for key, value in details.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, (date, time)):
            value = value.isoformat()
        out[key] = value
    return out


def branch_answer(b: Branch) -> dict:
    return {"id": b.code, "name": b.name, "address": b.address, "hours": b.opening_hours, "area": b.area, "phone": b.phone}


def branches_matching(db: Session, market: Market, query: str | None) -> list[dict]:
    """A market's branches, or those whose name, address or area has any of the words asked for."""
    rows = db.scalars(select(Branch).where(Branch.market == market).order_by(Branch.id)).all()
    words = [w for w in str(query or "").lower().split() if w]
    if words:
        rows = [b for b in rows if any(w in f"{b.name} {b.address} {b.area}".lower() for w in words)]
    return [branch_answer(b) for b in rows]


def hand_over(db: Session, market: Market, body: dict, headers: dict) -> dict:
    """Passes the call to a queue of people, with what they should know. A named service manager who is away makes it a
    call-back instead (the agent offers one)."""
    manager = None
    if body.get("service_manager_id"):
        manager = db.scalar(select(ServiceManager).where(ServiceManager.code == text(body["service_manager_id"])))
    cif = text(body.get("cif"))
    known = db.scalar(select(Customer.cif).where(Customer.cif == cif)) if cif else None
    priority = "high" if text(body.get("priority")) == "high" else "normal"
    row = HandOver(
        market=market,
        cif=known or "",
        skillset=text(body.get("skillset")),
        priority=priority,
        intent=text(body.get("intent"))[:120],
        summary=text(body.get("summary"))[:1000],
        service_manager_id=manager.id if manager else None,
        screen_pop={key: value for key, value in headers.items() if key.startswith("x-")},
        outcome=HandOverOutcome.UNAVAILABLE if manager and not manager.available else HandOverOutcome.TRANSFERRED,
    )
    db.add(row)
    db.flush()
    row.reference = reference("HO", row.id)
    details = {"id": row.reference, "cif": row.cif, "skillset": row.skillset, "priority": priority, "intent": row.intent, "outcome": row.outcome.value}
    record(db, "hand_over", market, **details)
    if row.outcome is HandOverOutcome.UNAVAILABLE:
        return {"ok": False, "transferred": False, "reason": "service_manager_unavailable", "name": manager.name, "reference": row.reference}
    wait = policy.number_setting(db, f"queue_wait_{priority}_s", market)
    return {"ok": True, "transferred": True, "reference": row.reference, "queue": row.skillset or "general", "estimated_wait_s": wait}


def open_callback(db: Session, market: Market, phone: str) -> dict:
    """The call-back this number already asked for, if one is still open: a caller is never booked twice."""
    row = db.scalar(
        select(Callback)
        .where(Callback.market == market, Callback.caller_phone == policy.normalise_phone(db, phone, market), Callback.status == CallbackStatus.OPEN)
        .order_by(Callback.id)
    )
    return {"open": True, "request_id": row.reference, "number": row.callback_number, "reason": row.reason} if row else {"open": False}


def request_callback(db: Session, market: Market, body: dict) -> dict:
    number = text(body.get("number") or body.get("caller"))
    digits = re.sub(r"[\s-]", "", number)
    shortest, longest = policy.number_setting(db, "callback_number_min_digits"), policy.number_setting(db, "callback_number_max_digits")
    if not re.fullmatch(rf"\+?\d{{{shortest},{longest}}}", digits):
        return {"ok": False, "reason": f"number_must_be_{shortest}_to_{longest}_digits"}
    # the caller ID, when it is a real number (a browser call has none): else the number given
    given = policy.normalise_phone(db, body.get("caller"), market)
    caller = given if len(re.sub(r"\D", "", given)) >= shortest else policy.normalise_phone(db, number, market)
    existing = open_callback(db, market, caller)
    if existing["open"]:
        return {"ok": True, "already_requested": True, "request_id": existing["request_id"], "number": existing["number"]}
    cif = text(body.get("cif"))
    row = Callback(market=market, cif=cif, caller_phone=caller, callback_number=number, reason=text(body.get("reason"))[:200])
    db.add(row)
    db.flush()
    row.reference = reference("CB", row.id)
    record(db, "callback_requested", market, id=row.reference, caller=row.caller_phone, number=number, status="open", reason=row.reason)
    return {"ok": True, "request_id": row.reference, "number": number}


def take_survey(db: Session, market: Market, body: dict) -> dict:
    scores = []
    for key in ("q1", "q2", "q3"):
        try:
            score = float(body.get(key))
        except (TypeError, ValueError):
            score = math.nan
        scores.append(score)
    if any(not (1 <= s <= 5) or not s.is_integer() for s in scores):
        return {"ok": False, "reason": "scores_must_be_1_to_5"}
    q1, q2, q3 = (int(s) for s in scores)
    profile = text(body.get("profile")) or "ivr"
    db.add(Survey(market=market, profile=profile, q1=q1, q2=q2, q3=q3))
    record(db, "survey", market, profile=profile, q1=q1, q2=q2, q3=q3)
    return {"ok": True}


def send_fax(db: Session, market: Market, body: dict) -> dict:
    number = re.sub(r"\D", "", text(body.get("fax_number")))
    if len(number) < policy.number_setting(db, "fax_number_min_digits", market):
        return {"ok": False, "reason": "fax_number_too_short"}
    document = text(body.get("document_id") or body.get("title"))
    row = FaxJob(fax_number=number, document=document)
    db.add(row)
    db.flush()
    row.reference = reference("FX", row.id)
    record(db, "fax_sent", market, to=number, document=document, reference=row.reference)
    return {"ok": True, "job_id": row.reference}
