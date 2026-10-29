"""The bank's tables: customers and their logins, accounts and money, cheques, cards, the contact centre, branches,
published rates, one-time passwords and the audit log.

Revision ID: 066e584007e9
Revises: 
Create Date: 2026-10-29 12:33:51.556542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '066e584007e9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=True),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index(op.f('ix_audit_log_at'), 'audit_log', ['at'], unique=False)
    op.create_index(op.f('ix_audit_log_kind'), 'audit_log', ['kind'], unique=False)
    op.create_table('bank_identity',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('bank_name', sa.String(length=120), nullable=False),
    sa.Column('giro_bank_code', sa.String(length=10), nullable=False),
    sa.Column('swift_bic', sa.String(length=11), nullable=False),
    sa.Column('branch_code_note', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bank_identity')),
    sa.UniqueConstraint('market', name=op.f('uq_bank_identity_market'))
    )
    op.create_table('branches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('address', sa.String(length=200), nullable=False),
    sa.Column('opening_hours', sa.String(length=120), nullable=False),
    sa.Column('area', sa.String(length=40), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_branches')),
    sa.UniqueConstraint('code', name=op.f('uq_branches_code'))
    )
    op.create_table('call_registrations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cif', sa.String(length=20), nullable=False),
    sa.Column('intent', sa.String(length=120), nullable=False),
    sa.Column('skillset', sa.String(length=60), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_call_registrations'))
    )
    op.create_table('callbacks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('caller_phone', sa.String(length=16), nullable=False),
    sa.Column('callback_number', sa.String(length=20), nullable=False),
    sa.Column('reason', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('open', 'done', name='callback_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_callbacks')),
    sa.UniqueConstraint('reference', name=op.f('uq_callbacks_reference'))
    )
    op.create_index(op.f('ix_callbacks_caller_phone'), 'callbacks', ['caller_phone'], unique=False)
    op.create_table('callers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phone', sa.String(length=16), nullable=False),
    sa.Column('language', sa.String(length=5), nullable=False),
    sa.Column('favourite_transaction', sa.String(length=30), nullable=False),
    sa.Column('is_vip', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_callers')),
    sa.UniqueConstraint('phone', name=op.f('uq_callers_phone'))
    )
    op.create_table('card_applications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_fingerprint', sa.String(length=64), nullable=False),
    sa.Column('product', sa.String(length=60), nullable=False),
    sa.Column('status', sa.Enum('received', 'approved', 'declined', name='application_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('sent_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_card_applications'))
    )
    op.create_index(op.f('ix_card_applications_id_fingerprint'), 'card_applications', ['id_fingerprint'], unique=False)
    op.create_table('customers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cif', sa.String(length=20), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('contact_name', sa.String(length=120), nullable=True),
    sa.Column('customer_type', sa.Enum('business', 'personal', 'consumer', name='customer_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('access_level', sa.Enum('P', 'AS', 'AC', name='access_level', native_enum=False, create_constraint=True), nullable=True),
    sa.Column('segment', sa.Enum('BI', 'BC', name='segment', native_enum=False, create_constraint=True), nullable=True),
    sa.Column('mobile', sa.String(length=16), nullable=True),
    sa.Column('business_internet_banking', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('iq_member', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('otp_suspended', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_customers')),
    sa.UniqueConstraint('cif', name=op.f('uq_customers_cif'))
    )
    op.create_table('deposit_rates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('tenor_months', sa.Integer(), nullable=False),
    sa.Column('rate_pct', sa.Numeric(precision=9, scale=4), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('tenor_months > 0', name=op.f('ck_deposit_rates_tenor_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_deposit_rates')),
    sa.UniqueConstraint('market', 'currency', 'tenor_months', name=op.f('uq_deposit_rates_market_currency_tenor_months'))
    )
    op.create_table('exchange_rates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('bank_buys', sa.Numeric(precision=14, scale=6), nullable=False),
    sa.Column('bank_sells', sa.Numeric(precision=14, scale=6), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exchange_rates')),
    sa.UniqueConstraint('market', 'currency', name=op.f('uq_exchange_rates_market_currency'))
    )
    op.create_table('fax_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('fax_number', sa.String(length=20), nullable=False),
    sa.Column('document', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_fax_jobs')),
    sa.UniqueConstraint('reference', name=op.f('uq_fax_jobs_reference'))
    )
    op.create_table('forms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_forms')),
    sa.UniqueConstraint('code', name=op.f('uq_forms_code'))
    )
    op.create_table('lending_rates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('name', sa.String(length=30), nullable=False),
    sa.Column('rate_pct', sa.Numeric(precision=9, scale=4), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lending_rates')),
    sa.UniqueConstraint('market', 'name', name=op.f('uq_lending_rates_market_name'))
    )
    op.create_table('promotions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('valid_until', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_promotions')),
    sa.UniqueConstraint('code', name=op.f('uq_promotions_code'))
    )
    op.create_table('service_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('route', sa.String(length=40), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_codes')),
    sa.UniqueConstraint('code', name=op.f('uq_service_codes_code'))
    )
    op.create_table('service_managers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('team', sa.String(length=60), nullable=False),
    sa.Column('available', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_managers')),
    sa.UniqueConstraint('code', name=op.f('uq_service_managers_code'))
    )
    op.create_table('service_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sr_number', sa.String(length=20), nullable=True),
    sa.Column('cif', sa.String(length=20), nullable=False),
    sa.Column('account_number', sa.String(length=20), nullable=False),
    sa.Column('request_type', sa.String(length=60), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('subcategory', sa.String(length=60), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_service_requests')),
    sa.UniqueConstraint('sr_number', name=op.f('uq_service_requests_sr_number'))
    )
    op.create_table('statement_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('account_number', sa.String(length=20), nullable=False),
    sa.Column('month', sa.String(length=20), nullable=False),
    sa.Column('delivery', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_statement_requests')),
    sa.UniqueConstraint('reference', name=op.f('uq_statement_requests_reference'))
    )
    op.create_table('surveys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('profile', sa.String(length=20), nullable=False),
    sa.Column('q1', sa.SmallInteger(), nullable=False),
    sa.Column('q2', sa.SmallInteger(), nullable=False),
    sa.Column('q3', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('q1 BETWEEN 1 AND 5', name=op.f('ck_surveys_q1_is_1_to_5')),
    sa.CheckConstraint('q2 BETWEEN 1 AND 5', name=op.f('ck_surveys_q2_is_1_to_5')),
    sa.CheckConstraint('q3 BETWEEN 1 AND 5', name=op.f('ck_surveys_q3_is_1_to_5')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_surveys'))
    )
    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_number', sa.String(length=20), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('product', sa.String(length=60), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('ledger_balance', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('available_balance', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('cheques_enabled', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_acu', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_islamic', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('status', sa.Enum('active', 'dormant', name='account_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('char_length(currency) = 3', name=op.f('ck_accounts_currency_is_iso_code')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_accounts_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_accounts')),
    sa.UniqueConstraint('account_number', name=op.f('uq_accounts_account_number'))
    )
    op.create_index(op.f('ix_accounts_customer_id'), 'accounts', ['customer_id'], unique=False)
    op.create_table('appointment_slots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('appointment_type', sa.String(length=40), nullable=False),
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('slot_date', sa.Date(), nullable=False),
    sa.Column('slot_time', sa.Time(), nullable=False),
    sa.Column('is_taken', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name=op.f('fk_appointment_slots_branch_id_branches')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_appointment_slots')),
    sa.UniqueConstraint('code', name=op.f('uq_appointment_slots_code'))
    )
    op.create_index(op.f('ix_appointment_slots_appointment_type'), 'appointment_slots', ['appointment_type'], unique=False)
    op.create_table('bills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('biller_reference', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_bills_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bills')),
    sa.UniqueConstraint('customer_id', 'biller_reference', name=op.f('uq_bills_customer_id_biller_reference'))
    )
    op.create_index(op.f('ix_bills_customer_id'), 'bills', ['customer_id'], unique=False)
    op.create_table('cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('last4', sa.String(length=4), nullable=False),
    sa.Column('product', sa.String(length=60), nullable=False),
    sa.Column('status', sa.Enum('inactive', 'active', 'blocked', name='card_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('credit_limit', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('outstanding_balance', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('minimum_due', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('due_on', sa.Date(), nullable=False),
    sa.Column('annual_fee', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('annual_fee >= 0', name=op.f('ck_cards_fee_not_negative')),
    sa.CheckConstraint('credit_limit >= 0', name=op.f('ck_cards_limit_not_negative')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_cards_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cards')),
    sa.UniqueConstraint('last4', name=op.f('uq_cards_last4'))
    )
    op.create_index(op.f('ix_cards_customer_id'), 'cards', ['customer_id'], unique=False)
    op.create_table('credentials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('pin', 'tpin', name='credential_kind', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('secret_hash', sa.String(length=200), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('locked', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('failed_attempts >= 0', name=op.f('ck_credentials_failed_attempts_not_negative')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_credentials_customer_id_customers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_credentials')),
    sa.UniqueConstraint('customer_id', 'kind', name=op.f('uq_credentials_customer_id_kind'))
    )
    op.create_table('direct_debits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mandate_reference', sa.String(length=20), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('merchant', sa.String(length=120), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.Enum('active', 'terminated', name='mandate_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_direct_debits_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_direct_debits')),
    sa.UniqueConstraint('mandate_reference', name=op.f('uq_direct_debits_mandate_reference'))
    )
    op.create_index(op.f('ix_direct_debits_customer_id'), 'direct_debits', ['customer_id'], unique=False)
    op.create_table('hand_overs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('skillset', sa.String(length=60), nullable=False),
    sa.Column('priority', sa.String(length=10), nullable=False),
    sa.Column('intent', sa.String(length=120), nullable=False),
    sa.Column('service_manager_id', sa.Integer(), nullable=True),
    sa.Column('outcome', sa.Enum('transferred', 'unavailable', name='hand_over_outcome', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('screen_pop', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['service_manager_id'], ['service_managers.id'], name=op.f('fk_hand_overs_service_manager_id_service_managers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hand_overs'))
    )
    op.create_table('identity_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('document_type', sa.Enum('nric', 'mykad', name='document_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=True),
    sa.Column('last4', sa.String(length=4), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_identity_documents_customer_id_customers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_identity_documents')),
    sa.UniqueConstraint('document_type', 'fingerprint', name=op.f('uq_identity_documents_document_type_fingerprint'))
    )
    op.create_index(op.f('ix_identity_documents_customer_id'), 'identity_documents', ['customer_id'], unique=False)
    op.create_table('loans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('loan_number', sa.String(length=20), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('product', sa.String(length=60), nullable=False),
    sa.Column('monthly_instalment', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('next_due_on', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_loans_customer_id_customers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_loans')),
    sa.UniqueConstraint('loan_number', name=op.f('uq_loans_loan_number'))
    )
    op.create_index(op.f('ix_loans_customer_id'), 'loans', ['customer_id'], unique=False)
    op.create_table('login_identifiers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('phone_code', 'key_code', name='identifier_kind', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('last4', sa.String(length=4), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_login_identifiers_customer_id_customers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_login_identifiers')),
    sa.UniqueConstraint('kind', 'fingerprint', name=op.f('uq_login_identifiers_kind_fingerprint'))
    )
    op.create_index(op.f('ix_login_identifiers_customer_id'), 'login_identifiers', ['customer_id'], unique=False)
    op.create_table('one_time_passwords',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=200), nullable=False),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('attempts >= 0', name=op.f('ck_one_time_passwords_attempts_not_negative')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_one_time_passwords_customer_id_customers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_one_time_passwords'))
    )
    op.create_index(op.f('ix_one_time_passwords_customer_id'), 'one_time_passwords', ['customer_id'], unique=False)
    op.create_table('bookings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('slot_id', sa.Integer(), nullable=False),
    sa.Column('cif', sa.String(length=20), nullable=False),
    sa.Column('appointment_type', sa.String(length=40), nullable=False),
    sa.Column('contact_name', sa.String(length=120), nullable=False),
    sa.Column('cancelled', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['slot_id'], ['appointment_slots.id'], name=op.f('fk_bookings_slot_id_appointment_slots')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bookings')),
    sa.UniqueConstraint('reference', name=op.f('uq_bookings_reference'))
    )
    op.create_index(op.f('ix_bookings_cif'), 'bookings', ['cif'], unique=False)
    op.create_index(op.f('ix_bookings_slot_id'), 'bookings', ['slot_id'], unique=False)
    op.create_table('card_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('card_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('outcome', sa.String(length=20), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['card_id'], ['cards.id'], name=op.f('fk_card_actions_card_id_cards')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_card_actions')),
    sa.UniqueConstraint('reference', name=op.f('uq_card_actions_reference'))
    )
    op.create_index(op.f('ix_card_actions_card_id'), 'card_actions', ['card_id'], unique=False)
    op.create_table('cheque_book_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('account_number', sa.String(length=20), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('delivery', sa.Enum('normal', 'express', 'same_day', name='delivery', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('fee', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('ready_in_working_days', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_cheque_book_orders_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cheque_book_orders')),
    sa.UniqueConstraint('reference', name=op.f('uq_cheque_book_orders_reference'))
    )
    op.create_index(op.f('ix_cheque_book_orders_account_id'), 'cheque_book_orders', ['account_id'], unique=False)
    op.create_table('cheque_books',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('first_cheque_no', sa.String(length=6), nullable=False),
    sa.Column('last_cheque_no', sa.String(length=6), nullable=False),
    sa.Column('sent_on', sa.Date(), nullable=False),
    sa.Column('delivery', sa.String(length=80), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_cheque_books_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cheque_books'))
    )
    op.create_index(op.f('ix_cheque_books_account_id'), 'cheque_books', ['account_id'], unique=False)
    op.create_table('cheque_deposits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('deposited_on', sa.Date(), nullable=False),
    sa.Column('cheque_no', sa.String(length=10), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.Enum('cleared', 'clearing', 'returned', name='deposit_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('value_date', sa.Date(), nullable=True),
    sa.Column('return_reason', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_cheque_deposits_amount_positive')),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_cheque_deposits_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cheque_deposits'))
    )
    op.create_index(op.f('ix_cheque_deposits_account_id'), 'cheque_deposits', ['account_id'], unique=False)
    op.create_table('incoming_funds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('received_on', sa.Date(), nullable=False),
    sa.Column('remitter', sa.String(length=120), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.Enum('credited', 'pending', name='incoming_fund_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_incoming_funds_amount_positive')),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_incoming_funds_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incoming_funds'))
    )
    op.create_index(op.f('ix_incoming_funds_account_id'), 'incoming_funds', ['account_id'], unique=False)
    op.create_table('investigations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_reference', sa.String(length=20), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('topic', sa.String(length=120), nullable=False),
    sa.Column('service_manager_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_investigations_account_id_accounts')),
    sa.ForeignKeyConstraint(['service_manager_id'], ['service_managers.id'], name=op.f('fk_investigations_service_manager_id_service_managers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_investigations')),
    sa.UniqueConstraint('account_id', name=op.f('uq_investigations_account_id')),
    sa.UniqueConstraint('case_reference', name=op.f('uq_investigations_case_reference'))
    )
    op.create_table('issued_cheques',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('market', sa.Enum('sg', 'my', name='market', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('account_number', sa.String(length=20), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('cheque_no', sa.String(length=10), nullable=False),
    sa.Column('status', sa.Enum('paid', 'not presented', 'stopped', name='cheque_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('paid_on', sa.Date(), nullable=True),
    sa.Column('stopped_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_issued_cheques_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_issued_cheques')),
    sa.UniqueConstraint('account_number', 'cheque_no', name=op.f('uq_issued_cheques_account_number_cheque_no'))
    )
    op.create_index(op.f('ix_issued_cheques_account_id'), 'issued_cheques', ['account_id'], unique=False)
    op.create_table('own_transfers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('from_account_id', sa.Integer(), nullable=False),
    sa.Column('to_account_id', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_own_transfers_amount_positive')),
    sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id'], name=op.f('fk_own_transfers_from_account_id_accounts')),
    sa.ForeignKeyConstraint(['to_account_id'], ['accounts.id'], name=op.f('fk_own_transfers_to_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_own_transfers')),
    sa.UniqueConstraint('reference', name=op.f('uq_own_transfers_reference'))
    )
    op.create_index(op.f('ix_own_transfers_from_account_id'), 'own_transfers', ['from_account_id'], unique=False)
    op.create_index(op.f('ix_own_transfers_to_account_id'), 'own_transfers', ['to_account_id'], unique=False)
    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('from_account_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('loan', 'credit_card', 'utility', 'giro', name='payment_kind', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('payee', sa.String(length=120), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_payments_amount_positive')),
    sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id'], name=op.f('fk_payments_from_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payments')),
    sa.UniqueConstraint('reference', name=op.f('uq_payments_reference'))
    )
    op.create_index(op.f('ix_payments_from_account_id'), 'payments', ['from_account_id'], unique=False)
    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('posted_on', sa.Date(), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_transactions_account_id_accounts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions'))
    )
    op.create_index(op.f('ix_transactions_account_id'), 'transactions', ['account_id'], unique=False)
    op.create_table('vips',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phone', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('vip_check', sa.Enum('account', 'phone_code', 'default', name='vip_check', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('customer_id', sa.Integer(), nullable=True),
    sa.Column('language', sa.String(length=5), nullable=False),
    sa.Column('service_manager_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_vips_account_id_accounts')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_vips_customer_id_customers')),
    sa.ForeignKeyConstraint(['service_manager_id'], ['service_managers.id'], name=op.f('fk_vips_service_manager_id_service_managers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vips')),
    sa.UniqueConstraint('phone', name=op.f('uq_vips_phone'))
    )
    op.create_table('stop_payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('reference', sa.String(length=30), nullable=True),
    sa.Column('issued_cheque_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=200), nullable=False),
    sa.Column('fee', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('fee_currency', sa.String(length=3), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['issued_cheque_id'], ['issued_cheques.id'], name=op.f('fk_stop_payments_issued_cheque_id_issued_cheques')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stop_payments')),
    sa.UniqueConstraint('reference', name=op.f('uq_stop_payments_reference'))
    )
    op.create_index(op.f('ix_stop_payments_issued_cheque_id'), 'stop_payments', ['issued_cheque_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stop_payments_issued_cheque_id'), table_name='stop_payments')
    op.drop_table('stop_payments')
    op.drop_table('vips')
    op.drop_index(op.f('ix_transactions_account_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_payments_from_account_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_own_transfers_to_account_id'), table_name='own_transfers')
    op.drop_index(op.f('ix_own_transfers_from_account_id'), table_name='own_transfers')
    op.drop_table('own_transfers')
    op.drop_index(op.f('ix_issued_cheques_account_id'), table_name='issued_cheques')
    op.drop_table('issued_cheques')
    op.drop_table('investigations')
    op.drop_index(op.f('ix_incoming_funds_account_id'), table_name='incoming_funds')
    op.drop_table('incoming_funds')
    op.drop_index(op.f('ix_cheque_deposits_account_id'), table_name='cheque_deposits')
    op.drop_table('cheque_deposits')
    op.drop_index(op.f('ix_cheque_books_account_id'), table_name='cheque_books')
    op.drop_table('cheque_books')
    op.drop_index(op.f('ix_cheque_book_orders_account_id'), table_name='cheque_book_orders')
    op.drop_table('cheque_book_orders')
    op.drop_index(op.f('ix_card_actions_card_id'), table_name='card_actions')
    op.drop_table('card_actions')
    op.drop_index(op.f('ix_bookings_slot_id'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_cif'), table_name='bookings')
    op.drop_table('bookings')
    op.drop_index(op.f('ix_one_time_passwords_customer_id'), table_name='one_time_passwords')
    op.drop_table('one_time_passwords')
    op.drop_index(op.f('ix_login_identifiers_customer_id'), table_name='login_identifiers')
    op.drop_table('login_identifiers')
    op.drop_index(op.f('ix_loans_customer_id'), table_name='loans')
    op.drop_table('loans')
    op.drop_index(op.f('ix_identity_documents_customer_id'), table_name='identity_documents')
    op.drop_table('identity_documents')
    op.drop_table('hand_overs')
    op.drop_index(op.f('ix_direct_debits_customer_id'), table_name='direct_debits')
    op.drop_table('direct_debits')
    op.drop_table('credentials')
    op.drop_index(op.f('ix_cards_customer_id'), table_name='cards')
    op.drop_table('cards')
    op.drop_index(op.f('ix_bills_customer_id'), table_name='bills')
    op.drop_table('bills')
    op.drop_index(op.f('ix_appointment_slots_appointment_type'), table_name='appointment_slots')
    op.drop_table('appointment_slots')
    op.drop_index(op.f('ix_accounts_customer_id'), table_name='accounts')
    op.drop_table('accounts')
    op.drop_table('surveys')
    op.drop_table('statement_requests')
    op.drop_table('service_requests')
    op.drop_table('service_managers')
    op.drop_table('service_codes')
    op.drop_table('promotions')
    op.drop_table('lending_rates')
    op.drop_table('forms')
    op.drop_table('fax_jobs')
    op.drop_table('exchange_rates')
    op.drop_table('deposit_rates')
    op.drop_table('customers')
    op.drop_index(op.f('ix_card_applications_id_fingerprint'), table_name='card_applications')
    op.drop_table('card_applications')
    op.drop_table('callers')
    op.drop_index(op.f('ix_callbacks_caller_phone'), table_name='callbacks')
    op.drop_table('callbacks')
    op.drop_table('call_registrations')
    op.drop_table('branches')
    op.drop_table('bank_identity')
    op.drop_index(op.f('ix_audit_log_kind'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_at'), table_name='audit_log')
    op.drop_table('audit_log')
