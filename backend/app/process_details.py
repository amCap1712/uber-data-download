import traceback
from decimal import Decimal

from sqlmodel import Session, select

from app.db import get_engine, Trip, init_engine


def main():
    condition = Trip.duration.is_(None)
    with Session(get_engine()) as session:
        query = select(Trip).where(condition)
        trips = session.scalars(query)

        for trip in trips:
            try:
                trip_dict = trip.details.get("trip", {})
                receipt_dict = trip.details.get("receipt", {})

                distance = receipt_dict.get("distance")
                if distance is not None:
                    print(distance)
                    trip.distance = Decimal(distance)
                trip.distance_label = receipt_dict.get("distanceLabel")

                trip.duration = receipt_dict.get("duration")
                trip.begin_trip_time = trip_dict.get("beginTripTime")
                trip.dropoff_trip_time = trip_dict.get("dropoffTime")

                waypoints = trip_dict.get("waypoints", [])
                if len(waypoints) >= 2:
                    trip.begin_address = waypoints[0]
                    trip.dropoff_address = waypoints[-1]

                session.add(trip)
                session.commit()
            except Exception:
                traceback.print_exc()
                session.rollback()


if __name__ == "__main__":
    init_engine()
    main()
