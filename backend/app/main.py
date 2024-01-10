from decimal import Decimal

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from starlette.responses import Response

from app.db import get_engine, Trip, Invoice, init_engine
from app.download import download_new_invoices
from app.model import Submission


init_engine()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/")
async def main(submission: Submission, background_tasks: BackgroundTasks):
    with Session(get_engine()) as session:
        trip_ids = []

        for item in submission.data:
            trip_id = item.summary["uuid"]

            invoices = [
                Invoice(download_url=invoice["downloadURL"])
                for invoice in item.invoices
            ]

            fare = item.details.get("trip", {}).get("fare")
            if fare:
                try:
                    fare = Decimal(fare.replace("₹", ""))
                except ValueError:
                    fare = None
            else:
                fare = None

            trip = Trip(
                user_id=submission.user_id,
                trip_id=trip_id,
                summary=item.summary,
                details=item.details,
                invoices=invoices,
                fare=fare,
            )
            session.add(trip)
            trip_ids.append(trip_id)

        session.commit()

        background_tasks.add_task(download_new_invoices, trip_ids)

    return Response(status_code=201)


"""
SELECT trip.id, uid.amount_payable, did.amount_payable, uid.amount_payable + did.amount_payable, trip.fare, uid.amount_payable + did.amount_payable != trip.fare
  FROM trip
  JOIN driver_invoice_data did on trip.trip_id = did.trip_id
  JOIN uber_invoice_data uid on trip.trip_id = uid.trip_id
"""
