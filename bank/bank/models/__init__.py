"""Every table, imported here so the metadata (and Alembic) sees them all."""

from .accounts import (
    Account,
    AccountStatus,
    FixedDeposit,
    Hold,
    IncomingFund,
    IncomingFundStatus,
    Loan,
    Maturity,
    OwnTransfer,
    Payment,
    PaymentKind,
    Transaction,
)
from .branches import AppointmentSlot, Booking, Branch
from .cards import ApplicationStatus, Bill, Biller, Card, CardAction, CardApplication, CardStatus, DirectDebit, MandateStatus, Payee
from .cheques import ChequeBook, ChequeBookOrder, ChequeDeposit, ChequeStatus, Delivery, DepositStatus, IssuedCheque, StopPayment
from .common import Market
from .contact_centre import (
    Callback,
    CallbackStatus,
    CallRegistration,
    FaxJob,
    HandOver,
    HandOverOutcome,
    Investigation,
    ServiceCode,
    ServiceManager,
    ServiceRequest,
    StatementRequest,
    Survey,
    Vip,
    VipCheck,
)
from .customers import (
    AccessLevel,
    AccountHolder,
    Address,
    AddressKind,
    Credential,
    CredentialKind,
    Customer,
    CustomerType,
    DocumentType,
    HolderRole,
    IdentifierKind,
    IdentityDocument,
    LoginIdentifier,
    Person,
    Relationship,
    RelationshipRole,
    RiskRating,
    Segment,
)
from .products import SPENDABLE, Product, ProductCategory
from .reference import BankIdentity, ContactPoint, DepositRate, ExchangeRate, Form, LendingRate, Promotion, PublicHoliday, Setting, Tariff
from .security import AuditEvent, OneTimePassword

__all__ = [name for name in dir() if not name.startswith("_")]
