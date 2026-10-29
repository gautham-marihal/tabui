"""Value lists shared by the tables. Stored as checked text, so a wrong value is refused by the database itself."""

import enum

from sqlalchemy import Enum


class Market(enum.StrEnum):
    SG = "sg"
    MY = "my"


def choice(enum_class: type[enum.Enum], name: str) -> Enum:
    """A column limited to an enum's values: VARCHAR plus a CHECK constraint (no database-side type to migrate)."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(m.value) for m in enum_class),
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


MarketColumn = choice(Market, "market")
