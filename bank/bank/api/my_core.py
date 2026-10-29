"""Malaysia core banking: key-code, phone-code and IC logins with a TPIN, and TPIN changes; accounts, transfers and
payments; direct debits; cheques; cards and card applications; rates, branches, forms and fax.

Anything done to an account or card names the person doing it (`person`): it must be theirs to use, active, and (for
money going out) an account money can be paid from. Payments go only to what the customer has: their loans and cards,
the bills and payees they registered."""

import re
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import (
    Account,
    AccountStatus,
    Bill,
    Card,
    CardAction,
    CardApplication,
    CardStatus,
    ChequeBookOrder,
    CredentialKind,
    CustomerType,
    DepositRate,
    DirectDebit,
    DocumentType,
    ExchangeRate,
    Form,
    IdentifierKind,
    LendingRate,
    Loan,
    MandateStatus,
    Market,
    OwnTransfer,
    Payee,
    Payment,
    PaymentKind,
    Person,
    ProductCategory,
    Relationship,
    StatementRequest,
)
from ..security import fingerprint, hash_secret, verify_secret
from . import cheques, lookups, policy
from .common import amount_of, branches_matching, day, json_body, last4, money, record, reference, send_fax, text

router = APIRouter(prefix="/my/core", tags=["Malaysia: core banking"])
MY = Market.MY


def _wrong_tpin(db: Session, credential, person: Person) -> dict:
    limit = policy.number_setting(db, "max_wrong_pins", MY)
    credential.failed_attempts += 1
    if credential.failed_attempts >= limit:
        credential.locked = True
        record(db, "tpin_locked", MY, person=person.person_ref)
        return {"ok": False, "reason": "locked"}
    return {"ok": False, "reason": "invalid_tpin", "tries_left": limit - credential.failed_attempts}


