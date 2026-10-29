"""Finding people, customers and accounts, by what a caller gives: a login code, an ID number, a CIF, an account
number, the last four digits."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Account,
    AccountHolder,
    AccountStatus,
    Credential,
    CredentialKind,
    Customer,
    CustomerType,
    DocumentType,
    IdentifierKind,
    IdentityDocument,
    LoginIdentifier,
    Market,
    Person,
    Relationship,
    RelationshipRole,
    Transaction,
)
from ..security import fingerprint
from .common import day, last4, money


def customer(db: Session, market: Market, cif: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.market == market, Customer.cif == cif))


def account(db: Session, market: Market | None, number: str, *, for_update: bool = False) -> Account | None:
    """An account by its full number, in one country (or either, with no market)."""
    query = select(Account).where(Account.account_number == str(number or ""))
    if market is not None:
        query = query.where(Account.market == market)
    # a balance about to change is locked until the transaction ends, so two calls cannot spend the same money
    return db.scalar(query.with_for_update(of=Account) if for_update else query)


def by_login_code(db: Session, market: Market, kind: IdentifierKind, code: str) -> Person | None:
    """The person a phone code or key code was issued to, on that country's lines."""
    return db.scalar(
        select(Person)
        .join(LoginIdentifier)
        .where(LoginIdentifier.market == market, LoginIdentifier.kind == kind, LoginIdentifier.fingerprint == fingerprint(code))
    )


def by_id_number(db: Session, document: DocumentType, number: str) -> Person | None:
    return db.scalar(
        select(Person).join(IdentityDocument).where(IdentityDocument.document_type == document, IdentityDocument.fingerprint == fingerprint(number))
    )


def credential(db: Session, person: Person, kind: CredentialKind) -> Credential | None:
    """The person's PIN or TPIN, locked for the rest of the transaction (a wrong try is counted once)."""
    return db.scalar(select(Credential).where(Credential.person_id == person.id, Credential.kind == kind).with_for_update())


# the business lines serve the companies a person acts for first; anyone else is served as themselves
_ROLE_ORDER = {RelationshipRole.DIRECTOR: 0, RelationshipRole.SIGNATORY: 1, RelationshipRole.OWNER: 2}


def line_customer(db: Session, person: Person, market: Market, types: tuple[CustomerType, ...]) -> Customer | None:
    """The customer record a person is served as on a line: of that country, of the kinds the line serves; their own
    banking before one they share with someone."""
    rows = db.execute(
        select(Customer, Relationship.role)
        .join(Relationship, Relationship.customer_id == Customer.id)
        .where(Relationship.person_id == person.id, Customer.market == market, Customer.customer_type.in_(types))
        .order_by(Customer.id)
    ).all()
    rows.sort(key=lambda row: (types.index(row[0].customer_type), _ROLE_ORDER[row[1]], len(row[0].relationships)))
    return rows[0][0] if rows else None


def people_of(db: Session, owner: Customer) -> list[tuple[Person, RelationshipRole]]:
    """The people linked to a customer, and how (the director of a company, the owner of their own banking)."""
    return list(db.execute(select(Person, Relationship.role).join(Relationship).where(Relationship.customer_id == owner.id).order_by(Relationship.id)).all())


def holdings_of(db: Session, person: Person) -> list[AccountHolder]:
    """Every account a person may use or ask about, in both countries: theirs, joint ones, and the companies' they sign
    for. A dormant account is listed (it can be asked about); a closed one is not."""
    return list(
        db.scalars(
            select(AccountHolder)
            .join(Account)
            .where(AccountHolder.person_id == person.id, Account.status != AccountStatus.CLOSED)
            .order_by(Account.market, Account.customer_id, Account.id)
        )
    )


def accounts_of(db: Session, owner: Customer) -> list[Account]:
    return list(db.scalars(select(Account).where(Account.customer_id == owner.id, Account.status != AccountStatus.CLOSED).order_by(Account.id)))


def account_summary(row: Account, extra: tuple[str, ...] = ()) -> dict:
    """An account as the systems list it. A flag is named only when it is set (an ACU account says acu: true)."""
    summary = {
        "number": row.account_number,
        "last4": last4(row.account_number),
        "type": row.product_name,
        "category": row.product.category.value,
        "currency": row.currency,
        "cheques": row.cheques_enabled,
        "status": row.status.value,
    }
    flags = {"acu": row.is_acu, "dormant": row.status is AccountStatus.DORMANT, "islamic": row.is_islamic}
    summary.update({name: True for name in extra if flags[name]})
    return summary


def find_by_last4(db: Session, market: Market, cif: str, digits: str) -> dict:
    """One of the customer's accounts by the last digits the caller said or keyed. Digits that fit two accounts are
    ambiguous: the caller is asked for more."""
    owner = customer(db, market, cif)
    wanted = "".join(ch for ch in str(digits or "") if ch.isdigit())
    matches = [a for a in accounts_of(db, owner) if a.account_number.endswith(wanted)] if owner and len(wanted) >= 3 else []
    if len(matches) != 1:
        return {"found": False, "reason": "ambiguous" if matches else "not_found"}
    return {"found": True, **account_summary(matches[0])}


def history(db: Session, account_id: int, limit: int) -> list[dict]:
    """The account's latest postings, newest first, each with the balance it left."""
    rows = db.scalars(
        select(Transaction).where(Transaction.account_id == account_id).order_by(Transaction.posted_on.desc(), Transaction.id.desc()).limit(limit)
    )
    return [{"date": day(t.posted_on), "description": t.description, "amount": money(t.amount), "balance": money(t.balance_after)} for t in rows]
