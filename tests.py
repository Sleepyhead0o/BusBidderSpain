
import tempfile
import unittest

from dataclasses import replace
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from data_generator import DATAMAPPE, lag_data

from busbidder.booking import Booker

from busbidder.market import (
    finn_tilbud,
    poenggrenser,
    tidsgrenser,
    tidsavstand,
    last_marked,
    last_profiler,
    lag_tilbud,
    ranger_tilbud,
    sjekk_tilbud
)

from busbidder.models import (
    BookingError,
    DataError,
    Request,
    Weights
)


class TestBusBidder(unittest.TestCase):

    # set up test data
    @classmethod
    def setUpClass(cls):
        lag_data()

        cls.selskaper, cls.reisemaal, cls.tilbud, cls.avvist = last_marked(
            DATAMAPPE
        )

        cls.grenser = poenggrenser(cls.tilbud)

        cls.profiler = last_profiler(
            DATAMAPPE / "profiles.json"
        )

        cls.krav = Request(
            "Malaga",
            date(2026, 11, 12),
            date(2026, 11, 12),
            preferred=time(9),
            max_transfers=2,
            luggage=1
        )

        cls.tid_grenser = tidsgrenser(
            cls.tilbud, cls.krav.preferred
        )

        cls.gyldige, _ = finn_tilbud(
            cls.tilbud,
            cls.krav
        )

    # check companies and destinations
    def test_selskaper_og_reisemaal(self):
        self.assertEqual(
            len(self.selskaper),
            5
        )

        self.assertEqual(
            len(self.reisemaal),
            15
        )

    # check company-destination pairs
    def test_alle_selskap_maal(self):
        par = {     # pairs
            (tur.company, tur.destination)
            for tur in self.tilbud
        }

        self.assertEqual(
            len(par),
            75
        )

    # Check invalid offers
    def test_ugyldige_tilbud(self):
        self.assertEqual(
            len(self.tilbud),
            152
        )

        self.assertEqual(
            self.avvist,
            10
        )

    # check missing data
    def test_mangler_data(self):
        with tempfile.TemporaryDirectory() as mappe:    # folder
            with self.assertRaises(DataError):
                last_marked(
                    Path(mappe)
                )

    # check invalid price
    def test_ugyldig_pris(self):
        rad = {        # row
            "offer_id": "OF-9999",
            "company": "SR",
            "origin": "Madrid",
            "destination": "Malaga",
            "depart": "2026-11-12T09:00",
            "arrive": "2026-11-12T10:00",
            "minutes": "60",
            "price": "-5",
            "transfers": "0",
            "luggage": "1",
            "changeable": "true",
            "refundable": "false",
            "seats": "1",
            "rating": "4"
        }

        with self.assertRaises(DataError):
            lag_tilbud(
                rad,
                self.selskaper,
                self.reisemaal
            )

    # check all hard constraints
    def test_alle_krav(self):
        tur = self.gyldige[0]       # offer

        krav = replace(             # request
            self.krav,
            budget=Decimal("1"),
            max_transfers=0,
            luggage=10,
            max_dur=1,
            seats=100,
            changeable=True,
            refundable=True
        )

        avvist = sjekk_tilbud(       # rejection reasons
            tur,
            krav
        )

        self.assertTrue(
            {
                "budget",
                "transfers",
                "luggage",
                "duration",
                "seats",
                "changeable",
                "refundable"
            }.issubset(avvist)
        )

    # check missing offer value
    def test_manglende_verdi(self):
        rad = {        # row
            "offer_id": "OF-9999",
            "company": "SR",
            "origin": "Madrid",
            "destination": "Malaga",
            "depart": "2026-11-12T09:00",
            "arrive": "2026-11-12T10:00",
            "minutes": "60",
            "price": "",
            "transfers": "0",
            "luggage": "1",
            "changeable": "true",
            "refundable": "false",
            "seats": "1",
            "rating": "4"
        }

        with self.assertRaises(DataError):
            lag_tilbud(
                rad,
                self.selskaper,
                self.reisemaal
            )

    # check price boundary
    def test_prisgrense(self):
        tur = self.gyldige[0]       # offer

        krav = replace(
            self.krav,
            budget=tur.price
        )

        gyldige, _ = finn_tilbud(    # valid offers
            [tur],
            krav
        )

        self.assertEqual(
            gyldige,
            [tur]
        )

    # Check no available seats
    def test_ingen_seter(self):
        tur = replace(
            self.gyldige[0],
            seats=0
        )

        gyldige, _ = finn_tilbud(
            [tur],
            self.krav
        )

        self.assertEqual(
            gyldige,
            []
        )

    # Check changeable ticket requirement
    def test_krav_om_endring(self):
        tur = next(
            tur for tur in self.gyldige
            if not tur.changeable
        )

        krav = replace(
            self.krav,
            changeable=True
        )

        gyldige, _ = finn_tilbud(
            [tur],
            krav
        )

        self.assertEqual(
            gyldige,
            []
        )

    # check invalid weights
    def test_ugyldige_vekter(self):
        with self.assertRaises(DataError):
            Weights(
                40, 20, 20, 10
            )

    # check past travel date
    def test_gammel_dato_godtas(self):
        krav = Request(
            "Malaga",
            date(2026, 11, 11),
            date(2026, 11, 12)
        )

        self.assertEqual(
            krav.start,
            date(2026, 11, 11)
        )

    # check same-day travel
    def test_samme_dato_godtas(self):
        krav = Request(
            "Malaga",
            date(2026, 11, 12),
            date(2026, 11, 12)
        )

        self.assertEqual(
            krav.start,
            date(2026, 11, 12)
        )

    # check later travel date
    def test_senere_dato_godtas(self):
        krav = Request(
            "Malaga",
            date(2026, 11, 13),
            date(2026, 11, 13)
        )

        self.assertEqual(
            krav.start,
            date(2026, 11, 13)
        )

    # Check invalid date range
    def test_ugyldig_krav(self):
        with self.assertRaises(DataError):
            replace(
                self.krav,
                start=date(2026, 11, 13)
            )

    # check consistent ranking
    def test_lik_rangering(self):
        vekter = self.profiler["Business"]     # weights

        forste = ranger_tilbud(                 # first ranking
            self.gyldige,
            self.krav,
            vekter,
            self.grenser,
            self.tid_grenser
        )

        andre = ranger_tilbud(                  # second ranking
            list(reversed(self.gyldige)),
            self.krav,
            vekter,
            self.grenser,
            self.tid_grenser
        )

        self.assertEqual(
            forste,
            andre
        )

        self.assertTrue(
            all(
                0 <= res.total <= 100
                for res in forste
            )
        )

    # check global score bounds
    def test_felles_grenser(self):
        self.assertEqual(
            self.grenser["price"],
            (
                min(float(tur.price) for tur in self.tilbud),
                max(float(tur.price) for tur in self.tilbud)
            )
        )

        self.assertEqual(
            self.grenser["duration"],
            (
                min(tur.duration for tur in self.tilbud),
                max(tur.duration for tur in self.tilbud)
            )
        )

    # check scores are independent of the filtered offers
    def test_poeng_uavhengig_av_utvalg(self):
        vekter = Weights(50, 50, 0, 0)
        tur = self.gyldige[0]

        alene = ranger_tilbud(        # alone
            [tur], self.krav, vekter,
            self.grenser, self.tid_grenser
        )[0]

        sammen = next(               # together
            res for res in ranger_tilbud(
                self.gyldige, self.krav, vekter,
                self.grenser, self.tid_grenser
            )
            if res.offer.id == tur.id
        )

        self.assertEqual(alene.points, sammen.points)
        self.assertAlmostEqual(alene.total, sammen.total)

    # check equal normalization bounds
    def test_like_grenser(self):
        tur = self.gyldige[0]
        grenser = poenggrenser([tur])       # bounds
        vekter = Weights(50, 50, 0, 0)

        res = ranger_tilbud(
            [tur], self.krav, vekter,
            grenser,
            tidsgrenser([tur], self.krav.preferred)
        )[0]

        self.assertEqual(
            res.points["price"], 100.0
        )

        self.assertEqual(
            res.points["duration"], 100.0
        )

    # check time bounds use all offers
    def test_tidsgrenser_alle_tilbud(self):
        avstander = [       # time differences
            tidsavstand(tur, self.krav.preferred)
            for tur in self.tilbud
        ]

        self.assertEqual(
            self.tid_grenser,
            (min(avstander), max(avstander))
        )

    # check time scores are independent of filtered offers
    def test_tidspoeng_uavhengig_av_utvalg(self):
        vekter = Weights(0, 0, 100, 0)
        tur = self.gyldige[0]

        alene = ranger_tilbud(
            [tur], self.krav, vekter,
            self.grenser, self.tid_grenser
        )[0]

        sammen = next(
            res for res in ranger_tilbud(
                self.gyldige, self.krav, vekter,
                self.grenser, self.tid_grenser
            )
            if res.offer.id == tur.id
        )

        self.assertEqual(
            alene.points["time"],
            sammen.points["time"]
        )

    # check different preferred departure times
    def test_onsket_tid_endrer_grenser(self):
        annen = time(22, 0)        # another time
        andre_grenser = tidsgrenser(
            self.tilbud, annen
        )

        self.assertNotEqual(
            self.tid_grenser,
            andre_grenser
        )

    # check no preferred departure time
    def test_uten_onsket_tid(self):
        krav = replace(
            self.krav, preferred=None
        )

        self.assertIsNone(
            tidsgrenser(self.tilbud, krav.preferred)
        )

        vekter = Weights(0, 0, 100, 0)

        rangering = ranger_tilbud(       # ranking
            self.gyldige, krav, vekter,
            self.grenser, None
        )

        self.assertTrue(
            all(
                res.points["time"] == 50.0
                for res in rangering
            )
        )

    # check equal departure-time differences
    def test_like_tidsavstander(self):
        tur = self.gyldige[0]
        tid_grenser = tidsgrenser(       # time bounds
            [tur], self.krav.preferred
        )

        vekter = Weights(0, 0, 100, 0)

        rangering = ranger_tilbud(
            [tur], self.krav, vekter,
            self.grenser, tid_grenser
        )

        self.assertEqual(
            rangering[0].points["time"], 100.0
        )

    # check different profile recommendations
    def test_ulike_profiler(self):
        vinnere = {        # winners
            navn: ranger_tilbud(
                self.gyldige,
                self.krav,
                vekter,
                self.grenser,
                self.tid_grenser
            )[0].offer.company

            for navn, vekter in self.profiler.items()
        }

        self.assertEqual(
            len(set(vinnere.values())),
            3
        )

    # check saved booking and seat availability
    def test_bestilling_lagres(self):
        with tempfile.TemporaryDirectory() as mappe:
            tur = replace(
                self.gyldige[0],
                seats=2
            )

            sti = Path(mappe) / "book.sqlite3"    # path

            bestiller = Booker(                  # booking manager
                sti,
                [tur]
            )

            bestilling = bestiller.lag_bestilling(    # booking
                tur,
                "Alex",
                1
            )

            self.assertEqual(
                bestilling["qty"],
                1
            )

            self.assertEqual(
                bestiller.ledige_seter([tur])[0].seats,
                1
            )

            ny_bestiller = Booker(       # new booking manager
                sti,
                [tur]
            )

            self.assertEqual(
                ny_bestiller.ledige_seter([tur])[0].seats,
                1
            )

            self.assertEqual(
                ny_bestiller.finn_bestilling(bestilling["ref"]),
                bestilling
            )

            self.assertEqual(
                bestilling["changeable"],
                int(tur.changeable)
            )

    # check overbooking prevention
    def test_stopper_overbooking(self):
        with tempfile.TemporaryDirectory() as mappe:
            tur = replace(
                self.gyldige[0],
                seats=1
            )

            bestiller = Booker(
                Path(mappe) / "book.sqlite3",
                [tur]
            )

            bestiller.lag_bestilling(
                tur,
                "Alex",
                1
            )

            with self.assertRaises(BookingError):
                bestiller.lag_bestilling(
                    tur,
                    "Pat",
                    1
                )

    # check invalid booking reference
    def test_ugyldig_bestillingskode(self):
        with tempfile.TemporaryDirectory() as mappe:
            bestiller = Booker(
                Path(mappe) / "book.sqlite3",
                [self.gyldige[0]]
            )

            with self.assertRaises(BookingError):
                bestiller.finn_bestilling(
                    "invalid"
                )


if __name__ == "__main__":
    unittest.main()
