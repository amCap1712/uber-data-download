import asyncio
import traceback
from decimal import Decimal

from sqlmodel import Session, select, and_
from pypdf import PdfReader

from app.db import get_engine, Invoice, InvoiceType, UberInvoiceData, DriverInvoiceData, init_engine


def pdf_to_text(file_path: str) -> tuple[InvoiceType, list[str]]:
    reader = PdfReader(file_path)
    page = reader.pages[0]
    text = page.extract_text()

    invoice_type = InvoiceType.UBER if "uber fees" in text.lower() else InvoiceType.DRIVER

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)

    return invoice_type, lines


def extract_decimal_value(lines: list[str], key: str, offset: int) -> Decimal:
    value = lines[lines.index(key) + offset]
    if value == '-':
        new_offset = offset + (2 if offset == 6 else 1)
        value = '-' + lines[lines.index(key) + new_offset]
    return Decimal(value)


def extract_uber_invoice_data(trip_id: str, lines: list[str]):
    try:
        rounding = extract_decimal_value(lines, "Rounding", 6)
    except ValueError:
        rounding = Decimal(0)
    fees = extract_decimal_value(lines, "Uber Fees", 6)
    net_amount = extract_decimal_value(lines, "Total net amount", 2)
    tax = extract_decimal_value(lines, "Total IGST 18%", 2)
    amount_payable = extract_decimal_value(lines, "Total amount payable", 2)
    return UberInvoiceData(
        trip_id=trip_id,
        rounding=rounding,
        fees=fees,
        net_amount=net_amount,
        tax=tax,
        amount_payable=amount_payable,
    )


def extract_driver_invoice_data(trip_id: str, lines: list[str]):
    fare = extract_decimal_value(lines, "Transportation service fare", 9)
    net_amount = extract_decimal_value(lines, "Total net amount", 2)
    try:
        tax = extract_decimal_value(lines, "Total CGST 2.5%", 2) \
              + extract_decimal_value(lines, "Total SGST/UTGST 2.5%", 2)
    except ValueError:
        tax = extract_decimal_value(lines, "Total IGST 5%", 2)
    amount_payable = extract_decimal_value(lines, "Total amount payable", 2)
    return DriverInvoiceData(
        trip_id=trip_id,
        fare=fare,
        net_amount=net_amount,
        tax=tax,
        amount_payable=amount_payable,
    )


async def process_invoices(condition):
    with Session(get_engine()) as session:
        query = select(Invoice).where(condition)
        invoices = session.scalars(query)

        for invoice in invoices:
            try:
                invoice_type, lines = pdf_to_text(str(invoice.get_path()))
                if invoice_type == InvoiceType.UBER:
                    invoice_data = extract_uber_invoice_data(invoice.trip_id, lines)
                else:
                    invoice_data = extract_driver_invoice_data(invoice.trip_id, lines)
                invoice.processed = True
                session.add(invoice_data)
            except Exception as e:
                traceback.print_exc()

        session.commit()


async def process_new_invoices(invoice_ids: list[int]):
    await process_invoices(Invoice.id.in_(invoice_ids))


async def process_old_invoices():
    await process_invoices(and_(Invoice.processed.is_(False), Invoice.downloaded.is_(True)))


if __name__ == "__main__":
    init_engine()
    asyncio.run(process_old_invoices())
