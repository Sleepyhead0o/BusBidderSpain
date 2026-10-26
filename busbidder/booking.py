
import json
import logging
import os

from datetime import datetime
from pathlib import Path
from uuid import uuid4


class BookingError(ValueError):
    pass


class BookingManager:

    def __init__(self, path):
        self.path = Path(path)

    def load_bookings(self):

        if not self.path.exists():
            return []

        try:
            with self.path.open(encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise BookingError("Invalid bookings file")

            for b in data:
                if (
                    not isinstance(b, dict)
                    or not isinstance(b.get("offer_id"), str)
                    or not isinstance(b.get("ref"), str)
                    or type(b.get("seats")) is not int
                    or b["seats"] <= 0
                ):
                    raise BookingError("Invalid booking record")

            return data

        except (OSError, ValueError, TypeError) as e:
            raise BookingError("Cannot load bookings") from e

    def remaining(self, offers):

        counts = {
            o.offer_id: o.available_seats
            for o in offers
        }

        for b in self.load_bookings():
            oid = b["offer_id"]

            if oid in counts:
                counts[oid] -= b["seats"]

        return counts

    def book(self, o, seats, name):

        if type(seats) is not int or seats <= 0:
            raise BookingError("Invalid seat count")

        if not isinstance(name, str) or not name.strip():
            raise BookingError("Invalid traveller name")

        bookings = self.load_bookings()

        used = sum(
            b["seats"]
            for b in bookings
            if b["offer_id"] == o.offer_id
        )

        if o.available_seats - used < seats:
            raise BookingError("Not enough seats")

        refs = {
            b["ref"]
            for b in bookings
        }

        ref = "BB-" + uuid4().hex[:12].upper()

        while ref in refs:
            ref = "BB-" + uuid4().hex[:12].upper()

        b = {
            "ref": ref,
            "offer_id": o.offer_id,
            "name": name.strip(),
            "comp": o.company,
            "orig": o.origin,
            "dest": o.destination,
            "dep": o.departure.isoformat(
                timespec="minutes"
            ),
            "arriv": o.arrival.isoformat(
                timespec="minutes"
            ),
            "seats": seats,
            "price": round(
                o.price_eur * seats, 2
            ),
            "ch": o.changeable,
            "refund": o.refundable,
            "payment": "SIMULATED",
            "created": datetime.now().isoformat(
                timespec="seconds"
            )
        }

        bookings.append(b)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        tmp = self.path.with_name(
            self.path.name + ".tmp"
        )

        try:
            tmp.write_text(
                json.dumps(bookings, indent=4),
                encoding="utf-8"
            )

            os.replace(tmp, self.path)

        except OSError as e:
            raise BookingError("Cannot save booking") from e

        logging.info(
            "Booking %s: offer %s, seats %s",
            ref, o.offer_id, seats
        )

        return b
