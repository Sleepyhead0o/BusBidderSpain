
import logging
import re
import secrets
import sqlite3

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime


REF_REG = re.compile(
    r"BBS-\d{8}-[A-F0-9]{8}$"
)


from .models import BookingError


class Booker:

    def __init__(self, sti, tilbud):
        self.sti = sti

        sti.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self.apne_db() as kobling:
            kobling.execute(
                """
                CREATE TABLE IF NOT EXISTS seats (
                    id TEXT PRIMARY KEY,
                    qty INTEGER NOT NULL CHECK (qty >= 0)
                )
                """
            )

            kobling.execute(
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

            kobling.executemany(
                "INSERT OR IGNORE INTO seats VALUES (?, ?)",
                [
                    (tur.id, tur.seats)
                    for tur in tilbud
                ]
            )

    @contextmanager
    def apne_db(self):
        kobling = sqlite3.connect(self.sti)
        kobling.row_factory = sqlite3.Row

        try:
            with kobling:
                yield kobling

        finally:
            kobling.close()

    def ledige_seter(self, tilbud):     # seat availability 
        with self.apne_db() as kobling:
            treff = {
                rad["id"]: rad["qty"]
                for rad in kobling.execute(
                    "SELECT id, qty FROM seats"
                )
            }

        return [
            replace(
                tur,
                seats=treff[tur.id]
            )
            for tur in tilbud
        ]

    def lag_bestilling(self, tur, navn, antall):        # create booking
        navn = navn.strip()

        if (
            not navn
            or len(navn) > 80
            or not isinstance(antall, int)
            or isinstance(antall, bool)
            or antall < 1
        ):
            raise BookingError(
                "Invalid passenger name or seat count."
            )

        naa = datetime.now().isoformat(
            timespec="seconds"
        )

        kode = (
            f"BBS-{datetime.now():%Y%m%d}-"
            f"{secrets.token_hex(4).upper()}"
        )

        belop = str(
            tur.price * antall
        )

        try:
            with self.apne_db() as kobling:
                kobling.execute(
                    "BEGIN IMMEDIATE"
                )

                treff = kobling.execute(
                    """
                    UPDATE seats
                    SET qty = qty - ?
                    WHERE id = ?
                    AND qty >= ?
                    """,
                    (antall, tur.id, antall)
                )

                if treff.rowcount != 1:
                    raise BookingError(
                        "Not enough seats available."
                    )

                kobling.execute(
                    """
                    INSERT INTO bookings
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        kode,
                        tur.id,
                        navn,
                        antall,
                        belop,
                        int(tur.changeable),
                        int(tur.refundable),
                        naa
                    )
                )

        except sqlite3.Error as err:
            raise BookingError(
                f"Could not save booking: {err}"
            ) from err

        logging.info(
            "Booked %s, offer %s, seats %d",
            kode,
            tur.id,
            antall
        )

        return self.finn_bestilling(kode)       # gets new booking details with referance

    def finn_bestilling(self, kode):            # find booking
        if not REF_REG.fullmatch(kode):
            raise BookingError(
                "Invalid booking reference"
            )

        with self.apne_db() as kobling:
            rad = kobling.execute(
                """
                SELECT * FROM bookings
                WHERE ref = ?
                """,
                (kode,)
            ).fetchone()

        if rad:     # row
            return dict(rad)

        return None
