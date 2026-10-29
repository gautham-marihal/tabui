"""Singapore Siebel: logging in by account number, checking the contact's NRIC, service requests, and open cases."""

import re

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import AccountStatus, DocumentType, IdentityDocument, Investigation, Market, Person, Relationship, ServiceRequest
from . import lookups, policy
from .common import day, json_body, record, reference, text

router = APIRouter(prefix="/sg/siebel", tags=["Singapore: Siebel"])
SG = Market.SG


@router.post("/account-login")
def account_login(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """A full account number: whose it is, or why not (invalidAcct; a dormant or frozen account says so)."""
    number = text(body.get("account"))
    digits = policy.identity(db, SG).account_number_digits
    account = lookups.account(db, SG, number) if re.fullmatch(rf"\d{{{digits}}}", number) else None
    if not account or account.status is AccountStatus.CLOSED:
        return {"found": False, "invalidAcct": "Y"}
    owner = account.customer
    return {
        "found": True,
        "cif": owner.cif,
        "name": owner.name,
        "dormant": account.status is AccountStatus.DORMANT,
        "status": account.status.value,
        "access_level": owner.access_level.value if owner.access_level else None,
        "user_type": owner.customer_type.value,
    }


@router.post("/verify-contact")
def verify_contact(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """The last four characters of the caller's NRIC, checked against the people who act for the customer (its
    directors and signatories, or its owners). Letters in any case."""
    owner = lookups.customer(db, SG, text(body.get("cif")))
    given = text(body.get("nric_last4")).upper()
    match = (
        db.scalar(
            select(Person)
            .join(Relationship, Relationship.person_id == Person.id)
            .join(IdentityDocument, IdentityDocument.person_id == Person.id)
            .where(Relationship.customer_id == owner.id, IdentityDocument.document_type == DocumentType.NRIC, func.upper(IdentityDocument.last4) == given)
        )
        if owner and given
        else None
    )
    return {"valid": True, "person": match.person_ref, "name": match.salutation} if match else {"valid": False, "invalidContact": "Y"}


@router.post("/service-requests")
def raise_service_request(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    fields = {key: text(body.get(key)) for key in ("cif", "account", "type", "category", "subcategory", "notes")}
    row = ServiceRequest(
        cif=fields["cif"],
        account_number=fields["account"][-4:],
        request_type=fields["type"],
        category=fields["category"],
        subcategory=fields["subcategory"],
        notes=fields["notes"][:500],
    )
    db.add(row)
    db.flush()
    row.sr_number = reference("SR", row.id, digits=7)
    record(db, "service_request", SG, sr=row.sr_number, **{k: v for k, v in fields.items() if k in body})
    return {"ok": True, "sr_number": row.sr_number}


@router.get("/accounts/{number}/investigation")
def investigation(number: str, db: Session = Depends(get_session)):
    account = lookups.account(db, SG, number)
    case = db.scalar(select(Investigation).where(Investigation.account_id == account.id)) if account else None
    if not case:
        return {"found": False, "account_found": bool(account)}
    manager = case.service_manager
    return {
        "found": True,
        "case_id": case.case_reference,
        "topic": case.topic,
        "opened_on": day(case.opened_on),
        "last_service_manager": {"id": manager.code, "name": manager.name, "group": manager.team, "available": manager.available},
        # the same, flat, for callers that read top-level fields only
        "service_manager_id": manager.code,
        "service_manager_name": manager.name,
    }
