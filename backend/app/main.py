import decimal
from decimal import Decimal

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.dialects.postgresql import insert
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


def parse_fare(fare: str):
    if not fare:
        return None
    try:
        index = 0
        for letter in fare:
            if letter.isnumeric():
                break
            index += 1
        return Decimal(fare[index:])
    except (ValueError, decimal.InvalidOperation):
        return None


@app.post("/")
async def main(submission: Submission, background_tasks: BackgroundTasks):
    with Session(get_engine()) as session:
        trip_ids = []

        for item in submission.data:
            trip_id = item.summary["uuid"]

            fare = parse_fare(item.details.get("trip", {}).get("fare"))

            statement = insert(Trip).values(
                user_id=submission.user_id,
                trip_id=trip_id,
                summary=item.summary,
                details=item.details,
                fare=fare,
            ).on_conflict_do_nothing().returning(Trip.id)
            result = session.execute(statement)

            if result.fetchone() is not None:
                for invoice in item.invoices:
                    session.add(Invoice(trip_id=trip_id, download_url=invoice["downloadURL"]))

            trip_ids.append(trip_id)

        session.commit()

        background_tasks.add_task(download_new_invoices, trip_ids)

    return Response(status_code=201)
