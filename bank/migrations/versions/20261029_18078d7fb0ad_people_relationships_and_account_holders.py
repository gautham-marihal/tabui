"""People, the customers they bank as, and the accounts they may use.

Logins (phone codes, key codes), PINs and ID documents move from customer records to people: one person logs in once
and sees every account they hold, in both countries. Existing data is carried across: every customer someone logs in or
is identified as becomes a person linked to it (the owner of personal banking, the director of a company), with that
customer's accounts. Only then are the old links dropped.

Revision ID: 18078d7fb0ad
Revises: 1bbcfd60e7d7
Create Date: 2026-10-29 22:58:14.409930

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "18078d7fb0ad"
down_revision: str | Sequence[str] | None = "1bbcfd60e7d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED = ("credentials", "identity_documents", "login_identifiers")


def upgrade() -> None:
    # ---- the new tables
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_ref", sa.String(length=12), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("salutation", sa.String(length=60), nullable=False),
        sa.Column("mobile", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("language", sa.String(length=5), server_default="en", nullable=False),
        sa.Column("nationality", sa.String(length=2), nullable=False),
        sa.Column("otp_suspended", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_people")),
        sa.UniqueConstraint("mobile", name=op.f("uq_people_mobile")),
        sa.UniqueConstraint("person_ref", name=op.f("uq_people_person_ref")),
    )
    op.create_table(
        "relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("owner", "director", "signatory", name="relationship_role", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name=op.f("fk_relationships_customer_id_customers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], name=op.f("fk_relationships_person_id_people"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relationships")),
        sa.UniqueConstraint("person_id", "customer_id", name=op.f("uq_relationships_person_id_customer_id")),
    )
    op.create_index(op.f("ix_relationships_customer_id"), "relationships", ["customer_id"], unique=False)
    op.create_index(op.f("ix_relationships_person_id"), "relationships", ["person_id"], unique=False)
    op.create_table(
        "account_holders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("primary", "joint", "signatory", name="holder_role", native_enum=False, create_constraint=True), nullable=False),
        sa.Column("can_transact", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_account_holders_account_id_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], name=op.f("fk_account_holders_person_id_people"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_account_holders")),
        sa.UniqueConstraint("account_id", "person_id", name=op.f("uq_account_holders_account_id_person_id")),
    )
    op.create_index(op.f("ix_account_holders_account_id"), "account_holders", ["account_id"], unique=False)
    op.create_index(op.f("ix_account_holders_person_id"), "account_holders", ["person_id"], unique=False)

    # ---- the new links, empty for now
    for table in OWNED:
        op.add_column(table, sa.Column("person_id", sa.Integer(), nullable=True))
    op.add_column("login_identifiers", sa.Column("market", sa.Enum("sg", "my", name="market", native_enum=False, create_constraint=True), nullable=True))

    # ---- the data: a person for every customer someone logs in or is identified as, then everything moves to them
    op.execute(
        """
        INSERT INTO people (person_ref, full_name, salutation, mobile, language, nationality)
        SELECT 'P' || lpad(c.id::text, 5, '0'),
               coalesce(c.contact_name, c.name),
               coalesce(c.contact_name, c.name),
               CASE WHEN row_number() OVER (PARTITION BY c.mobile ORDER BY c.id) = 1 THEN c.mobile END,
               'en',
               upper(c.market)
        FROM customers c
        WHERE EXISTS (SELECT 1 FROM login_identifiers x WHERE x.customer_id = c.id)
           OR EXISTS (SELECT 1 FROM credentials x WHERE x.customer_id = c.id)
           OR EXISTS (SELECT 1 FROM identity_documents x WHERE x.customer_id = c.id)
        """
    )
    op.execute(
        """
        INSERT INTO relationships (person_id, customer_id, role)
        SELECT p.id, c.id, CASE WHEN c.customer_type = 'business' THEN 'director' ELSE 'owner' END
        FROM people p JOIN customers c ON p.person_ref = 'P' || lpad(c.id::text, 5, '0')
        """
    )
    for table in OWNED:
        op.execute(f"UPDATE {table} t SET person_id = r.person_id FROM relationships r WHERE r.customer_id = t.customer_id")
    op.execute("UPDATE login_identifiers t SET market = c.market FROM customers c WHERE c.id = t.customer_id")
    op.execute(
        """
        INSERT INTO account_holders (account_id, person_id, role, can_transact)
        SELECT a.id, r.person_id, CASE WHEN r.role = 'owner' THEN 'primary' ELSE 'signatory' END, true
        FROM accounts a JOIN relationships r ON r.customer_id = a.customer_id
        """
    )

    # ---- the new links are required; the old ones go
    for table in OWNED:
        op.alter_column(table, "person_id", nullable=False)
    op.alter_column("login_identifiers", "market", nullable=False)

    op.drop_constraint(op.f("uq_credentials_customer_id_kind"), "credentials", type_="unique")
    op.drop_constraint(op.f("fk_credentials_customer_id_customers"), "credentials", type_="foreignkey")
    op.drop_column("credentials", "customer_id")
    op.create_unique_constraint(op.f("uq_credentials_person_id_kind"), "credentials", ["person_id", "kind"])
    op.create_foreign_key(op.f("fk_credentials_person_id_people"), "credentials", "people", ["person_id"], ["id"], ondelete="CASCADE")

    op.drop_index(op.f("ix_identity_documents_customer_id"), table_name="identity_documents")
    op.drop_constraint(op.f("fk_identity_documents_customer_id_customers"), "identity_documents", type_="foreignkey")
    op.drop_column("identity_documents", "customer_id")
    op.create_index(op.f("ix_identity_documents_person_id"), "identity_documents", ["person_id"], unique=False)
    op.create_foreign_key(op.f("fk_identity_documents_person_id_people"), "identity_documents", "people", ["person_id"], ["id"], ondelete="CASCADE")

    op.drop_index(op.f("ix_login_identifiers_customer_id"), table_name="login_identifiers")
    op.drop_constraint(op.f("uq_login_identifiers_kind_fingerprint"), "login_identifiers", type_="unique")
    op.drop_constraint(op.f("fk_login_identifiers_customer_id_customers"), "login_identifiers", type_="foreignkey")
    op.drop_column("login_identifiers", "customer_id")
    op.create_index(op.f("ix_login_identifiers_person_id"), "login_identifiers", ["person_id"], unique=False)
    op.create_unique_constraint(op.f("uq_login_identifiers_market_kind_fingerprint"), "login_identifiers", ["market", "kind", "fingerprint"])
    op.create_foreign_key(op.f("fk_login_identifiers_person_id_people"), "login_identifiers", "people", ["person_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    # logins, PINs and documents go back to a customer each person banks as (their first link)
    for table in OWNED:
        op.add_column(table, sa.Column("customer_id", sa.Integer(), nullable=True))
        op.execute(
            f"""
            UPDATE {table} t SET customer_id = (
                SELECT r.customer_id FROM relationships r WHERE r.person_id = t.person_id ORDER BY r.id LIMIT 1
            )
            """
        )
        op.execute(f"DELETE FROM {table} WHERE customer_id IS NULL")
        op.alter_column(table, "customer_id", nullable=False)

    op.drop_constraint(op.f("fk_login_identifiers_person_id_people"), "login_identifiers", type_="foreignkey")
    op.drop_constraint(op.f("uq_login_identifiers_market_kind_fingerprint"), "login_identifiers", type_="unique")
    op.drop_index(op.f("ix_login_identifiers_person_id"), table_name="login_identifiers")
    op.drop_column("login_identifiers", "market")
    op.drop_column("login_identifiers", "person_id")
    op.create_unique_constraint(op.f("uq_login_identifiers_kind_fingerprint"), "login_identifiers", ["kind", "fingerprint"])
    op.create_index(op.f("ix_login_identifiers_customer_id"), "login_identifiers", ["customer_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_login_identifiers_customer_id_customers"), "login_identifiers", "customers", ["customer_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint(op.f("fk_identity_documents_person_id_people"), "identity_documents", type_="foreignkey")
    op.drop_index(op.f("ix_identity_documents_person_id"), table_name="identity_documents")
    op.drop_column("identity_documents", "person_id")
    op.create_index(op.f("ix_identity_documents_customer_id"), "identity_documents", ["customer_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_identity_documents_customer_id_customers"), "identity_documents", "customers", ["customer_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint(op.f("fk_credentials_person_id_people"), "credentials", type_="foreignkey")
    op.drop_constraint(op.f("uq_credentials_person_id_kind"), "credentials", type_="unique")
    op.drop_column("credentials", "person_id")
    op.create_unique_constraint(op.f("uq_credentials_customer_id_kind"), "credentials", ["customer_id", "kind"])
    op.create_foreign_key(op.f("fk_credentials_customer_id_customers"), "credentials", "customers", ["customer_id"], ["id"], ondelete="CASCADE")

    op.drop_index(op.f("ix_account_holders_person_id"), table_name="account_holders")
    op.drop_index(op.f("ix_account_holders_account_id"), table_name="account_holders")
    op.drop_table("account_holders")
    op.drop_index(op.f("ix_relationships_person_id"), table_name="relationships")
    op.drop_index(op.f("ix_relationships_customer_id"), table_name="relationships")
    op.drop_table("relationships")
    op.drop_table("people")
