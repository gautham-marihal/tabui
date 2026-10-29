"""People, the customers (CIFs) they bank as, and how they prove who they are.

A person is one human, in either country. They bank through customer records: their own (personal) and those of
companies they act for; a joint account belongs to a customer record two people own together. Accounts belong to a
customer; who may use each one, and how, is in account_holders. A person logs in once (a phone code or key code, and a
PIN or TPIN) and sees every account they hold, in both countries.

Each fact is kept in one place: a person's name, mobile and language on the person; a company's name and registration on
its customer record; who acts for a company in relationships.
"""

import enum
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Timestamps
from .common import Market, MarketColumn, choice


class Person(Timestamps, Base):
    """One human the bank knows, whatever they bank as and wherever."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_ref: Mapped[str] = mapped_column(String(12), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    # how the agents address them ("Mr Tan", "Puan Aisyah")
    salutation: Mapped[str] = mapped_column(String(60))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    # E.164: SMS one-time passwords go here, and calls from it are recognised
    mobile: Mapped[str | None] = mapped_column(String(16), unique=True)
    email: Mapped[str | None] = mapped_column(String(120))
    # en, zh or ms
    language: Mapped[str] = mapped_column(String(5), default="en", server_default="en")
    nationality: Mapped[str] = mapped_column(String(2))
    # what they call about most (e.g. "balance"), so an agent can offer it first
    favourite_transaction: Mapped[str] = mapped_column(String(30), default="", server_default="")
    # three wrong one-time passwords suspend them until a branch resets it
    otp_suspended: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    relationships: Mapped[list["Relationship"]] = relationship(back_populates="person", order_by="Relationship.id")
    holdings: Mapped[list["AccountHolder"]] = relationship(back_populates="person", order_by="AccountHolder.id")
    identifiers: Mapped[list["LoginIdentifier"]] = relationship(back_populates="person")
    credentials: Mapped[list["Credential"]] = relationship(back_populates="person")
    identity_documents: Mapped[list["IdentityDocument"]] = relationship(back_populates="person")
    addresses: Mapped[list["Address"]] = relationship(back_populates="person", order_by="Address.id")


class CustomerType(enum.StrEnum):
    BUSINESS = "business"
    PERSONAL = "personal"
    CONSUMER = "consumer"


class AccessLevel(enum.StrEnum):
    # Singapore phone banking: P full access, AS account services only, AC account enquiries only
    FULL = "P"
    ACCOUNT_SERVICES = "AS"
    ENQUIRIES = "AC"


class Segment(enum.StrEnum):
    BUSINESS_INDIVIDUAL = "BI"
    BUSINESS_CORPORATE = "BC"


class RiskRating(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Customer(Timestamps, Base):
    """A customer record (the CIF): a company, or one or two people's own banking, in one country."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    cif: Mapped[str] = mapped_column(String(20), unique=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    name: Mapped[str] = mapped_column(String(120))
    customer_type: Mapped[CustomerType] = mapped_column(choice(CustomerType, "customer_type"))
    # a company's registration: the UEN in Singapore, the SSM number in Malaysia
    registration_number: Mapped[str | None] = mapped_column(String(20))
    access_level: Mapped[AccessLevel | None] = mapped_column(choice(AccessLevel, "access_level"))
    segment: Mapped[Segment | None] = mapped_column(choice(Segment, "segment"))
    customer_since: Mapped[date] = mapped_column(Date)
    home_branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"))
    # the relationship manager who looks after the customer
    service_manager_id: Mapped[int | None] = mapped_column(ForeignKey("service_managers.id"))
    risk_rating: Mapped[RiskRating] = mapped_column(choice(RiskRating, "risk_rating"), default=RiskRating.LOW)
    kyc_review_due: Mapped[date | None] = mapped_column(Date)
    business_internet_banking: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    iq_member: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer", order_by="Account.id")  # noqa: F821
    relationships: Mapped[list["Relationship"]] = relationship(back_populates="customer", order_by="Relationship.id")
    addresses: Mapped[list["Address"]] = relationship(back_populates="customer", order_by="Address.id")
    home_branch: Mapped["Branch | None"] = relationship()  # noqa: F821
    service_manager: Mapped["ServiceManager | None"] = relationship()  # noqa: F821

    @property
    def contact(self) -> "Person | None":
        """Who the bank speaks to for the customer: a company's director (else a signatory), or the first owner."""
        order = (RelationshipRole.DIRECTOR, RelationshipRole.OWNER, RelationshipRole.SIGNATORY)
        linked = sorted(self.relationships, key=lambda r: (order.index(r.role), r.id))
        return linked[0].person if linked else None


