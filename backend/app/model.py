from pydantic import BaseModel


class TripSubmission(BaseModel):
    summary: dict
    details: dict
    invoices: list[dict]


class Submission(BaseModel):
    user_id: str
    data: list[TripSubmission]