@router.post("/login")
def login(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Business Banking: key code, then TPIN. Consumer: phone code (or the 12-digit IC number), then TPIN."""
    by_key = "key_code" in body
    code = text(body.get("key_code") if by_key else body.get("phone_code"))
    if by_key:
        person = lookups.by_login_code(db, MY, IdentifierKind.KEY_CODE, code)
    else:
        person = lookups.by_login_code(db, MY, IdentifierKind.PHONE_CODE, code) or lookups.by_id_number(db, DocumentType.MYKAD, code)
    # a key code is for the companies a person acts for; a phone code or IC for their own (consumer) banking
    customer = lookups.line_customer(db, person, MY, (CustomerType.BUSINESS,) if by_key else (CustomerType.CONSUMER,)) if person else None
    credential = lookups.credential(db, person, CredentialKind.TPIN) if person and customer else None
    if not credential:
        return {"ok": False, "reason": "invalid_key_code" if by_key else "invalid_phone_code"}
    if credential.locked:
        return {"ok": False, "reason": "locked"}
    if "tpin" not in body:
        return {"ok": True, "code_valid": True}
    if not verify_secret(text(body["tpin"]), credential.secret_hash):
        return _wrong_tpin(db, credential, person)
    credential.failed_attempts = 0
    return {
        "ok": True,
        "cif": customer.cif,
        "line": customer.customer_type.value,
        "iq_member": customer.iq_member,
        "person": person.person_ref,
        "name": person.salutation,
    }


@router.post("/tpin")
def change_tpin(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """A new 6-digit TPIN for a logged-in person, given the current one (a wrong one counts towards the lock)."""
    person = policy.person_by_ref(db, text(body.get("person")))
    credential = lookups.credential(db, person, CredentialKind.TPIN) if person else None
    old, new = text(body.get("old_tpin")), text(body.get("new_tpin"))
    if not credential:
        return {"ok": False, "reason": "caller_not_verified"}
    if credential.locked:
        return {"ok": False, "reason": "locked"}
    if not verify_secret(old, credential.secret_hash):
        return _wrong_tpin(db, credential, person)
    if "confirm" in body and text(body.get("confirm")) != new:
        return {"ok": False, "reason": "tpins_do_not_match"}
    if not re.fullmatch(r"\d{6}", new):
        return {"ok": False, "reason": "new_tpin_must_be_6_digits"}
    if new == old:
        return {"ok": False, "reason": "same_as_old"}
    credential.secret_hash = hash_secret(new)
    credential.failed_attempts = 0
    record(db, "tpin_changed", MY, person=person.person_ref)
    return {"ok": True}


def _customer_ids(db: Session, person: Person) -> list[int]:
    """The customers a person acts for or owns: whose loans, cards, bills and payees they may use."""
    return list(db.scalars(select(Relationship.customer_id).where(Relationship.person_id == person.id)))


def _loan_answer(loan: Loan) -> dict:
    return {
        "id": loan.loan_number,
        "type": loan.product.name,
        "monthly": money(loan.monthly_instalment),
        "outstanding": money(loan.outstanding),
        "arrears": money(loan.arrears),
        "due": day(loan.next_due_on),
        "currency": loan.currency,
    }


def _card_answer(card: Card) -> dict:
    return {
        "last4": card.last4,
        "product": card.product.name,
        "kind": card.product.category.value,
        "status": card.status.value,
        "holder": card.holder.salutation,
    }


@router.get("/customers/{cif}")
def profile(cif: str, db: Session = Depends(get_session)):
    customer = lookups.customer(db, MY, cif)
    if not customer:
        return {"found": False}
    cards = db.scalars(select(Card).where(Card.customer_id == customer.id).order_by(Card.id))
    loans = db.scalars(select(Loan).where(Loan.customer_id == customer.id).order_by(Loan.id))
    bills = db.scalars(select(Bill).where(Bill.customer_id == customer.id).order_by(Bill.id))
    return {
        "found": True,
        "cif": customer.cif,
        "name": customer.name,
        "line": customer.customer_type.value,
        "iq_member": customer.iq_member,
        "accounts": [lookups.account_summary(a, ("islamic",)) for a in lookups.accounts_of(db, customer)],
        "cards": [_card_answer(c) for c in cards],
        "loans": [_loan_answer(loan) for loan in loans],
        "bills": [f"{b.biller.name} {b.biller_reference}" for b in bills],
    }


@router.get("/people/{ref}/payees")
def payees(ref: str, db: Session = Depends(get_session)):
    """Everything a person may pay from phone banking: their own loans and credit cards, the bills and the payees at
    other banks they registered."""
    person = policy.person_by_ref(db, ref)
    if not person:
        return {"found": False, "reason": "caller_not_verified"}
    ids = _customer_ids(db, person)
    loans = db.scalars(select(Loan).where(Loan.customer_id.in_(ids), Loan.outstanding > 0).order_by(Loan.id))
    cards = db.scalars(select(Card).where(Card.customer_id.in_(ids)).order_by(Card.id))
    bills = db.scalars(select(Bill).where(Bill.customer_id.in_(ids)).order_by(Bill.id))
    others = db.scalars(select(Payee).where(Payee.customer_id.in_(ids)).order_by(Payee.id))
    return {
        "found": True,
        "loans": [_loan_answer(loan) for loan in loans],
        "credit_cards": [
            {**_card_answer(c), "balance": money(c.outstanding_balance), "minimum_due": money(c.minimum_due), "due": day(c.due_on)}
            for c in cards
            if c.product.category is ProductCategory.CREDIT_CARD
        ],
        "bills": [{"bill": b.biller_reference, "biller": b.biller.name, "nickname": b.nickname} for b in bills],
        "payees": [{"payee": p.nickname, "name": p.name, "bank": p.bank_name, "account_last4": p.account_last4} for p in others],
    }


@router.get("/customers/{cif}/accounts/{digits}")
def account_by_last4(cif: str, digits: str, db: Session = Depends(get_session)):
    return lookups.find_by_last4(db, MY, cif, digits)


@router.get("/accounts/{number}/balance")
def balance(number: str, person: str = "", db: Session = Depends(get_session)):
    account = lookups.account(db, MY, number)
    refusal = policy.may_use(db, person, account, market=MY)
    if refusal:
        return {"found": False, **refusal}
    return {
        "found": True,
        "account_last4": last4(number),
        "type": account.product_name,
        "currency": account.currency,
        "balance": money(account.ledger_balance),
        "available_balance": money(account.available_balance),
    }


@router.get("/accounts/{number}/history")
def history(number: str, person: str = "", db: Session = Depends(get_session)):
    account = lookups.account(db, MY, number)
    refusal = policy.may_use(db, person, account, market=MY)
    if refusal:
        return {"items": [], **refusal}
    return {"items": lookups.history(db, account.id, policy.number_setting(db, "history_items", MY))}


@router.post("/accounts/{number}/statements")
def request_statement(number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person = text(body.get("person"))
    account = lookups.account(db, MY, number, for_update=True)
    refusal = policy.may_use(db, person, account, market=MY, transact=True)
    if refusal:
        return refusal
    price = policy.tariff(db, MY, "statement_mail")
    row = StatementRequest(market=MY, account_id=account.id, account_number=number, month=text(body.get("month")) or "latest", instructed_by=person)
    db.add(row)
    db.flush()
    row.reference = reference("MST", row.id)
    if price.fee:
        policy.post(db, account, -price.fee, f"Statement copy fee ({row.month})", row.reference)
    record(db, "statement_requested", MY, account=last4(number), month=row.month, reference=row.reference, by=person)
    today = policy.today(db, MY)
    return {
        "ok": True,
        "reference": row.reference,
        "month": row.month,
        "fee": money(price.fee),
        "currency": price.currency,
        "arrives_in_days": price.working_days,
        "arrives_by": day(policy.working_days_after(db, MY, today, price.working_days)),
    }


def _effective_on(db: Session) -> date:
    """Instructions given after the evening cut-off take effect on the next day."""
    now = policy.now(db, MY)
    cutoff = datetime.strptime(policy.setting(db, "payments_cutoff", MY), "%H:%M").time()
    return now.date() if now.time() < cutoff else policy.working_days_after(db, MY, now.date(), 1)


def _paying_account(db: Session, body: dict) -> tuple[Account | None, dict | None, Decimal | None]:
    """The account money leaves, locked, and the amount: or a refusal."""
    source = lookups.account(db, MY, text(body.get("from_account")), for_update=True)
    refusal = policy.may_use(db, text(body.get("person")), source, market=MY, spend=True)
    if refusal:
        return None, refusal, None
    amount = amount_of(body.get("amount"))
    if amount is None:
        return None, {"ok": False, "reason": "invalid_amount"}, None
    if amount > source.available_balance:
        return None, {"ok": False, "reason": "insufficient_funds", "available": money(source.available_balance), "currency": source.currency}, None
    return source, None, amount


@router.post("/transfers/own")
def own_transfer(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Between two accounts of the same customer, in one currency, never more than can be spent. The receiving account
    is its full number or its last four digits."""
    source, refusal, amount = _paying_account(db, body)
    if refusal:
        return refusal
    wanted = text(body.get("to_account") or body.get("to_last4"))
    targets = [a for a in lookups.accounts_of(db, source.customer) if a.id != source.id and a.account_number.endswith(wanted)] if len(wanted) >= 4 else []
    if len(targets) != 1:
        return {"ok": False, "reason": "ambiguous" if targets else "accounts_not_yours"}
    target = lookups.account(db, MY, targets[0].account_number, for_update=True)
    if target.status is not AccountStatus.ACTIVE or target.product.category is ProductCategory.FIXED_DEPOSIT:
        return {"ok": False, "reason": "cannot_pay_into_this_account", "type": target.product_name}
    if source.currency != target.currency:
        return {"ok": False, "reason": "different_currencies"}
    person = text(body.get("person"))
    transfer = OwnTransfer(from_account_id=source.id, to_account_id=target.id, currency=source.currency, amount=amount, instructed_by=person)
    db.add(transfer)
    db.flush()
    transfer.reference = reference("TRF", transfer.id)
    on = _effective_on(db)
    policy.post(db, source, -amount, f"Transfer to account ending {last4(target.account_number)}", transfer.reference, on)
    policy.post(db, target, amount, f"Transfer from account ending {last4(source.account_number)}", transfer.reference, on)
    record(db, "own_transfer", MY, ref=transfer.reference, **{"from": last4(source.account_number)}, to=last4(target.account_number), amount=amount, by=person)
    return {
        "ok": True,
        "reference": transfer.reference,
        "amount": money(amount),
        "currency": source.currency,
        "from_last4": last4(source.account_number),
        "to_last4": last4(target.account_number),
        "effective_on": day(on),
        "new_balance_from": money(source.ledger_balance),
    }


def _payment_target(db: Session, kind: PaymentKind, person: Person, body: dict):
    """What is being paid, among what the person may pay: (row, payee label, refusal)."""
    ids = _customer_ids(db, person)
    if kind is PaymentKind.LOAN:
        number = text(body.get("loan") or body.get("reference"))
        loan = db.scalar(select(Loan).where(Loan.customer_id.in_(ids), Loan.loan_number == number).with_for_update(of=Loan))
        return (loan, loan.loan_number, None) if loan else (None, "", {"ok": False, "reason": "not_one_of_their_loans"})
    if kind is PaymentKind.CREDIT_CARD:
        tail = text(body.get("card") or body.get("payee"))[-4:]
        card = db.scalar(select(Card).where(Card.customer_id.in_(ids), Card.last4 == tail).with_for_update(of=Card))
        if not card or card.product.category is not ProductCategory.CREDIT_CARD:
            return None, "", {"ok": False, "reason": "not_one_of_their_credit_cards"}
        return card, f"{card.product.name} ending {card.last4}", None
    if kind is PaymentKind.UTILITY:
        wanted = text(body.get("bill") or body.get("payee")).lower()
        bills = db.scalars(select(Bill).where(Bill.customer_id.in_(ids))).all()
        match = [b for b in bills if wanted and wanted in (b.biller_reference.lower(), b.nickname.lower(), b.biller.name.lower(), b.biller.code.lower())]
        if len(match) != 1:
            return None, "", {"ok": False, "reason": "ambiguous_bill" if match else "not_a_registered_bill"}
        return match[0], f"{match[0].biller.name} {match[0].biller_reference}", None
    wanted = text(body.get("payee")).lower()
    payee = next((p for p in db.scalars(select(Payee).where(Payee.customer_id.in_(ids))) if wanted in (p.nickname.lower(), p.name.lower())), None)
    if not payee:
        return None, "", {"ok": False, "reason": "not_a_registered_payee"}
    return payee, f"{payee.name} at {payee.bank_name} (account ending {payee.account_last4})", None


@router.post("/payments/{kind}")
def pay(kind: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Pays one of the person's loans or credit cards, a registered bill, or a registered payee at another bank."""
    if kind not in {k.value for k in PaymentKind}:
        return {"ok": False, "reason": "unknown_payment"}
    payment_kind = PaymentKind(kind)
    source, refusal, amount = _paying_account(db, body)
    if refusal:
        return refusal
    person = policy.person_by_ref(db, text(body.get("person")))
    target, label, refusal = _payment_target(db, payment_kind, person, body)
    if refusal:
        return refusal
    home = policy.identity(db, MY).base_currency
    if source.currency != home:
        return {"ok": False, "reason": "pay_from_a_local_currency_account", "currency": home}
    if isinstance(target, Loan):
        if amount > target.outstanding:
            return {"ok": False, "reason": "more_than_owed", "outstanding": money(target.outstanding)}
        _apply_loan_payment(db, target, amount)
    elif isinstance(target, Card):
        if amount > target.outstanding_balance:
            return {"ok": False, "reason": "more_than_owed", "outstanding": money(target.outstanding_balance)}
        target.outstanding_balance -= amount
        target.minimum_due = max(target.minimum_due - amount, Decimal("0"))
    payment = Payment(
        from_account_id=source.id,
        kind=payment_kind,
        payee=label,
        currency=source.currency,
        amount=amount,
        loan_id=target.id if isinstance(target, Loan) else None,
        card_id=target.id if isinstance(target, Card) else None,
        bill_id=target.id if isinstance(target, Bill) else None,
        payee_id=target.id if isinstance(target, Payee) else None,
        instructed_by=person.person_ref,
    )
    db.add(payment)
    db.flush()
    payment.reference = reference("PAY", payment.id)
    on = _effective_on(db)
    policy.post(db, source, -amount, f"{kind.replace('_', ' ').capitalize()} payment to {label}", payment.reference, on)
    record(db, f"payment_{kind}", MY, ref=payment.reference, **{"from": last4(source.account_number)}, to=label, amount=amount, by=person.person_ref)
    return {
        "ok": True,
        "reference": payment.reference,
        "paid_to": label,
        "amount": money(amount),
        "currency": source.currency,
        "effective_on": day(on),
        "new_balance": money(source.ledger_balance),
    }


def _apply_loan_payment(db: Session, loan: Loan, amount: Decimal) -> None:
    """Arrears are paid first; once this month's instalment is covered, the next one is due a month later."""
    to_arrears = min(amount, loan.arrears)
    loan.arrears -= to_arrears
    loan.outstanding -= amount
    if amount - to_arrears >= loan.monthly_instalment:
        month = loan.next_due_on.month % 12 + 1
        year = loan.next_due_on.year + (loan.next_due_on.month == 12)
        loan.next_due_on = loan.next_due_on.replace(year=year, month=month)


@router.get("/fpx/{cif}")
def direct_debits(cif: str, db: Session = Depends(get_session)):
    customer = lookups.customer(db, MY, cif)
    rows = db.scalars(select(DirectDebit).where(DirectDebit.customer_id == customer.id).order_by(DirectDebit.id)) if customer else []
    return {"items": [{"id": d.mandate_reference, "merchant": d.merchant, "amount": money(d.amount), "status": d.status.value} for d in rows]}


@router.post("/fpx/{cif}/{mandate}/terminate")
def end_direct_debit(cif: str, mandate: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    customer = lookups.customer(db, MY, cif)
    person = policy.person_by_ref(db, text(body.get("person")))
    if not customer or not person or customer.id not in _customer_ids(db, person):
        return {"ok": False, "reason": "no_such_direct_debit"}
    row = db.scalar(select(DirectDebit).where(DirectDebit.customer_id == customer.id, DirectDebit.mandate_reference == mandate).with_for_update())
    if not row:
        return {"ok": False, "reason": "no_such_direct_debit"}
    if row.status is MandateStatus.TERMINATED:
        return {"ok": False, "reason": "already_terminated"}
    row.status = MandateStatus.TERMINATED
    record(db, "fpx_terminated", MY, cif=cif, id=mandate, by=person.person_ref)
    return {"ok": True, "id": mandate, "merchant": row.merchant}


@router.get("/cheques/{number}/{cheque_no}")
def cheque_status(number: str, cheque_no: str, person: str = "", db: Session = Depends(get_session)):
    return cheques.status(db, MY, number, cheque_no, person)


@router.post("/cheques/{number}/stop")
def stop_payment(number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return cheques.stop(db, MY, number, body, "MSTP")


@router.post("/accounts/{number}/cheque-book")
def order_cheque_book(number: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    person = text(body.get("person"))
    account = lookups.account(db, MY, number, for_update=True)
    refusal = policy.may_use(db, person, account, market=MY, transact=True)
    if refusal:
        return refusal
    if not account.cheques_enabled:
        return {"ok": False, "reason": "account_has_no_cheques"}
    price = policy.tariff(db, MY, "cheque_book_normal")
    row = ChequeBookOrder(
        market=MY, account_number=number, account_id=account.id, fee=price.fee, ready_in_working_days=price.working_days, instructed_by=person
    )
    db.add(row)
    db.flush()
    row.reference = reference("MCB", row.id)
    if price.fee:
        policy.post(db, account, -price.fee, "Cheque book fee", row.reference)
    record(db, "cheque_book_requested", MY, account=last4(number), reference=row.reference, by=person)
    return {
        "ok": True,
        "reference": row.reference,
        "fee": money(price.fee),
        "currency": price.currency,
        "ready_in_working_days": price.working_days,
        "ready_by": day(policy.working_days_after(db, MY, policy.today(db, MY), price.working_days)),
    }


def _card(db: Session, cif: str, digits: str, person_ref: str, *, for_update: bool = False) -> tuple[Card | None, dict | None]:
    """One of the customer's cards, for a person who holds it or acts for the customer."""
    customer = lookups.customer(db, MY, cif)
    person = policy.person_by_ref(db, person_ref)
    if not person:
        return None, {"ok": False, "found": False, "reason": "caller_not_verified"}
    query = select(Card).where(Card.customer_id == (customer.id if customer else -1), Card.last4 == str(digits)[-4:])
    card = db.scalar(query.with_for_update(of=Card) if for_update else query)
    if not card or (card.holder_id != person.id and card.customer_id not in _customer_ids(db, person)):
        return None, {"ok": False, "found": False, "reason": "not_one_of_their_cards"}
    return card, None


@router.get("/customers/{cif}/cards/{digits}")
def card(cif: str, digits: str, person: str = "", db: Session = Depends(get_session)):
    row, refusal = _card(db, cif, digits, person)
    if refusal:
        return refusal
    credit = row.product.category is ProductCategory.CREDIT_CARD
    today = policy.today(db, MY)
    fee_due = Decimal("0") if row.fee_waived_until and row.fee_waived_until >= today else row.product.annual_fee
    return {
        "found": True,
        **_card_answer(row),
        "expires": row.expires_on.strftime("%m/%y"),
        "block_reason": row.block_reason or None,
        **(
            {
                "limit": money(row.credit_limit),
                "balance": money(row.outstanding_balance),
                "available_credit": money(row.available_credit),
                "minimum_due": money(row.minimum_due),
                "due": day(row.due_on),
                "annual_fee": money(fee_due),
                "fee_waived_until": day(row.fee_waived_until),
            }
            if credit
            else {"linked_account_last4": last4(row.account.account_number) if row.account else None}
        ),
    }


@router.post("/customers/{cif}/cards/{digits}/{action}")
def card_action(cif: str, digits: str, action: str, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    """Activate a card, block a lost or stolen one, waive this year's annual fee, change the credit limit (an increase is
    reviewed), or move a balance from another bank's card onto it (processed in the price list's working days)."""
    person = text(body.get("person"))
    row, refusal = _card(db, cif, digits, person, for_update=True)
    if refusal:
        return refusal
    credit = row.product.category is ProductCategory.CREDIT_CARD
    today = policy.today(db, MY)
    details = {key: body[key] for key in ("new_limit", "amount", "from_bank", "reason") if key in body}
    outcome, answer = "done", {}
    if action == "activate":
        if row.status is not CardStatus.INACTIVE:
            return {"ok": False, "reason": "already_active" if row.status is CardStatus.ACTIVE else f"card_{row.status.value}"}
        row.status = CardStatus.ACTIVE
    elif action == "block":
        if row.status is CardStatus.BLOCKED:
            return {"ok": False, "reason": "already_blocked"}
        row.status, row.block_reason = CardStatus.BLOCKED, text(body.get("reason")) or "reported lost"
        price = policy.tariff(db, MY, "card_replacement")
        answer = {"replacement_in_working_days": price.working_days, "replacement_fee": money(price.fee), "currency": price.currency}
    elif not credit:
        return {"ok": False, "reason": "only_for_credit_cards"}
    elif action == "fee-waiver":
        if not row.product.annual_fee:
            return {"ok": False, "reason": "no_fee_to_waive"}
        if row.fee_waived_until and row.fee_waived_until >= today:
            return {"ok": False, "reason": "already_waived", "until": day(row.fee_waived_until)}
        row.fee_waived_until = today.replace(year=today.year + 1)
        answer = {"waived": money(row.product.annual_fee), "until": day(row.fee_waived_until)}
    elif action == "credit-limit":
        wanted = amount_of(body.get("new_limit"))
        if wanted is None:
            return {"ok": False, "reason": "invalid_limit"}
        if wanted < row.outstanding_balance:
            return {"ok": False, "reason": "below_the_balance_owed", "balance": money(row.outstanding_balance)}
        if wanted > row.credit_limit:
            outcome = "review"
            answer = {"decision_in_working_days": policy.tariff(db, MY, "credit_limit_review").working_days}
        else:
            row.credit_limit = wanted
    elif action == "balance-transfer":
        amount = amount_of(body.get("amount"))
        if amount is None:
            return {"ok": False, "reason": "invalid_amount"}
        if amount > row.available_credit:
            return {"ok": False, "reason": "more_than_available_credit", "available_credit": money(row.available_credit)}
        price = policy.tariff(db, MY, "balance_transfer")
        outcome = "submitted"
        answer = {"amount": money(amount), "processed_in_working_days": price.working_days, "fee": money(price.fee), "currency": price.currency}
    else:
        return {"ok": False, "reason": "unknown_action"}
    entry = CardAction(card_id=row.id, action=action, outcome=outcome, details=details, instructed_by=person)
    db.add(entry)
    db.flush()
    entry.reference = reference("CRD", entry.id)
    record(db, f"card_{action}", MY, card=row.last4, outcome=outcome, reference=entry.reference, by=person, **details)
    return {"ok": True, "reference": entry.reference, "outcome": outcome, "status": row.status.value, "limit": money(row.credit_limit), **answer}


@router.get("/card-applications/{id_number}")
def card_application(id_number: str, db: Session = Depends(get_session)):
    row = db.scalar(select(CardApplication).where(CardApplication.id_fingerprint == fingerprint(id_number)).order_by(CardApplication.id.desc()))
    if not row:
        return {"found": False}
    return {"found": True, "status": row.status.value, "card": row.product.name, "applied_on": day(row.applied_on), "sent_on": day(row.sent_on)}


@router.get("/rates")
def rates(db: Session = Depends(get_session)):
    home = policy.identity(db, MY).base_currency
    lending = list(db.scalars(select(LendingRate).where(LendingRate.market == MY).order_by(LendingRate.id)))
    deposits = list(db.scalars(select(DepositRate).where(DepositRate.market == MY).order_by(DepositRate.currency.desc(), DepositRate.tenor_months)))
    fx = db.scalars(select(ExchangeRate).where(ExchangeRate.market == MY).order_by(ExchangeRate.id))
    return {
        **{r.name: money(r.rate_pct) for r in lending},
        "lending": [{"name": r.name, "label": r.label, "rate": money(r.rate_pct)} for r in lending],
        "currency": home,
        "fd": [{"tenor_months": d.tenor_months, "rate": money(d.rate_pct)} for d in deposits if d.currency == home],
        "fcy_fd": [{"currency": d.currency, "tenor_months": d.tenor_months, "rate": money(d.rate_pct)} for d in deposits if d.currency != home],
        "fx": {r.currency: {"buy": float(r.bank_buys), "sell": float(r.bank_sells)} for r in fx},
    }


@router.get("/branches")
def branches(q: str = "", db: Session = Depends(get_session)):
    return {"items": branches_matching(db, MY, q)}


@router.get("/forms")
def forms(db: Session = Depends(get_session)):
    rows = db.scalars(select(Form).where(Form.market == MY, Form.by_fax.is_(True)).order_by(Form.id))
    return {"items": [{"id": f.code, "title": f.title, "purpose": f.purpose} for f in rows]}


@router.post("/fax")
def fax(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return send_fax(db, MY, body)
