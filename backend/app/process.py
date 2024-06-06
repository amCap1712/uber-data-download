import asyncio
import decimal
import traceback
from decimal import Decimal

from sqlmodel import Session, select, and_
from pypdf import PdfReader

from app.db import get_engine, Invoice, InvoiceType, UberInvoiceData, DriverInvoiceData, init_engine


def pdf_to_text(file_path: str) -> tuple[InvoiceType, list[str]]:
    reader = PdfReader(file_path)
    page = reader.pages[0]
    text = page.extract_text()

    ltext = text.lower()
    if "uber fees" in ltext or "booking fee" in ltext or "convenience fee" in ltext:
        invoice_type = InvoiceType.UBER
    else:
        invoice_type = InvoiceType.DRIVER

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)

    return invoice_type, lines


def extract_decimal_value(lines: list[str], key: str, offset: int) -> Decimal:
    key = key.lower()
    for idx, line in enumerate(lines):
        if key in line.lower():
            value = lines[idx + offset]
            if value == "-":
                offset += 1
                value = "-" + lines[idx + offset]
            value = value.replace(",", "")
            return Decimal(value)


def extract_tax(lines: list[str]) -> tuple[Decimal, int]:
    for idx, line in enumerate(lines):
        if "Total CGST" in line or "Total SGST" in line:
            offset = 2
            value1 = lines[idx + offset]
            if value1 == "-":
                offset += 1
                value1 = "-" + lines[idx + offset]
            value1 = value1.replace(",", "")

            offset += 3
            value2 = lines[idx + offset]
            if value2 == "-":
                offset += 1
                value2 = "-" + lines[idx + offset]
            value2 = value2.replace(",", "")

            value = Decimal(value1) + Decimal(value2)
            return value, 4 + offset
        
        if "Total IGST" in line:
            offset = 2
            value = lines[idx + offset]
            if value == "-":
                offset += 1
                value = "-" + lines[idx + offset]
            value = value.replace(",", "")

            return Decimal(value), 4 + offset

    return Decimal(0), 6


def extract_uber_invoice_data(trip_id: str, lines: list[str]):
    tax, offset = extract_tax(lines)

    uber_fees = extract_decimal_value(lines, "Uber Fees", offset)
    if uber_fees is None:
        uber_fees = Decimal(0)
    booking_fee = extract_decimal_value(lines, "Booking Fee", offset)
    if booking_fee is None:
        booking_fee = Decimal(0)
    convenience_fee = extract_decimal_value(lines, "Convenience Fee", offset)
    if convenience_fee is None:
        convenience_fee = Decimal(0)
    fees = uber_fees + booking_fee + convenience_fee

    net_amount = extract_decimal_value(lines, "Total net amount", 2)
    try:
        rounding = extract_decimal_value(lines, "Rounding", offset)
        if rounding is None:
            rounding = Decimal(0)
    except decimal.InvalidOperation:
        rounding = Decimal(0)
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
    tax, offset = extract_tax(lines)
    fare = extract_decimal_value(lines, "Transportation service fare", offset)
    if fare is None:
        print(lines)
    net_amount = extract_decimal_value(lines, "Total net amount", 2)
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
                fields = ["Australia", "United Kingdom", "Credit Note"]
                skip = False
                for line in lines:
                    for field in fields:
                        if field.lower() in line.lower():
                            skip = True
                            break
                if skip:
                    continue
                print(invoice.get_path())
                if invoice_type == InvoiceType.UBER:
                    invoice_data = extract_uber_invoice_data(invoice.trip_id, lines)
                    if invoice_data.fees is not None:
                        session.add(invoice_data)
                        invoice.processed = True
                        session.commit()
                else:
                    invoice_data = extract_driver_invoice_data(invoice.trip_id, lines)
                    if invoice_data.fare is not None:
                        session.add(invoice_data)
                        invoice.processed = True
                        session.commit()
            except Exception as e:
                traceback.print_exc()


async def process_new_invoices(invoice_ids: list[int]):
    await process_invoices(Invoice.id.in_(invoice_ids))


async def process_old_invoices():
    await process_invoices(and_(Invoice.processed.is_(False), Invoice.downloaded.is_(True)))


if __name__ == "__main__":
    init_engine()
    asyncio.run(process_old_invoices())
