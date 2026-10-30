import csv
import json
import logging
import math
import re

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Company, DataError, Offer, Score, Weights


LOG = logging.getLogger(__name__)

ID_RULE = re.compile(r"OF-\d{4,6}$")


def rows(path, needed):
    try:
        with path.open(
            newline="",
            encoding="utf-8-sig"
        ) as f:

            rd = csv.DictReader(f)

            if not rd.fieldnames:
                raise DataError(
                    f"Missing headers in {path.name}."
                )

            if not set(needed).issubset(rd.fieldnames):
                raise DataError(
                    f"Missing columns in {path.name}."
                )

            return list(rd)

    except (OSError, UnicodeError, csv.Error) as err:
        raise DataError(
            f"Cannot read {path}: {err}"
        ) from err


def number(row, key, smallest=0):
    val = (row.get(key) or "").strip()

    if not val.isdigit():
        raise DataError(
            f"Invalid {key}."
        )

    n = int(val)

    if n < smallest:
        raise DataError(
            f"Invalid {key}."
        )

    return n


def yesno(row, key):
    val = (row.get(key) or "").strip().lower()

    if val not in ("true", "false"):
        raise DataError(
            f"Invalid {key}."
        )

    return val == "true"


def parse_offer(row, companies, destinations):
    try:
        oid = (row.get("offer_id") or "").strip()
        co = (row.get("company") or "").strip()
        dst = (row.get("destination") or "").strip()

        if not ID_RULE.fullmatch(oid):
            raise DataError(
                "Invalid offer ID."
            )

        if co not in companies or dst not in destinations:
            raise DataError(
                "Unknown company or destination."
            )

        if (row.get("origin") or "").strip() != "Madrid":
            raise DataError(
                "Origin must be Madrid."
            )

        dep = datetime.fromisoformat(row["depart"])
        arr = datetime.fromisoformat(row["arrive"])

        if dep.tzinfo or arr.tzinfo or arr <= dep:
            raise DataError(
                "Invalid departure/arrival order."
            )

        mins = number(row, "minutes", 1)

        if (arr - dep).total_seconds() != mins * 60:
            raise DataError(
                "Duration does not match the times."
            )

        price = Decimal(row["price"])
        rating = float(row["rating"])

        if not price.is_finite() or price <= 0:
            raise DataError(
                "Price must be positive."
            )

        if not math.isfinite(rating) or not 1 <= rating <= 5:
            raise DataError(
                "Rating must be from 1 to 5."
            )

        eco = (row.get("emissions") or "").strip()

        if eco:
            eco = float(eco)
        else:
            eco = None

        if eco is not None:
            if not math.isfinite(eco) or eco < 0:
                raise DataError(
                    "Invalid emissions."
                )

        return Offer(
            oid,
            co,
            dst,
            dep,
            arr,
            price,
            number(row, "transfers"),
            number(row, "luggage"),
            yesno(row, "changeable"),
            yesno(row, "refundable"),
            number(row, "seats"),
            rating,
            eco
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation
    ) as err:

        raise DataError(
            f"Invalid or missing offer value: {err}"
        ) from err


def load_data(folder):
    companies = {}

    cr = rows(
        folder / "companies.csv",
        ["code", "name", "description"]
    )

    for row in cr:
        co = (row["code"] or "").strip()
        name = (row["name"] or "").strip()
        desc = (row["description"] or "").strip()

        if not co or not name or not desc or co in companies:
            raise DataError(
                "Invalid or duplicate company."
            )

        companies[co] = Company(
            co,
            name,
            desc
        )

    destinations = set()

    dr = rows(
        folder / "destinations.csv",
        ["name"]
    )

    for row in dr:
        dst = (row["name"] or "").strip()

        if not dst or dst in destinations or dst == "Madrid":
            raise DataError(
                "Invalid or duplicate destination."
            )

        destinations.add(dst)

    cols = [
        "offer_id",
        "company",
        "origin",
        "destination",
        "depart",
        "arrive",
        "minutes",
        "price",
        "transfers",
        "luggage",
        "changeable",
        "refundable",
        "seats",
        "rating"
    ]

    offers = []
    bad = []
    used = set()

    for line, row in enumerate(
        rows(folder / "offers.csv", cols),
        2
    ):
        try:
            off = parse_offer(
                row,
                companies,
                destinations
            )

            if off.id in used:
                raise DataError(
                    "Duplicate offer ID."
                )

            used.add(off.id)
            offers.append(off)

        except DataError as err:
            LOG.warning(
                "Rejected line %d: %s",
                line,
                err
            )

            bad.append({
                "line": line,
                "id": row.get("offer_id", ""),
                "reason": str(err)
            })

    out = folder.parent / "output" / "rejected.csv"
    out.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with out.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        wr = csv.DictWriter(
            f,
            ["line", "id", "reason"]
        )

        wr.writeheader()
        wr.writerows(bad)

    if not offers:
        raise DataError(
            "No valid offers were found."
        )

    return companies, destinations, offers, len(bad)


