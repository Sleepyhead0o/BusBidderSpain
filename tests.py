import tempfile
import unittest

from dataclasses import replace
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from data_generator import DATA, generate

from busbidder.booking import Booker

from busbidder.market import (
    filter_offers,
    get_bounds,
    get_time_bounds,
    time_gap,
    load_data,
    load_profiles,
    parse_offer,
    rank_offers,
    reasons
)

from busbidder.models import (
    BookingError,
    DataError,
    Request,
    Weights
)


class TestBusBidder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        generate()

        cls.companies, cls.dsts, cls.offers, cls.bad = load_data(
            DATA
        )

        cls.bounds = get_bounds(cls.offers)

        cls.profiles = load_profiles(
            DATA / "profiles.json"
        )

        cls.req = Request(
            "Malaga",
            date(2026, 11, 12),
            date(2026, 11, 12),
            preferred=time(9),
            max_transfers=2,
            luggage=1
        )

        cls.time_bounds = get_time_bounds(cls.offers, cls.req.preferred)

        cls.good, _ = filter_offers(
            cls.offers,
            cls.req
        )

    def test_companies_and_destinations(self):
        self.assertEqual(
            len(self.companies),
            5
        )

        self.assertEqual(
            len(self.dsts),
            15
        )

    def test_all_company_destination_pairs(self):
        combos = {
            (off.company, off.destination)
            for off in self.offers
        }

        self.assertEqual(
            len(combos),
            75
        )

    def test_invalid_records_rejected(self):
        self.assertEqual(
            len(self.offers),
            152
        )

        self.assertEqual(
            self.bad,
            10
        )

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DataError):
                load_data(
                    Path(tmp)
                )

    def test_invalid_price(self):
        row = {
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
            parse_offer(
                row,
                self.companies,
                self.dsts
            )

    def test_all_hard_constraints(self):
        off = self.good[0]

        req = replace(
            self.req,
            budget=Decimal("1"),
            max_transfers=0,
            luggage=10,
            max_minutes=1,
            seats=100,
            changeable=True,
            refundable=True
        )

        bad = reasons(
            off,
            req
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
            }.issubset(bad)
        )

    def test_missing_offer_value(self):
        row = {
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
            parse_offer(
                row,
                self.companies,
                self.dsts
            )

    def test_budget_boundary(self):
        off = self.good[0]

        req = replace(
            self.req,
            budget=off.price
        )

        good, _ = filter_offers(
            [off],
            req
        )

        self.assertEqual(
            good,
            [off]
        )

    def test_no_seats(self):
        off = replace(
            self.good[0],
            seats=0
        )

        good, _ = filter_offers(
            [off],
            self.req
        )

        self.assertEqual(
            good,
            []
        )

    def test_hard_changeability(self):
        off = next(
            off for off in self.good
            if not off.changeable
        )

        req = replace(
            self.req,
            changeable=True
        )

        good, _ = filter_offers(
            [off],
            req
        )

        self.assertEqual(
            good,
            []
        )

    def test_invalid_weights(self):
        with self.assertRaises(DataError):
            Weights(
                40, 20, 20, 10
            )

    def test_invalid_request(self):
        with self.assertRaises(DataError):
            replace(
                self.req,
                start=date(2026, 11, 13)
            )

    def test_ranking_reproducible(self):
        w = self.profiles["Business"]

        a = rank_offers(
            self.good,
            self.req,
            w,
            self.bounds,
            self.time_bounds
        )

        b = rank_offers(
            list(reversed(self.good)),
            self.req,
            w,
            self.bounds,
            self.time_bounds
        )

        self.assertEqual(
            a,
            b
        )

        self.assertTrue(
            all(
                0 <= r.total <= 100
                for r in a
            )
        )

    def test_global_min_max(self):
        self.assertEqual(
            self.bounds["price"],
            (
                min(float(off.price) for off in self.offers),
                max(float(off.price) for off in self.offers)
            )
        )

        self.assertEqual(
            self.bounds["duration"],
            (
                min(off.duration for off in self.offers),
                max(off.duration for off in self.offers)
            )
        )

    def test_scores_do_not_depend_on_filtered_set(self):
        w = Weights(50, 50, 0, 0)
        off = self.good[0]

        alone = rank_offers(
            [off], self.req, w, self.bounds, self.time_bounds
        )[0]

        together = next(
            r for r in rank_offers(
                self.good, self.req, w, self.bounds, self.time_bounds
            )
            if r.offer.id == off.id
        )

        self.assertEqual(alone.points, together.points)
        self.assertAlmostEqual(alone.total, together.total)

    def test_equal_bounds_are_handled(self):
        off = self.good[0]
        bounds = get_bounds([off])
        w = Weights(50, 50, 0, 0)

        r = rank_offers(
            [off], self.req, w, bounds,
            get_time_bounds([off], self.req.preferred)
        )[0]
        self.assertEqual(r.points["price"], 100.0)
        self.assertEqual(r.points["duration"], 100.0)

    def test_time_bounds_use_complete_dataset(self):
        gaps = [time_gap(off, self.req.preferred) for off in self.offers]
        self.assertEqual(self.time_bounds, (min(gaps), max(gaps)))

    def test_time_score_does_not_depend_on_filtered_offers(self):
        w = Weights(0, 0, 100, 0)
        off = self.good[0]
        alone = rank_offers(
            [off], self.req, w, self.bounds, self.time_bounds
        )[0]
        together = next(
            r for r in rank_offers(
                self.good, self.req, w, self.bounds, self.time_bounds
            ) if r.offer.id == off.id
        )
        self.assertEqual(alone.points["time"], together.points["time"])

    def test_preferred_time_changes_bounds(self):
        other = time(22, 0)
        other_bounds = get_time_bounds(self.offers, other)
        self.assertNotEqual(self.time_bounds, other_bounds)

    def test_no_preferred_time_uses_neutral_score(self):
        req = replace(self.req, preferred=None)
        self.assertIsNone(get_time_bounds(self.offers, req.preferred))
        w = Weights(0, 0, 100, 0)
        rank = rank_offers(self.good, req, w, self.bounds, None)
        self.assertTrue(all(r.points["time"] == 50.0 for r in rank))

    def test_equal_time_gaps_receive_same_score(self):
        off = self.good[0]
        time_bounds = get_time_bounds([off], self.req.preferred)
        w = Weights(0, 0, 100, 0)
        rank = rank_offers([off], self.req, w, self.bounds, time_bounds)
        self.assertEqual(rank[0].points["time"], 100.0)

    def test_profiles_can_differ(self):
        winners = {
            name: rank_offers(
                self.good,
                self.req,
                w,
                self.bounds,
                self.time_bounds
            )[0].offer.company

            for name, w in self.profiles.items()
        }

        self.assertEqual(
            len(set(winners.values())),
            3
        )

    def test_booking_persists_and_uses_seats(self):
        with tempfile.TemporaryDirectory() as tmp:
            off = replace(
                self.good[0],
                seats=2
            )

            path = Path(tmp) / "book.sqlite3"

            svc = Booker(
                path,
                [off]
            )

            b = svc.book(
                off,
                "Alex",
                1
            )

            self.assertEqual(
                b["qty"],
                1
            )

            self.assertEqual(
                svc.available([off])[0].seats,
                1
            )

            svc2 = Booker(
                path,
                [off]
            )

            self.assertEqual(
                svc2.available([off])[0].seats,
                1
            )

            self.assertEqual(
                svc2.find(b["ref"]),
                b
            )

            self.assertEqual(
                b["changeable"],
                int(off.changeable)
            )

    def test_booking_prevents_overbooking(self):
        with tempfile.TemporaryDirectory() as tmp:
            off = replace(
                self.good[0],
                seats=1
            )

            svc = Booker(
                Path(tmp) / "book.sqlite3",
                [off]
            )

            svc.book(
                off,
                "Alex",
                1
            )

            with self.assertRaises(BookingError):
                svc.book(
                    off,
                    "Pat",
                    1
                )

    def test_invalid_booking_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = Booker(
                Path(tmp) / "book.sqlite3",
                [self.good[0]]
            )

            with self.assertRaises(BookingError):
                svc.find(
                    "invalid"
                )


if __name__ == "__main__":
    unittest.main()