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

            fare = parse_fare(item.details.get("trip", {}).get("fare"))

            statement = insert(Trip).values(
                user_id=submission.user_id,
                trip_id=trip_id,
                summary=item.summary,
                details=item.details,
                invoices_json=item.invoices,
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


@app.get("/study", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("study.html", {"request": request})


@app.post("/receipts")
async def create_upload_file(trip_id: str, file: UploadFile):
    path = MEDIA_BASE_PATH / "media" / trip_id / "receipt.pdf"
    path.parent.mkdir(exist_ok=True)
    with open(path, mode="wb") as f:
        f.write(file.file.read())
    return {}

"""
select user_id
     , max(trip_id)
     , count(*)
     , max(t.last_updated) as last_updated_max
  from trip t
  join invoice i
 using (trip_id)
 group by user_id
 order by last_updated_max desc 

 65f34d32d899ea4fd6d6197b
 65fb0cd08626e511f3eafccb
 65f4b1857f5b498314e118cf
 11c6dc4d-7acc-47b6-abfb-5cc1f3faf039
 cce64325-82bd-46f4-8ac9-02883361b3ea
 58d180a9-72b2-45e6-a2b8-9a1bdac83762

select t.*
  from trip t
  join invoice i
 using (trip_id)
 where t.user_id in ('65f34d32d899ea4fd6d6197b', '65fb0cd08626e511f3eafccb', '65f4b1857f5b498314e118cf')
   and i.processed is false;
   
with temp as (
    select user_id
     , trip_id
  from trip t
  join driver_invoice_data d
 using (trip_id)
group by user_id, trip_id
)
 select user_id
      , count(*)
   from temp
   where user_id like '65%'
 group by user_id
 order by user_id
"""

