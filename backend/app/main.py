import decimal
import json
from decimal import Decimal

from fastapi import FastAPI, BackgroundTasks, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from starlette.templating import Jinja2Templates

from app.db import get_engine, Trip, Invoice, init_engine, MEDIA_BASE_PATH
from app.download import download_new_invoices
from app.model import Submission


init_engine()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
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

        print(json.dumps(jsonable_encoder(submission)))

        for item in submission.data:
            trip_id = item.summary["uuid"]
            trip_dict = item.details.get("trip", {})
            receipt_dict = item.details.get("receipt", {})

            begin_trip_time = trip_dict.get("beginTripTime")
            dropoff_trip_time = trip_dict.get("dropoffTime")
            fare = parse_fare(trip_dict.get("fare"))
            duration = receipt_dict.get("duration")

            distance = receipt_dict.get("distance")
            if distance is not None:
                try:
                    distance = Decimal(distance)
                except decimal.InvalidOperation:
                    distance = None
            distance_label = receipt_dict.get("distanceLabel")

            begin_address = None
            dropoff_address = None

            waypoints = trip_dict.get("waypoints", [])
            if len(waypoints) >= 2:
                begin_address = waypoints[0]
                dropoff_address = waypoints[-1]

            statement = insert(Trip).values(
                user_id=submission.user_id,
                trip_id=trip_id,
                summary=item.summary,
                details=item.details,
                invoices_json=item.invoices,
                fare=fare,
                duration=duration,
                distance=distance,
                distance_label=distance_label,
                begin_address=begin_address,
                dropoff_address=dropoff_address,
                begin_trip_time=begin_trip_time,
                dropoff_trip_time=dropoff_trip_time
            ).on_conflict_do_nothing().returning(Trip.id)
            result = session.execute(statement)

            if result.fetchone() is not None:
                for invoice in item.invoices:
                    session.add(Invoice(trip_id=trip_id, download_url=invoice["downloadURL"]))
                trip_ids.append(trip_id)

        session.commit()

        background_tasks.add_task(download_new_invoices, trip_ids)

    return Response(status_code=201)


@app.get("/study", response_class=HTMLResponse)
async def study_prolific(request: Request):
    return templates.TemplateResponse("study-prolific.html", {"request": request})


@app.get("/study/facebook", response_class=HTMLResponse)
async def study_facebook(request: Request):
    return templates.TemplateResponse("study-facebook.html", {"request": request})


@app.get("/study/thanks", response_class=HTMLResponse)
async def study_thanks(request: Request):
    return templates.TemplateResponse("study-thanks.html", {"request": request})


@app.post("/receipts")
async def create_upload_file(trip_id: str, file: UploadFile):
    path = MEDIA_BASE_PATH / "media" / trip_id / "receipt.pdf"
    path.parent.mkdir(exist_ok=True)
    with open(path, mode="wb") as f:
        f.write(file.file.read())
    return {}
