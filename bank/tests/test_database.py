"""The database itself: its structure matches the models, confidential values are never readable, and every change is
written to the audit log."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from conftest import call
from sqlalchemy import text

from bank.db import Base, engine
from bank.security import fingerprint, hash_secret, verify_secret

# every login code, PIN, TPIN and full ID number in the seed data
CONFIDENTIAL = [
    # phone codes and key codes
    "1234567",
    "55667788",
    "3355779",
    "7654321",
    "4433221",
    "2468024",
    "1111111",
    "5577991",
    "6644220",
    "9988776",
    "12345678",
    "22446688",
    "87654321",
    "11112222",
    "33557799",
    "44668800",
    # PINs and TPINs
    "246810",
    "135246",
    "224466",
    "135790",
    "556677",
    "112233",
    "111111",
    "778899",
    "445566",
    "998877",
    "123456",
    "654321",
    "999999",
    "246802",
    # full IC numbers
    "750615105511",
    "880101145678",
    "820302085533",
    "950812146622",
]


def test_the_migrations_build_exactly_the_tables_the_models_describe():
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
    assert differences == []


def test_no_pin_code_or_id_number_is_stored_where_it_can_be_read(db):
    for table in Base.metadata.sorted_tables:
        for row in db.execute(table.select()).mappings():
            for column, value in row.items():
                assert str(value) not in CONFIDENTIAL, f"{table.name}.{column} holds a PIN, code or ID number as it is"
    hashes = db.execute(text("SELECT secret_hash FROM credentials")).scalars().all()
    assert hashes and all(h.startswith("scrypt$") for h in hashes)


def test_secrets_are_salted_hashes_and_codes_are_keyed_fingerprints():
    first, second = hash_secret("246810"), hash_secret("246810")
    assert first != second, "the same PIN never looks the same twice"
    assert verify_secret("246810", first) and not verify_secret("246811", first)
    assert fingerprint("321b") == fingerprint("321B"), "letters are compared without case"


def test_every_change_lands_in_the_audit_log_without_the_secret(client):
    call(client, "POST", "/sg/as400/pin", {"phone_code": "1234567", "old_pin": "246810", "new_pin": "135135"})
    assert call(client, "POST", "/sg/as400/login", {"phone_code": "1234567", "pin": "135135"})["ok"] is True, "the new PIN works"
    call(client, "POST", "/my/core/transfers/own", {"from_account": "7011223344", "to_account": "7011223355", "amount": 1})
    events = call(client, "GET", "/activity")["items"]
    assert [e["kind"] for e in events] == ["pin_changed"]
    assert "135135" not in str(events) and "246810" not in str(events)
