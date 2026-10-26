from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from math import isfinite


class DataError(Exception):
    pass


class BookingError(Exception):
    pass


@dataclass
class Company:
    code: str
    name: str
    description: str


@dataclass
class Offer:
    id: str
    company: str
    destination: str
    depart: datetime
    arrive: datetime
    price: Decimal
    transfers: int
    luggage: int
    changeable: bool
    refundable: bool
    seats: int
    rating: float
    emissions: float | None = None

    @property
    def duration(self):
        return int(
            (self.arrive - self.depart).total_seconds() / 60
        )

    @property
    def day(self):
        return self.depart.date()


@dataclass
class Request:
    destination: str
    start: date
    end: date
    budget: Decimal | None = None
    preferred: time | None = None
    max_transfers: int | None = None
    luggage: int = 0
    max_minutes: int | None = None
    changeable: bool = False
    refundable: bool = False
    seats: int = 1

    def __post_init__(self):
        if not self.destination or self.start > self.end:
            raise DataError(
                "Destination or travel dates are invalid."
            )

        if self.budget is not None:
            if not self.budget.is_finite() or self.budget <= 0:
                raise DataError(
                    "Budget must be positive."
                )

        if self.max_transfers is not None:
            if self.max_transfers < 0:
                raise DataError(
                    "Maximum transfers cannot be negative."
                )

        if self.max_minutes is not None:
            if self.max_minutes <= 0:
                raise DataError(
                    "Maximum duration must be positive."
                )

        if self.luggage < 0 or self.seats < 1:
            raise DataError(
                "Luggage or seat count is invalid."
            )


@dataclass
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
            not isfinite(v) or v < 0
            for v in vals
        ):
            raise DataError(
                "Weights must be nonnegative numbers."
            )

        if abs(sum(vals) - 100) > 0.000001:
            raise DataError(
                "Weights must add up to 100%."
            )


@dataclass
class Score:
    offer: Offer
    points: dict
    total: float