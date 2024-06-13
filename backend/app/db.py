import os
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import Identity, Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine, Relationship


MEDIA_BASE_PATH = Path.cwd()


class InvoiceType(Enum):
    DRIVER = "driver"
    UBER = "uber"


class DriverInvoiceData(SQLModel, table=True):
    __tablename__ = "driver_invoice_data"
    id: Optional[int] = Field(
        default=None,
        sa_column_args=(Identity(always=True),),
        primary_key=True,
        nullable=False,
    )

    trip_id: str = Field(foreign_key="trip.trip_id")
    trip: "Trip" = Relationship(back_populates="driver_invoice_data")

    fare: Decimal
    net_amount: Decimal
    tax: Decimal
    amount_payable: Decimal


class UberInvoiceData(SQLModel, table=True):
    __tablename__ = "uber_invoice_data"
    id: Optional[int] = Field(
        default=None,
        sa_column_args=(Identity(always=True),),
        primary_key=True,
        nullable=False,
    )

    trip_id: str = Field(foreign_key="trip.trip_id")
    trip: "Trip" = Relationship(back_populates="uber_invoice_data")

    rounding: Decimal
    fees: Decimal
    net_amount: Decimal
    tax: Decimal
    amount_payable: Decimal


class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    id: Optional[int] = Field(
        default=None,
        sa_column_args=(Identity(always=True),),
        primary_key=True,
        nullable=False,
    )
    download_url: str
    downloaded: bool = Field(default=False)
    processed: bool = Field(default=False)
    last_updated: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    trip_id: str = Field(foreign_key="trip.trip_id")
    trip: "Trip" = Relationship(back_populates="invoices")

    def get_path(self) -> Path:
        filename = urlparse(self.download_url).path.split('/')[-1]
        return MEDIA_BASE_PATH / "media" / self.trip_id / filename


class Trip(SQLModel, table=True):
    __tablename__ = "trip"
    id: Optional[int] = Field(
        default=None,
        sa_column_args=(Identity(always=True),),
        primary_key=True,
        nullable=False,
    )
    user_id: str
    trip_id: str = Field(unique=True)
    summary: dict = Field(default={}, sa_column=Column(JSONB))
    details: dict = Field(default={}, sa_column=Column(JSONB))
    invoices_json: list[dict] = Field(default=[], sa_column=Column(JSONB))
    fare: Optional[Decimal] = None

    begin_trip_time: Optional[str] = None
    dropoff_trip_time: Optional[str] = None
    distance: Optional[Decimal] = None
    distance_label: Optional[str] = None
    duration: Optional[str] = None
    begin_address: Optional[str] = None
    dropoff_address: Optional[str] = None

    invoices: list[Invoice] = Relationship(back_populates="trip")

    driver_invoice_data: Optional[DriverInvoiceData] = Relationship(back_populates="trip")
    uber_invoice_data: Optional[UberInvoiceData] = Relationship(back_populates="trip")

    last_updated: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))


_engine: Engine | None = None


def init_engine():
    global _engine
    _engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))


def get_engine() -> Engine:
    global _engine
    return _engine


def create_db_and_tables():
    SQLModel.metadata.create_all(_engine)


if __name__ == "__main__":
    init_engine()
    create_db_and_tables()
