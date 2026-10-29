"""The starting data holds together the way a bank's does: every balance is its postings, every movement is on the
accounts it touches, each fact is in one place, and the rules the systems apply come from the bank's own tables."""

from decimal import Decimal

from conftest import call
from sqlalchemy import func, select

from bank.models import (
    Account,
    AccountHolder,
    AccountStatus,
    Card,
    ChequeBook,
    ChequeDeposit,
    ChequeStatus,
    Customer,
    FixedDeposit,
    IncomingFund,
    IncomingFundStatus,
    IssuedCheque,
    Loan,
    Person,
    Relationship,
    Setting,
    Tariff,
    Transaction,
)


def test_every_balance_is_the_sum_of_its_postings_and_each_posting_keeps_the_balance_it_left(db):
    for account in db.scalars(select(Account)):
        postings = list(db.scalars(select(Transaction).where(Transaction.account_id == account.id).order_by(Transaction.posted_on, Transaction.id)))
        assert postings, f"{account.account_number} has no postings"
        assert sum((t.amount for t in postings), Decimal("0")) == account.ledger_balance, account.account_number
        running = Decimal("0")
        for t in postings:
            running += t.amount
            assert t.balance_after == running, f"{account.account_number} {t.posted_on} {t.description}"
            assert running >= 0, f"{account.account_number} is overdrawn on {t.posted_on}"


def test_what_happened_to_money_is_on_the_accounts_it_touched(db):
    def posted(account_id, words):
        return db.scalar(select(func.count(Transaction.id)).where(Transaction.account_id == account_id, Transaction.description.contains(words)))

    for cheque in db.scalars(select(IssuedCheque).where(IssuedCheque.status == ChequeStatus.PAID)):
        assert posted(cheque.account_id, f"Cheque {cheque.cheque_no} cleared"), cheque.cheque_no
    for deposit in db.scalars(select(ChequeDeposit)):
        assert posted(deposit.account_id, f"Cheque deposit {deposit.cheque_no}"), deposit.cheque_no
    for fund in db.scalars(select(IncomingFund)):
        assert bool(posted(fund.account_id, fund.reference)) == (fund.status is IncomingFundStatus.CREDITED), fund.reference
    for cheque in db.scalars(select(IssuedCheque)):
        books = db.scalars(select(ChequeBook).where(ChequeBook.account_id == cheque.account_id)).all()
        assert any(b.first_cheque_no <= cheque.cheque_no <= b.last_cheque_no for b in books), f"cheque {cheque.cheque_no} is from no book"
    for loan in db.scalars(select(Loan)):
        assert posted(loan.repayment_account_id, f"instalment {loan.loan_number}"), loan.loan_number
        assert Decimal("0") < loan.outstanding <= loan.principal
    salary = db.scalar(select(func.count(Transaction.id)).where(Transaction.description == "PayNow from Lim & Co Logistics"))
    assert salary == 1, "a transfer inside the bank is on both accounts"


def test_a_dormant_account_has_been_quiet_and_a_fixed_deposit_is_its_terms(client, db):
    dormant = db.scalar(select(Account).where(Account.status == AccountStatus.DORMANT))
    latest = db.scalar(select(func.max(Transaction.posted_on)).where(Transaction.account_id == dormant.id))
    assert (call(client, "GET", "/hub/reference")["sg"]["today"] > latest.isoformat()) and (dormant.ledger_balance == Decimal("12.50"))
    for deposit in db.scalars(select(FixedDeposit)):
        account = db.get(Account, deposit.account_id)
        assert deposit.principal == account.ledger_balance and deposit.matures_on > deposit.placed_on


def test_each_fact_is_in_one_place(db):
    # who may use an account is exactly the people linked to its customer
    for account in db.scalars(select(Account)):
        holders = set(db.scalars(select(AccountHolder.person_id).where(AccountHolder.account_id == account.id)))
        linked = set(db.scalars(select(Relationship.person_id).where(Relationship.customer_id == account.customer_id)))
        assert holders == linked, account.account_number
    # every card is held by someone linked to its customer, and a debit card draws on that customer's account
    for card in db.scalars(select(Card)):
        linked = set(db.scalars(select(Relationship.person_id).where(Relationship.customer_id == card.customer_id)))
        assert card.holder_id in linked, card.last4
        if card.account_id:
            assert db.get(Account, card.account_id).customer_id == card.customer_id, card.last4
    # every person can log in somewhere, and every customer has someone behind it
    for person in db.scalars(select(Person)):
        assert person.identifiers and person.credentials, person.person_ref
    for customer in db.scalars(select(Customer)):
        assert customer.contact, customer.cif


def test_the_rules_come_from_the_bank_s_own_tables(client, db):
    # change a setting and a tariff in the database, and the systems follow
    db.scalar(select(Setting).where(Setting.name == "slots_offered")).value = "2"
    db.scalar(select(Tariff).where(Tariff.code == "cheque_book_express")).fee = Decimal("25")
    db.commit()
    assert len(call(client, "GET", "/sg/cmm/appointments/slots?type=foreign_worker")["items"]) == 2
    book = call(client, "POST", "/sg/soa/accounts/501234567001/cheque-book", {"delivery": "express", "person": "P001"})
    assert book["fee"] == 25.0


def test_the_reference_the_agents_are_built_from(client):
    reference = call(client, "GET", "/hub/reference")
    sg, my = reference["sg"], reference["my"]
    assert (sg["country"], sg["currency"], sg["timezone"]) == ("Singapore", "SGD", "Asia/Singapore")
    assert sg["lines"]["business_line"]["number"] == "6538 1111"
    assert sg["lines"]["service_centre"]["hours"] == [{"days": ["mon", "tue", "wed", "thu", "fri"], "start": "08:30", "end": "18:00"}]
    assert sg["tariffs"]["stop_cheque"] == {"label": "Stop payment of a cheque", "fee": 30.0, "currency": "SGD", "working_days": 0}
    assert my["tariffs"]["stop_cheque"]["fee"] == 10.0 and my["settings"]["payments_cutoff"] == "20:00"
    assert all(h["date"] >= sg["today"] for h in sg["holidays"]), "holidays from today on"
    assert reference["service_codes"][0]["code"] == "328"
