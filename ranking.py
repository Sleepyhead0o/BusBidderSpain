
from models import Weights, RankedOffer


PROFILES = {
    "1": {
        "name": "Budget Traveller",
        "weights": Weights(0.65, 0.15, 0.10, 0.10)
    },
    "2": {
        "name": "Business Traveller",
        "weights": Weights(0.15, 0.40, 0.30, 0.15)
    },
    "3": {
        "name": "Flexible Tourist",
        "weights": Weights(0.15, 0.15, 0.10, 0.60)
    }
}


def display_profiles():
    print("\n=== Traveller Profiles ===")

    for n, p in PROFILES.items():
        print(f"{n}. {p['name']}")


def select_profile(n):
    if n not in PROFILES:
        raise ValueError("Invalid profile")

    p = PROFILES[n]
    return p["name"], p["weights"]


def filter_offers(offers, req, remaining=None):

    if remaining is None:
        remaining = {}

    valid = []

    for o in offers:

        if o.destination != req.dest:
            continue

        if not (
            req.startD <= o.departure.date() <= req.endD
        ):
            continue

        avail = remaining.get(
            o.offer_id, o.available_seats
        )

        if avail < req.seats:
            continue

        if req.max_p is not None:
            if o.price_eur * req.seats > req.max_p:
                continue

        if req.max_tr is not None:
            if o.transfers > req.max_tr:
                continue

        if o.luggage_bags < req.min_lug:
            continue

        if req.max_dur is not None:
            if o.duration_minutes > req.max_dur:
                continue

        if req.req_ch and not o.changeable:
            continue

        if req.req_ref and not o.refundable:
            continue

        valid.append(o)

    return valid


def normalize_lower(v, low, high):

    if low == high:
        return 100.0

    return 100 * (high - v) / (high - low)


def departure_score(dep, pref):

    a = dep.hour * 60 + dep.minute
    b = pref.hour * 60 + pref.minute

    diff = abs(a - b)
    diff = min(diff, 1440 - diff)

    return 100 * (1 - diff / 720)


def flexibility_score(o):
    return 50 * o.changeable + 50 * o.refundable


def rank_offers(offers, w, pref):

    if not offers:
        return []

    prices = [o.price_eur for o in offers]
    durs = [o.duration_minutes for o in offers]

    pmin, pmax = min(prices), max(prices)
    dmin, dmax = min(durs), max(durs)

    ranked = []

    for o in offers:

        p = normalize_lower(
            o.price_eur, pmin, pmax
        )

        d = normalize_lower(
            o.duration_minutes, dmin, dmax
        )

        t = departure_score(
            o.departure.time(), pref
        )

        f = flexibility_score(o)

        score = (
            w.price * p
            + w.duration * d
            + w.time * t
            + w.flexibility * f
        )

        ranked.append(
            RankedOffer(o, p, d, t, f, score)
        )

    ranked.sort(
        key=lambda r: (
            -r.total_score,
            r.offer.price_eur,
            r.offer.duration_minutes,
            r.offer.offer_id
        )
    )

    return ranked


def explain(best, others):

    o = best.offer
    pros = []
    cons = []

    if best.price_score >= 80:
        pros.append("competitive price")

    if best.duration_score >= 80:
        pros.append("short journey")

    if best.time_score >= 80:
        pros.append("convenient departure")

    if o.transfers == 0:
        pros.append("direct journey")

    if o.changeable:
        pros.append("changeable ticket")

    if o.refundable:
        pros.append("refundable ticket")

    if any(
        r.offer.price_eur < o.price_eur
        for r in others
    ):
        cons.append("some alternatives are cheaper")

    if any(
        r.offer.duration_minutes < o.duration_minutes
        for r in others
    ):
        cons.append("some alternatives are faster")

    if not o.refundable:
        cons.append("non-refundable ticket")

    return (
        "Advantages: "
        + ", ".join(pros or ["good overall score"])
        + "\nDisadvantages: "
        + ", ".join(cons or ["no major disadvantage"])
    )
