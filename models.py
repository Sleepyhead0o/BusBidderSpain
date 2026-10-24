from dataclasses import dataclass
from datetime import date, datetime, time
from math import isfinite


@dataclass(frozen=True)
class BusOffer:
    offer_id: str
    company: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    duration_minutes: int
    price_eur: float
    transfers: int
    luggage_bags: int
    changeable: bool
    refundable: bool
    available_seats: int
    customer_rating: float
    estimated_co2_kg: float | None


@dataclass(frozen=True)
class TravellerRequest:
    destination: str
    start_date: date
    end_date: date
    max_price: float | None = None
    max_transfers: int | None = None
    min_luggage: int = 0
    max_duration: int | None = None
    require_changeable: bool = False
    require_refundable: bool = False
    preferred_time: time = time(9, 0)
    seats: int = 1

    def __post_init__(self):

        if (
            not isinstance(self.destination, str)
            or not self.destination.strip()
        ):
            raise ValueError("Invalid destination")

        if (
            type(self.start_date) is not date
            or type(self.end_date) is not date
        ):
            raise ValueError("Invalid dates")

        if self.start_date > self.end_date:
            raise ValueError("Invalid date range")

        p = self.max_price

        if p is not None:
            if (
                isinstance(p, bool)
                or not isinstance(p, (int, float))
                or not isfinite(p)
                or p < 0
            ):
                raise ValueError("Invalid budget")

        vals = (
            ("Transfers", self.max_transfers, 0),
            ("Luggage", self.min_luggage, 0),
            ("Duration", self.max_duration, 1),
            ("Seats", self.seats, 1)
        )

        for name, v, low in vals:
            if v is None and name in ("Transfers", "Duration"):
                continue

            if type(v) is not int or v < low:
                raise ValueError(f"Invalid {name}")

        if type(self.require_changeable) is not bool:
            raise ValueError("Invalid changeable requirement")

        if type(self.require_refundable) is not bool:
            raise ValueError("Invalid refundable requirement")

        if type(self.preferred_time) is not time:
            raise ValueError("Invalid preferred time")


@dataclass(frozen=True)
class Weights:
    price: float
    duration: float
    time: float
    flexibility: float

    def __post_init__(self):

        vals = (
            self.price,
            self.duration,
            self.time,
            self.flexibility
        )

        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not isfinite(v)
            or not 0 <= v <= 1
            for v in vals
        ):
            raise ValueError("Invalid weights")

        if abs(sum(vals) - 1) > 1e-6:
            raise ValueError("Weights must total 1.0")


@dataclass(frozen=True)
class RankedOffer:
    offer: BusOffer
    price_score: float
    duration_score: float
    time_score: float
    flexibility_score: float
    total_score: float