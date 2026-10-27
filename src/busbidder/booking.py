import logging
import re
import secrets
import sqlite3

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime


REF = re.compile(
    r"BBS-\d{8}-[A-F0-9]{8}$"
)


from .models import BookingError


class Booker:

    def __init__(self, path, offers):
        self.path = path

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.db() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS seats (
                    id TEXT PRIMARY KEY,
                    qty INTEGER NOT NULL CHECK (qty >= 0)
                )
                """
            )

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    ref TEXT PRIMARY KEY,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    changeable INTEGER NOT NULL,
                    refundable INTEGER NOT NULL,
                    date TEXT NOT NULL
                )
                """
            )

            db.executemany(
                "INSERT OR IGNORE INTO seats VALUES (?, ?)",
                [
                    (off.id, off.seats)
                    for off in offers
                ]
            )

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row

        try:
            with db:
                yield db

        finally:
            db.close()

    def available(self, offers):
        with self.db() as db:
            cur = {
                row["id"]: row["qty"]
                for row in db.execute(
                    "SELECT id, qty FROM seats"
                )
            }

        return [
            replace(
                off,
                seats=cur[off.id]
            )
            for off in offers
        ]

    def book(self, off, name, qty):
        name = name.strip()

        if (
            not name
            or len(name) > 80
            or not isinstance(qty, int)
            or isinstance(qty, bool)
            or qty < 1
        ):
            raise BookingError(
                "Invalid passenger name or seat count."
            )

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        ref = (
            f"BBS-{datetime.now():%Y%m%d}-"
            f"{secrets.token_hex(4).upper()}"
        )

        total = str(
            off.price * qty
        )

        try:
            with self.db() as db:
                db.execute(
                    "BEGIN IMMEDIATE"
                )

                cur = db.execute(
                    """
                    UPDATE seats
                    SET qty = qty - ?
                    WHERE id = ?
                    AND qty >= ?
                    """,
                    (qty, off.id, qty)
                )

                if cur.rowcount != 1:
                    raise BookingError(
                        "Not enough seats available."
                    )

                db.execute(
                    """
                    INSERT INTO bookings
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ref,
                        off.id,
                        name,
                        qty,
                        total,
                        int(off.changeable),
                        int(off.refundable),
                        now
                    )
                )

        except sqlite3.Error as err:
            raise BookingError(
                f"Could not save booking: {err}"
            ) from err

        logging.info(
            "Booked %s, offer %s, seats %d",
            ref,
            off.id,
            qty
        )

        return self.find(ref)

    def find(self, ref):
        if not REF.fullmatch(ref):
            raise BookingError(
                "Invalid booking reference."
            )

        with self.db() as db:
            row = db.execute(
                """
                SELECT * FROM bookings
                WHERE ref = ?
                """,
                (ref,)
            ).fetchone()

        if row:
            return dict(row)

        return None