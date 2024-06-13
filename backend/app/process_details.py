from decimal import Decimal

from sqlmodel import Session, select

from app.db import get_engine, Invoice, Trip


def main():
    condition = Trip.duration.is_(None)
    with Session(get_engine()) as session:
        query = select(Invoice).where(condition)
        trips = session.execute(query).all()

        for trip in trips:
            trip_dict = trip.details.get("trip", {})
            receipt_dict = trip.details.get("receipt", {})

            trip.duration = receipt_dict.get("duration")
            trip.distance = Decimal(receipt_dict.get("distance"))
            trip.distance_label = receipt_dict.get("distanceLabel")
            trip.begin_trip_time = trip_dict.get("beginTripTime")
            trip.dropoff_time = trip_dict.get("dropoffTime")

            waypoints = trip_dict.get("waypoints", [])
            if len(waypoints) >= 2:
                trip.start_address = waypoints[0]
                trip.dropoff_address = waypoints[-1]

            session.add(trip)
            session.commit()


if __name__ == "__main__":
    main()
