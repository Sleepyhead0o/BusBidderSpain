
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
    dest: str
    startD: date
    endD: date
    max_p: float | None = None
    max_tr: int | None = None
    min_lug: int = 0
    max_dur: int | None = None
    req_ch: bool = False
    req_ref: bool = False
    pref_t: time = time(9, 0)
    seats: int = 1

    def __post_init__(self):

        if (
            not isinstance(self.dest, str)
            or not self.dest.strip()
        ):
            raise ValueError("Invalid destination")

        if (
            type(self.startD) is not date
            or type(self.endD) is not date
        ):
            raise ValueError("Invalid dates")

        if self.startD > self.endD:
            raise ValueError("Invalid date range")

        p = self.max_p

        if p is not None:
            if (
                isinstance(p, bool)
                or not isinstance(p, (int, float))
                or not isfinite(p)
                or p < 0
            ):
                raise ValueError("Invalid budget")

        vals = (
            ("Transfers", self.max_tr, 0),
            ("Luggage", self.min_lug, 0),
            ("Duration", self.max_dur, 1),
            ("Seats", self.seats, 1)
        )

        for n, v, low in vals:

            if v is None and n in ("Transfers", "Duration"):
                continue

            if type(v) is not int or v < low:
                raise ValueError(f"Invalid {n}")

        if type(self.req_ch) is not bool:
            raise ValueError("Invalid changeable requirement")

        if type(self.req_ref) is not bool:
            raise ValueError("Invalid refundable requirement")

        if type(self.pref_t) is not time:
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
