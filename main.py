import logging
import sqlite3
import sys

from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from busbidder.booking import Booker

from busbidder.market import (
    explain,
    filter_offers,
    load_data,
    load_profiles,
    rank_offers
)

from busbidder.models import (
    BookingError,
    DataError,
    Request,
    Weights
)


ROOT = Path(__file__).resolve().parent


def ask(msg, conv=str, default=None):
    while True:
        txt = input(msg).strip()

        if not txt and default is not None:
            return default

        try:
            return conv(txt)

        except (ValueError, InvalidOperation):
            print(
                "Invalid value. Try again."
            )


def optional(msg, conv):
    while True:
        txt = input(
            msg + " (blank for none): "
        ).strip()

        if not txt:
            return None

        try:
            return conv(txt)

        except (ValueError, InvalidOperation):
            print(
                "Invalid value. Try again."
            )


def yesno(msg):
    while True:
        val = input(
            msg + " (y/n): "
        ).strip().lower()

        if val in ("y", "yes"):
            return True

        if val in ("n", "no"):
            return False

        print(
            "Please enter y or n."
        )


def get_request(dsts):
    names = sorted(dsts)

    print(
        "\nDestinations from Madrid:"
    )

    for i, name in enumerate(names, 1):
        print(
            f"{i:2}. {name}"
        )

    while True:
        n = ask(
            "Destination number: ",
            int
        )

        if 1 <= n <= len(names):
            break

        print(
            "Choose a destination from the list."
        )

    while True:
        try:
            return Request(
                destination=names[n - 1],

                start=ask(
                    "First date (YYYY-MM-DD): ",
                    date.fromisoformat
                ),

                end=ask(
                    "Last date (YYYY-MM-DD): ",
                    date.fromisoformat
                ),

                budget=optional(
                    "Maximum price (EUR)",
                    Decimal
                ),

                preferred=optional(
                    "Preferred time (HH:MM)",
                    time.fromisoformat
                ),

                max_transfers=optional(
                    "Maximum transfers",
                    int
                ),

                luggage=ask(
                    "Required luggage items [0]: ",
                    int,
                    0
                ),

                max_minutes=optional(
                    "Maximum duration (minutes)",
                    int
                ),

                changeable=yesno(
                    "Must be changeable?"
                ),

                refundable=yesno(
                    "Must be refundable?"
                ),

                seats=ask(
                    "Seats needed [1]: ",
                    int,
                    1
                )
            )

        except DataError as err:
            print(
                f"Invalid request: {err}. "
                "Please enter it again."
            )


def get_weights(profiles):
    names = list(profiles)

    print(
        "\nTraveller profiles:"
    )

    for i, name in enumerate(names, 1):
        w = profiles[name]

        print(
            f"{i}. {name}: "
            f"price {w.price}%, "
            f"duration {w.duration}%, "
            f"time {w.time}%, "
            f"flexibility {w.flexibility}%"
        )

    print(
        f"{len(names) + 1}. Custom weights"
    )

    while True:
        n = ask(
            "Profile number: ",
            int
        )

        if 1 <= n <= len(names):
            return profiles[names[n - 1]]

        if n == len(names) + 1:
            try:
                return Weights(
                    ask("Price %: ", float),
                    ask("Duration %: ", float),
                    ask("Departure time %: ", float),
                    ask("Flexibility %: ", float)
                )

            except DataError as err:
                print(err)

        else:
            print(
                "Invalid profile number."
            )


def show(rank, companies):
    print(
        "\nScores are out of 100; "
        "highest total ranks first."
    )

    print(
        "Hard requirements are checked "
        "BEFORE these scores."
    )

    for i, r in enumerate(rank, 1):
        off = r.offer
        p = r.points

        print(
            f"\n{i}. {companies[off.company].name} "
            f"| {off.id} | Total: {r.total:.1f}"
        )

        print(
            f"   {off.depart:%Y-%m-%d %H:%M} "
            f"to {off.arrive:%Y-%m-%d %H:%M} "
            f"| EUR {off.price:.2f} "
            f"| {off.duration} min "
            f"| {off.transfers} transfers "
            f"| {off.seats} seats "
            f"| {off.luggage} luggage "
            f"| rating {off.rating:.1f}/5"
        )

        print(
            f"   Changeable: {off.changeable} "
            f"| Refundable: {off.refundable}"
        )

        print(
            f"   Price {p['price']:.1f} "
            f"| Duration {p['duration']:.1f} "
            f"| Time {p['time']:.1f} "
            f"| Flexibility {p['flexibility']:.1f}"
        )

    print(
        "\nRecommendation:",
        explain(rank, companies)
    )


