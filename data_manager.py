
import csv
import logging
import re

from datetime import datetime
from math import isfinite
from pathlib import Path

from models import BusOffer


COMPANIES = {
    "SolRuta", "Camino Express", "CostaLink",
    "VerdeBus", "NocheVia"
}

DESTINATIONS = {
    "Barcelona", "Valencia", "Seville",
    "Malaga", "Granada", "Cordoba",
    "Bilbao", "San Sebastian", "Zaragoza",
    "Alicante", "Murcia", "Salamanca",
    "Toledo", "Santiago de Compostela", "Cadiz"
}

FIELDS = {
    "offer_id", "comp", "orig", "dest",
    "travel_date", "dep_time", "arrivDate",
    "arrivTime", "dur", "price", "transf",
    "lug", "ch", "refund", "available_seats",
    "c-rating", "co2"
}


class OfferValidationError(ValueError):
    pass


def to_integer(v, name):

    if not re.fullmatch(r"\d+", v):
        raise OfferValidationError(
            f"Invalid integer: {name}"
        )

    return int(v)


def to_boolean(v, name):

    if v not in ("true", "false"):
        raise OfferValidationError(
            f"Invalid boolean: {name}"
        )

    return v == "true"


def to_datetime(day, clock):

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise OfferValidationError("Invalid date format")

    if not re.fullmatch(r"\d{2}:\d{2}", clock):
        raise OfferValidationError("Invalid time format")

    try:
        return datetime.strptime(
            f"{day} {clock}",
            "%Y-%m-%d %H:%M"
        )

    except ValueError as e:
        raise OfferValidationError(
            "Invalid date/time"
        ) from e


def to_decimal(v, name):

    try:
        num = float(v)

    except (ValueError, TypeError, OverflowError) as e:
        raise OfferValidationError(
            f"Invalid number: {name}"
        ) from e

    if not isfinite(num):
        raise OfferValidationError(
            f"Non-finite value: {name}"
        )

    return num


def validate_offer(row):

    missing = [
        f for f in FIELDS
        if f != "co2"
        and (
            row.get(f) is None
            or not str(row[f]).strip()
        )
    ]

    if missing:
        raise OfferValidationError(
            "Missing: " + ", ".join(sorted(missing))
        )

    oid = row["offer_id"]

    if not re.fullmatch(r"(BUS\d{3}|INVALID\d{2})", oid):
        raise OfferValidationError("Invalid offer ID")

    if row["comp"] not in COMPANIES:
        raise OfferValidationError("Unknown company")

    if row["orig"] != "Madrid":
        raise OfferValidationError("Invalid origin")

    if row["dest"] not in DESTINATIONS:
        raise OfferValidationError("Unknown destination")

    dep = to_datetime(
        row["travel_date"], row["dep_time"]
    )

    arr = to_datetime(
        row["arrivDate"], row["arrivTime"]
    )

    dur = to_integer(row["dur"], "duration")
    tr = to_integer(row["transf"], "transfers")
    lug = to_integer(row["lug"], "luggage")
    seats = to_integer(
        row["available_seats"], "seats"
    )

    price = to_decimal(row["price"], "price")
    rating = to_decimal(row["c-rating"], "rating")

    ch = to_boolean(row["ch"], "changeable")
    ref = to_boolean(row["refund"], "refundable")

    v = row.get("co2")

    co2 = (
        to_decimal(v, "CO2")
        if v is not None and v.strip()
        else None
    )

    if price < 0:
        raise OfferValidationError("Negative price")

    if not 1 <= rating <= 5:
        raise OfferValidationError("Invalid rating")

    if co2 is not None and co2 < 0:
        raise OfferValidationError("Negative CO2")

    actual = (arr - dep).total_seconds() / 60

    if actual <= 0 or actual != dur:
        raise OfferValidationError("Incorrect duration")

    return BusOffer(
        offer_id=oid,
        company=row["comp"],
        origin=row["orig"],
        destination=row["dest"],
        departure=dep,
        arrival=arr,
        duration_minutes=dur,
        price_eur=price,
        transfers=tr,
        luggage_bags=lug,
        changeable=ch,
        refundable=ref,
        available_seats=seats,
        customer_rating=rating,
        estimated_co2_kg=co2
    )


def load_offers(filename):

    path = Path(filename)

    if not path.is_file():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    valid = []
    rejected = []
    seen = set()

    with path.open(
        newline="", encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise OfferValidationError("Empty CSV")

        missing = FIELDS - set(reader.fieldnames)

        if missing:
            raise OfferValidationError(
                "Missing columns: "
                + ", ".join(sorted(missing))
            )

        for line, row in enumerate(reader, 2):

            try:
                if None in row:
                    raise OfferValidationError(
                        "Extra columns"
                    )

                o = validate_offer(row)

                if o.offer_id in seen:
                    raise OfferValidationError(
                        "Duplicate ID"
                    )

                seen.add(o.offer_id)
                valid.append(o)

            except (
                OfferValidationError,
                ValueError,
                TypeError
            ) as e:

                rejected.append(
                    (
                        line,
                        row.get("offer_id", "?"),
                        str(e)
                    )
                )

                logging.warning(
                    "Row %s (%s): %s",
                    line,
                    row.get("offer_id", "?"),
                    e
                )

    return valid, rejected