class RelationshipRole(enum.StrEnum):
    OWNER = "owner"  # their own banking (two owners: a joint customer record)
    DIRECTOR = "director"  # runs the company, signs for it
    SIGNATORY = "signatory"  # authorised to operate the company's accounts


class Relationship(Timestamps, Base):
    """How a person is linked to a customer: their own banking, or a company they act for."""

    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("person_id", "customer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    role: Mapped[RelationshipRole] = mapped_column(choice(RelationshipRole, "relationship_role"))

    person: Mapped[Person] = relationship(back_populates="relationships")
    customer: Mapped[Customer] = relationship(back_populates="relationships")


class HolderRole(enum.StrEnum):
    PRIMARY = "primary"  # the account is theirs
    JOINT = "joint"  # held with someone else
    SIGNATORY = "signatory"  # a company's account they may operate


class AccountHolder(Timestamps, Base):
    """Who may use an account, and how. These are the accounts a person sees once they log in."""

    __tablename__ = "account_holders"
    __table_args__ = (UniqueConstraint("account_id", "person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    role: Mapped[HolderRole] = mapped_column(choice(HolderRole, "holder_role"))
    # may move money, stop cheques and the like; otherwise enquiries only
    can_transact: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    account: Mapped["Account"] = relationship()  # noqa: F821
    person: Mapped[Person] = relationship(back_populates="holdings")


class AddressKind(enum.StrEnum):
    HOME = "home"
    REGISTERED = "registered"  # a company's registered office
    MAILING = "mailing"  # where statements and cheque books are posted


class Address(Timestamps, Base):
    """A postal address of a person or of a customer record (never both)."""

    __tablename__ = "addresses"
    __table_args__ = (CheckConstraint("(person_id IS NULL) <> (customer_id IS NULL)", name="one_owner"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AddressKind] = mapped_column(choice(AddressKind, "address_kind"))
    line1: Mapped[str] = mapped_column(String(120))
    line2: Mapped[str] = mapped_column(String(120), default="", server_default="")
    postal_code: Mapped[str] = mapped_column(String(10))
    city: Mapped[str] = mapped_column(String(60))
    country: Mapped[str] = mapped_column(String(2))

    person: Mapped[Person | None] = relationship(back_populates="addresses")
    customer: Mapped[Customer | None] = relationship(back_populates="addresses")


class IdentifierKind(enum.StrEnum):
    PHONE_CODE = "phone_code"
    KEY_CODE = "key_code"


class LoginIdentifier(Timestamps, Base):
    """A code a person logs in with on one country's lines (phone code, key code): only a keyed fingerprint is kept."""

    __tablename__ = "login_identifiers"
    __table_args__ = (UniqueConstraint("market", "kind", "fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    market: Mapped[Market] = mapped_column(MarketColumn)
    kind: Mapped[IdentifierKind] = mapped_column(choice(IdentifierKind, "identifier_kind"))
    fingerprint: Mapped[str] = mapped_column(String(64))
    last4: Mapped[str] = mapped_column(String(4))

    person: Mapped[Person] = relationship(back_populates="identifiers")


class CredentialKind(enum.StrEnum):
    PIN = "pin"  # Singapore
    TPIN = "tpin"  # Malaysia


class Credential(Timestamps, Base):
    """A secret a person proves who they are with (PIN, telephone PIN): a salted hash, wrong tries and the lock."""

    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint("person_id", "kind"),
        CheckConstraint("failed_attempts >= 0", name="failed_attempts_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    kind: Mapped[CredentialKind] = mapped_column(choice(CredentialKind, "credential_kind"))
    secret_hash: Mapped[str] = mapped_column(String(200))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    person: Mapped[Person] = relationship(back_populates="credentials")


class DocumentType(enum.StrEnum):
    NRIC = "nric"  # Singapore
    MYKAD = "mykad"  # Malaysia (the IC number)


class IdentityDocument(Timestamps, Base):
    """A person's national ID: the full number only as a fingerprint, the last four for checks."""

    __tablename__ = "identity_documents"
    __table_args__ = (UniqueConstraint("document_type", "fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[DocumentType] = mapped_column(choice(DocumentType, "document_type"))
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    last4: Mapped[str] = mapped_column(String(4))

    person: Mapped[Person] = relationship(back_populates="identity_documents")
