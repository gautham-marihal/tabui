"""Singapore CMM (the contact centre's own tables): caller preferences, VIPs, service codes, promotions, forms, branches,
the bank's codes, appointments, call-backs, surveys and registered calls."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import AppointmentSlot, Booking, CallRegistration, Customer, Form, Market, Person, Promotion, ServiceCode, Vip
from . import lookups, policy
from .common import (
    branches_matching,
    clock,
    day,
    json_body,
    last4,
    open_callback,
    record,
    reference,
    request_callback,
    take_survey,
    text,
)

router = APIRouter(prefix="/sg/cmm", tags=["Singapore: CMM"])
SG = Market.SG


def _manager(m) -> dict:
    return {"id": m.code, "name": m.name, "group": m.team, "available": m.available}


def _caller(db: Session, phone: str) -> Person | None:
    return db.scalar(select(Person).where(Person.mobile == policy.normalise_phone(db, phone, SG)))


@router.get("/callers/{phone}")
def caller(phone: str, db: Session = Depends(get_session)):
    person = _caller(db, phone)
    if not person:
        return {"found": False, "language": "", "favourite_txn": "", "is_vip": False}
    is_vip = bool(db.scalar(select(Vip.id).where(Vip.person_id == person.id)))
    return {"found": True, "language": person.language, "favourite_txn": person.favourite_transaction, "is_vip": is_vip}


def _vip(db: Session, phone: str) -> Vip | None:
    person = _caller(db, phone)
    return db.scalar(select(Vip).where(Vip.person_id == person.id)) if person else None


@router.get("/vip/{phone}")
def vip(phone: str, db: Session = Depends(get_session)):
    """A VIP by their mobile: how to greet and check them, and their service manager."""
    row = _vip(db, phone)
    if not row:
        return {"found": False}
    return {
        "found": True,
        "name": row.person.salutation,
        "person": row.person.person_ref,
        "vip_type": row.vip_check.value,
        "language": row.person.language,
        "cif": row.customer.cif if row.customer else "",
        "account_last4": last4(row.account.account_number) if row.account else "",
        "last_service_manager": _manager(row.service_manager),
        # the same, flat, for callers that read top-level fields only
        "service_manager_id": row.service_manager.code,
        "service_manager_name": row.service_manager.name,
    }


@router.post("/vip/{phone}/check-account")
def vip_check_account(phone: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    row = _vip(db, phone)
    return {"valid": bool(row and row.account and row.account.account_number == text(body.get("account")))}


@router.get("/service-codes/{code}")
def service_code(code: str, db: Session = Depends(get_session)):
    row = db.scalar(select(ServiceCode).where(ServiceCode.code == code))
    return {"valid": True, "code": code, "route": row.route, "label": row.label} if row else {"valid": False, "code": code}


@router.get("/promotions")
def promotions(db: Session = Depends(get_session)):
    """The promotions running today."""
    today = policy.today(db, SG)
    rows = db.scalars(
        select(Promotion)
        .where(Promotion.market == SG, Promotion.valid_until >= today, (Promotion.valid_from.is_(None)) | (Promotion.valid_from <= today))
        .order_by(Promotion.id)
    )
    return {"items": [{"id": p.code, "title": p.title, "until": day(p.valid_until)} for p in rows]}


@router.get("/forms")
def forms(db: Session = Depends(get_session)):
    rows = db.scalars(select(Form).where(Form.market == SG, Form.by_fax.is_(True)).order_by(Form.id))
    return {"items": [{"id": f.code, "title": f.title, "purpose": f.purpose} for f in rows]}


@router.get("/branches")
def branches(q: str = "", db: Session = Depends(get_session)):
    return {"items": branches_matching(db, SG, q)}


@router.get("/bank-codes")
def bank_codes(db: Session = Depends(get_session)):
    row = policy.identity(db, SG)
    return {"bank": row.bank_name, "giro_bank_code": row.giro_bank_code, "swift": row.swift_bic, "branch_code_note": row.branch_code_note}


def slot_answer(slot: AppointmentSlot) -> dict:
    return {
        "slot_id": slot.code,
        "date": day(slot.slot_date),
        "time": clock(slot.slot_time),
        "branch_name": slot.branch.name,
        "branch_address": slot.branch.address,
    }


def booking_answer(booking: Booking) -> dict:
    return {"id": booking.reference, "cif": booking.cif, "type": booking.appointment_type, "contact_name": booking.contact_name, **slot_answer(booking.slot)}


def _upcoming(db: Session, slot: AppointmentSlot) -> bool:
    now = policy.now(db, SG)
    return datetime.combine(slot.slot_date, slot.slot_time, now.tzinfo) > now


@router.get("/appointments/slots")
def free_slots(type: str = "", db: Session = Depends(get_session)):  # noqa: A002  (the agents' query parameter is called type)
    """Free slots still ahead, soonest first, up to the number the agent offers at once."""
    rows = db.scalars(
        select(AppointmentSlot)
        .where(AppointmentSlot.appointment_type == type, AppointmentSlot.is_taken.is_(False), AppointmentSlot.slot_date >= policy.today(db, SG))
        .order_by(AppointmentSlot.slot_date, AppointmentSlot.slot_time)
    )
    upcoming = [s for s in rows if _upcoming(db, s)]
    return {"items": [slot_answer(s) for s in upcoming[: policy.number_setting(db, "slots_offered", SG)]]}


@router.post("/appointments")
def book(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    customer = lookups.customer(db, SG, text(body.get("cif")))
    if not customer:
        return {"ok": False, "reason": "unknown_customer"}
    slot = db.scalar(select(AppointmentSlot).where(AppointmentSlot.code == text(body.get("slot_id"))).with_for_update())
    if not slot or slot.is_taken or not _upcoming(db, slot):
        return {"ok": False, "reason": "slot_not_available"}
    wanted = text(body.get("type"))
    if wanted and wanted != slot.appointment_type:
        return {"ok": False, "reason": "slot_is_for_another_kind_of_appointment"}
    slot.is_taken = True
    booking = Booking(slot=slot, cif=customer.cif, appointment_type=slot.appointment_type, contact_name=text(body.get("contact_name")))
    db.add(booking)
    db.flush()
    booking.reference = reference("BK", booking.id)
    record(db, "appointment_booked", SG, **booking_answer(booking))
    return {
        "ok": True,
        "booking_id": booking.reference,
        "date": day(slot.slot_date),
        "time": clock(slot.slot_time),
        "branch": slot.branch.name,
        "address": slot.branch.address,
    }


@router.get("/appointments")
def bookings(cif: str = "", db: Session = Depends(get_session)):
    """One customer's bookings still ahead."""
    if not db.scalar(select(Customer.id).where(Customer.cif == cif)):
        return {"items": []}
    rows = db.scalars(select(Booking).where(Booking.cancelled.is_(False), Booking.cif == cif).order_by(Booking.id))
    return {"items": [booking_answer(b) for b in rows if _upcoming(db, b.slot)]}


@router.post("/appointments/{booking_ref}/cancel")
def cancel_booking(booking_ref: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Cancels one of the customer's own bookings; the slot is free again."""
    booking = db.scalar(select(Booking).where(Booking.reference == booking_ref, Booking.cancelled.is_(False)).with_for_update())
    if not booking or booking.cif != text(body.get("cif")):
        return {"ok": False, "reason": "no_such_booking"}
    booking.cancelled = True
    booking.slot.is_taken = False
    record(db, "appointment_cancelled", SG, id=booking.reference, cif=booking.cif)
    return {"ok": True, "booking_id": booking.reference}


@router.get("/callbacks/{phone}")
def callback_open(phone: str, db: Session = Depends(get_session)):
    return open_callback(db, SG, phone)


@router.post("/callbacks")
def callback(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return request_callback(db, SG, body)


@router.post("/surveys")
def survey(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return take_survey(db, SG, body)


@router.post("/calls/register")
def register_call(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    fields = {key: text(body.get(key)) for key in ("intent", "skillset", "cif")}
    db.add(CallRegistration(**fields))
    record(db, "call_registered", SG, **{k: v for k, v in fields.items() if k in body})
    return {"ok": True}