def compare(offers, companies, profiles, booker, req):
    current = booker.available(offers)

    good, why = filter_offers(
        current,
        req
    )

    print(
        f"\nSame {len(good)} acceptable offers "
        "for all profiles."
    )

    if not good:
        print(
            "No matching offers. "
            "Try different travel requirements."
        )
        return

    for name, w in profiles.items():
        rank = rank_offers(
            good,
            req,
            w
        )

        print(
            f"\n=== {name} traveller ==="
        )

        print(
            f"Weights: price {w.price}%, "
            f"duration {w.duration}%, "
            f"time {w.time}%, "
            f"flexibility {w.flexibility}%"
        )

        print(
            explain(rank, companies)
        )

        for i, r in enumerate(rank[:3], 1):
            print(
                f"{i}. {companies[r.offer.company].name}: "
                f"{r.total:.1f}/100"
            )


def menu(offers, companies, dsts, profiles, booker):
    while True:
        print(
            "\n=== BusBidder Spain ==="
        )

        print(
            "1. Find, rank and book offers"
        )

        print(
            "2. Compare traveller profiles"
        )

        print(
            "3. Find an existing booking"
        )

        print(
            "0. Exit"
        )

        choice = input(
            "Choose: "
        ).strip()

        if choice == "0":
            return

        if choice == "3":
            ref = input(
                "Booking reference: "
            ).strip().upper()

            try:
                b = booker.find(ref)

                if b:
                    print(b)
                else:
                    print(
                        "No booking found."
                    )

            except BookingError as err:
                print(err)

            continue

        if choice not in ("1", "2"):
            print(
                "Invalid option."
            )
            continue

        req = get_request(dsts)

        if choice == "2":
            compare(
                offers,
                companies,
                profiles,
                booker,
                req
            )
            continue

        w = get_weights(profiles)

        current = booker.available(offers)

        good, bad = filter_offers(
            current,
            req
        )

        print(
            f"\nAcceptable offers: "
            f"{len(good)} / {len(current)}"
        )

        print(
            "Hard-constraint rejections "
            f"(may overlap): {dict(bad)}"
        )

        if not good:
            print(
                "No matching offers. "
                "Change the requirements."
            )
            continue

        rank = rank_offers(
            good,
            req,
            w
        )

        show(
            rank,
            companies
        )

        if not yesno(
            "Book one of these offers?"
        ):
            continue

        n = ask(
            "Rank number (0 to cancel): ",
            int
        )

        if n == 0:
            continue

        if not 1 <= n <= len(rank):
            print(
                "Invalid rank number."
            )
            continue

        try:
            name = ask(
                "Passenger name: "
            )

            b = booker.book(
                rank[n - 1].offer,
                name,
                req.seats
            )

            print(
                "\n=== Booking confirmation "
                "(simulated payment) ==="
            )

            for k, v in b.items():
                print(
                    f"{k}: {v}"
                )

            print(
                "No payment details were collected."
            )

        except BookingError as err:
            print(
                f"Booking failed: {err}"
            )


def main():
    (ROOT / "logs").mkdir(
        exist_ok=True
    )

    logging.basicConfig(
        filename=ROOT / "logs" / "busbidder.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    try:
        companies, dsts, offers, bad = load_data(
            ROOT / "data"
        )

        profiles = load_profiles(
            ROOT / "data" / "profiles.json"
        )

        booker = Booker(
            ROOT / "output" / "bookings.sqlite3",
            offers
        )

        print(
            f"Loaded {len(offers)} valid offers; "
            f"rejected {bad} invalid rows."
        )

        print(
            f"Companies: {len(companies)}; "
            f"destinations: {len(dsts)}"
        )

        if "--compare" in sys.argv:
            req = Request(
                "Malaga",
                date(2026, 11, 12),
                date(2026, 11, 12),
                preferred=time(9),
                max_transfers=2,
                luggage=1
            )

            compare(
                offers,
                companies,
                profiles,
                booker,
                req
            )

        else:
            menu(
                offers,
                companies,
                dsts,
                profiles,
                booker
            )

    except (
        DataError,
        sqlite3.Error,
        OSError
    ) as err:

        logging.exception(
            "Application failed"
        )

        print(
            f"Error: {err}"
        )


if __name__ == "__main__":
    main()