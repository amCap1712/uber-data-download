import os
from datetime import datetime
from typing import Optional

from sqlalchemy import Identity, Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine, Relationship


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
    last_updated: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    trip_id: str = Field(foreign_key="trip.trip_id")
    trip: "Trip" = Relationship(back_populates="invoices")


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

    invoices: list[Invoice] = Relationship(back_populates="trip")

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
