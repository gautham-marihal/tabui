"""The database connection, the base class every table derives from, and the columns most tables share."""

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, MetaData, Numeric, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import settings

# Constraint names follow one pattern, so migrations name them the same way every time.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Money is exact: 18 digits, 2 after the point. Rates keep more places.
Money = Numeric(18, 2)
Rate = Numeric(9, 4)
FxRate = Numeric(14, 6)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {Decimal: Money}


class Timestamps:
    """When a row was made and last changed, set by the database itself."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


def make_engine(url: str | None = None):
    return create_engine(url or settings.database_url, pool_pre_ping=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One session per request: committed when the handler returns, rolled back if it raises."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
