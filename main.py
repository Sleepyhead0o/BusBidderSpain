
import logging

from pathlib import Path

from booking import BookingManager, BookingError
from data_manager import load_offers
from requests import (
    display_requests,
    select_request,
    RequestValidationError
)
from ranking import (
    display_profiles,
    select_profile,
    filter_offers,
    rank_offers,
    explain
)


ROOT = Path(__file__).parent
DATA = ROOT / "data" / "offers.csv"
OUT = ROOT / "output"


def display_request(name, req, profile):

    print("\n=== Selected Request ===")
    print("Request:", name)
    print("Profile:", profile)
    print("Route: Madrid to", req.dest)
    print("Travel period:", req.startD, "-", req.endD)
    print("Budget:", req.max_p)
    print("Max transfers:", req.max_tr)
    print("Luggage:", req.min_lug)
    print("Max duration:", req.max_dur)
    print("Changeable:", req.req_ch)
    print("Refundable:", req.req_ref)
    print("Preferred time:", req.pref_t)
    print("Seats:", req.seats)


def display_rankings(ranked, w, seats):

    if not ranked:
        print("\nNo matching offers.")
        return

    print("\n=== Ranked Offers ===")

    print(
        f"Weights: Price {w.price:.0%}, "
        f"Duration {w.duration:.0%}, "
        f"Departure time {w.time:.0%}, "
        f"Ticket flexibility {w.flexibility:.0%}"
    )

    print(
        f"\n{'#':<4}{'Company':<19}{'ID':<10}"
        f"{'Departure':<19}{'EUR':>8}"
        f"{'Min':>7}{'Score':>9}"
    )
    print("-" * 76)

    
    
    print("\n=== Available Bus Offers Ranked from Best to Worst ===")

    for i, r in enumerate(ranked, 1):
        o = r.offer

        print(
            f"\n{i}. {o.company} (Offer ID: {o.offer_id})"
            f"\n   Departure: {o.departure:%Y-%m-%d at %H:%M}"
            f"\n   Ticket price: EUR {o.price_eur:.2f}"
            f"\n   Journey duration: {o.duration_minutes} minutes"
            f"\n   Overall ranking score: {r.total_score:.1f}/100"
            f"\n"
            f"\n   Individual criteria scores:"
            f"\n   - Ticket price: {r.price_score:.1f}/100"
            f"\n   - Journey duration: {r.duration_score:.1f}/100"
            f"\n   - Preferred departure time: {r.time_score:.1f}/100"
            f"\n   - Ticket changes and refunds: {r.flexibility_score:.1f}/100"
        )


    best = ranked[0]

    print("\n=== Recommendation ===")
    print("Company:", best.offer.company)
    print("Offer ID:", best.offer.offer_id)
    print(
        "Total price: EUR",
        f"{best.offer.price_eur * seats:.2f}"
    )
    print("Score:", f"{best.total_score:.2f}/100")
    print(explain(best, ranked[1:]))

    print(
        "\nRecommendation is based on the selected "
        "requirements and weights."
    )


def create_booking(mgr, ranked, req):

    ans = input("\nBook an offer? (y/n): ").strip().lower()

    if ans != "y":
        return

    val = input("Ranking number: ").strip()

    if not val.isdigit():
        raise BookingError("Invalid ranking number")

    idx = int(val)

    if not 1 <= idx <= len(ranked):
        raise BookingError("Ranking number out of range")

    name = input("Traveller name: ").strip()

    b = mgr.book(
        ranked[idx - 1].offer,
        req.seats,
        name
    )

    print("\n=== Booking Confirmation ===")

    for key in (
        "reference", "traveller", "company",
        "destination", "departure", "seats",
        "total_price_eur", "changeable",
        "refundable", "payment_status"
    ):
        print(f"{key}: {b[key]}")


def main():

    OUT.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=OUT / "busbidder.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    print("=== BusBidder Spain ===")

    try:
        offers, rejected = load_offers(DATA)

    except (OSError, ValueError) as e:
        print("Dataset error:", e)
        return

    print("Valid records:", len(offers))
    print("Rejected records:", len(rejected))
    print(
        "Available offers:",
        sum(o.available_seats > 0 for o in offers)
    )

    mgr = BookingManager(OUT / "bookings.json")

    while True:

        try:
            display_requests()

            n = input("\nSelect request: ").strip()

            if n == "0":
                break

            name, req = select_request(n)

            display_profiles()

            n = input("\nSelect profile: ").strip()

            profile, w = select_profile(n)

            display_request(name, req, profile)

            remaining = mgr.remaining(offers)

            valid = filter_offers(
                offers, req, remaining
            )

            print("\nMatching offers:", len(valid))

            ranked = rank_offers(
                valid, w, req.pref_t
            )

            display_rankings(
                ranked, w, req.seats
            )

            if ranked:
                create_booking(mgr, ranked, req)

        except (
            RequestValidationError,
            BookingError,
            ValueError
        ) as e:

            print("\nError:", e)
            logging.warning(
                "Application error: %s", e
            )

        except (KeyboardInterrupt, EOFError):
            print("\nProgram interrupted.")
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