def load_profiles(path):
    try:
        with path.open(encoding="utf-8") as f:
            cfg = json.load(f)

        profiles = {
            name: Weights(**w)
            for name, w in cfg.items()
        }

        if len(profiles) < 3:
            raise DataError(
                "At least three profiles are required."
            )

        return profiles

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError
    ) as err:

        raise DataError(
            f"Cannot load profiles: {err}"
        ) from err


def reasons(off, req):
    bad = []

    if off.destination != req.destination:
        bad.append("destination")

    if not req.start <= off.day <= req.end:
        bad.append("date")

    if req.budget is not None:
        if off.price > req.budget:
            bad.append("budget")

    if off.seats < req.seats:
        bad.append("seats")

    if req.max_transfers is not None:
        if off.transfers > req.max_transfers:
            bad.append("transfers")

    if off.luggage < req.luggage:
        bad.append("luggage")

    if req.max_minutes is not None:
        if off.duration > req.max_minutes:
            bad.append("duration")

    if req.changeable and not off.changeable:
        bad.append("changeable")

    if req.refundable and not off.refundable:
        bad.append("refundable")

    return bad


def filter_offers(offers, req):
    good = []
    bad = Counter()

    for off in offers:
        why = reasons(off, req)

        if why:
            bad.update(why)
        else:
            good.append(off)

    return good, bad


def clamp(n):
    return max(
        0.0,
        min(100.0, n)
    )


def get_bounds(offers):
    # Calculate limits once from all valid, unfiltered offers.
    if not offers:
        raise DataError("No offers available for normalization.")

    return {
        "price": (
            min(float(off.price) for off in offers),
            max(float(off.price) for off in offers)
        ),
        "duration": (
            min(off.duration for off in offers),
            max(off.duration for off in offers)
        )
    }


def norm_low(value, low, high):
    # A smaller price or shorter duration receives more points.
    if low == high:
        return 100.0

    return clamp(
        100 * (high - float(value)) / (high - low)
    )


def time_gap(off, preferred):
    # Shortest circular difference on a 24-hour clock, in minutes.
    a = off.depart.hour * 60 + off.depart.minute
    b = preferred.hour * 60 + preferred.minute
    gap = abs(a - b)
    return min(gap, 1440 - gap)


def get_time_bounds(offers, preferred):
    # Calculated once per request from ALL valid (unfiltered) offers.
    if preferred is None:
        return None

    if not offers:
        raise DataError("No offers available for normalization.")

    gaps = [time_gap(off, preferred) for off in offers]
    return min(gaps), max(gaps)


def rank_offers(offers, req, w, bounds, time_bounds):
    rank = []

    p_min, p_max = bounds["price"]
    d_min, d_max = bounds["duration"]

    if req.preferred is not None and time_bounds is None:
        raise DataError("Departure-time bounds are required.")

    for off in offers:
        p = norm_low(off.price, p_min, p_max)
        d = norm_low(off.duration, d_min, d_max)

        if req.preferred is None:
            t = 50.0
        else:
            dt = time_gap(off, req.preferred)
            t = norm_low(dt, *time_bounds)

        f = 50.0 * (
            int(off.changeable)
            + int(off.refundable)
        )

        pts = {
            "price": p,
            "duration": d,
            "time": t,
            "flexibility": f
        }

        total = sum(
            pts[name] * getattr(w, name) / 100
            for name in pts
        )

        rank.append(
            Score(off, pts, total)
        )

    return sorted(
        rank,
        key=lambda r: (
            -r.total,
            r.offer.price,
            r.offer.duration,
            r.offer.id
        )
    )


def explain(rank, companies):
    if not rank:
        return "No matching offers."

    top = rank[0]
    off = top.offer

    pros = []
    cons = []

    if off.transfers == 0:
        pros.append("direct journey")

    if top.points["time"] >= 85:
        pros.append("relatively convenient departure")

    if off.changeable and off.refundable:
        pros.append(
            "flexible and refundable fare"
        )

    low = min(
        r.offer.price
        for r in rank
    )

    fast = min(
        r.offer.duration
        for r in rank
    )

    if off.price > low:
        cons.append(
            "not the cheapest offer"
        )

    if off.duration > fast:
        cons.append(
            "not the fastest offer"
        )

    if not off.refundable:
        cons.append(
            "non-refundable fare"
        )

    if not off.changeable:
        cons.append(
            "cannot be changed"
        )

    strengths = (
        ", ".join(pros)
        or "strong weighted score"
    )

    drawbacks = (
        ", ".join(cons)
        or "no major disadvantage in these criteria"
    )

    return (
        f"{companies[off.company].name} ranks first "
        f"({top.total:.1f}/100). "
        f"Advantages: {strengths}. "
        f"Trade-offs: {drawbacks}. "
        "This ranking depends on the chosen preferences."
    )