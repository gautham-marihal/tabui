"""Cheques written by customers, shared by the Singapore (AS400) and Malaysia core systems: status and stop-payment.
A stop order is for a cheque from one of the account's own cheque books, not yet paid and not already stopped; its fee
(from the price list) is taken from the account."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Account, ChequeBook, ChequeStatus, IssuedCheque, Market, StopPayment
from . import lookups, policy
from .common import compact, day, money, record, reference


def find(db: Session, market: Market, account_number: str, cheque_no: str, *, for_update: bool = False) -> IssuedCheque | None:
    query = select(IssuedCheque).where(IssuedCheque.market == market, IssuedCheque.account_number == account_number, IssuedCheque.cheque_no == cheque_no)
    return db.scalar(query.with_for_update() if for_update else query)


def status(db: Session, market: Market, account_number: str, cheque_no: str, person_ref: str) -> dict:
    refusal = policy.may_use(db, person_ref, lookups.account(db, market, account_number), market=market)
    if refusal:
        return {"found": False, **refusal}
    row = find(db, market, account_number, cheque_no)
    if not row:
        return {"found": False, "cheque_no": cheque_no}
    return compact(
        {
            "found": True,
            "cheque_no": cheque_no,
            "status": row.status.value,
            "amount": money(row.amount),
            "paid_on": day(row.paid_on),
            "stopped_on": day(row.stopped_on),
        }
    )


def _in_a_cheque_book(db: Session, account: Account, cheque_no: str) -> bool:
    books = db.scalars(select(ChequeBook).where(ChequeBook.account_id == account.id))
    return cheque_no.isdigit() and any(b.first_cheque_no <= cheque_no.zfill(len(b.first_cheque_no)) <= b.last_cheque_no for b in books)


def stop(db: Session, market: Market, account_number: str, body: dict, prefix: str) -> dict:
    """Stops a cheque that has not been paid, and charges the stop fee to the account."""
    cheque_no, reason, person_ref = (str(body.get(k) or "").strip() for k in ("cheque_no", "reason", "person"))
    account = lookups.account(db, market, account_number, for_update=True)
    refusal = policy.may_use(db, person_ref, account, market=market, transact=True)
    if refusal:
        return refusal
    if not account.cheques_enabled:
        return {"ok": False, "reason": "account_has_no_cheques"}
    if not cheque_no:
        return {"ok": False, "reason": "cheque_no_required"}
    cheque = find(db, market, account_number, cheque_no, for_update=True)
    if cheque and cheque.status is ChequeStatus.PAID:
        return {"ok": False, "reason": "already_paid", "paid_on": day(cheque.paid_on), "amount": money(cheque.amount)}
    if cheque and cheque.status is ChequeStatus.STOPPED:
        return {"ok": False, "reason": "already_stopped", "stopped_on": day(cheque.stopped_on)}
    if not cheque and not _in_a_cheque_book(db, account, cheque_no):
        return {"ok": False, "reason": "not_from_this_accounts_cheque_books"}
    price = policy.tariff(db, market, "stop_cheque")
    if account.available_balance < price.fee:
        return {"ok": False, "reason": "insufficient_funds_for_fee", "fee": money(price.fee), "currency": price.currency}
    if not cheque:
        # a cheque the bank has not seen yet (not presented): stopped before it arrives
        cheque = IssuedCheque(market=market, account_number=account_number, account_id=account.id, cheque_no=cheque_no)
        db.add(cheque)
    cheque.status = ChequeStatus.STOPPED
    cheque.stopped_on = policy.today(db, market)
    order = StopPayment(cheque=cheque, reason=reason, fee=price.fee, fee_currency=price.currency, instructed_by=person_ref)
    db.add(order)
    db.flush()
    order.reference = reference(prefix, order.id)
    if price.fee:
        policy.post(db, account, -price.fee, f"Stop payment fee, cheque {cheque_no}", order.reference)
    record(db, "cheque_stopped", market, account=account.account_number[-4:], cheque_no=cheque_no, reason=reason, reference=order.reference, by=person_ref)
    return {"ok": True, "cheque_no": cheque_no, "fee": money(price.fee), "currency": price.currency, "reference": order.reference}
