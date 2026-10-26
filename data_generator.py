import csv
import json

from datetime import datetime, timedelta
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"


COMPANIES = [
    ("SR", "SolRuta", "Low-cost daytime journeys"),
    ("CE", "Camino Express", "Fast direct journeys"),
    ("CL", "CostaLink", "Coastal connections"),
    ("VB", "VerdeBus", "Environment-focused journeys"),
    ("NV", "NocheVia", "Evening and night departures")
]


DESTINATIONS = [
    ("Barcelona", 500, 58),
    ("Valencia", 310, 38),
    ("Seville", 410, 39),
    ("Malaga", 440, 35),
    ("Granada", 385, 35),
    ("Cordoba", 315, 30),
    ("Bilbao", 415, 48),
    ("San Sebastian", 490, 55),
    ("Zaragoza", 255, 32),
    ("Alicante", 365, 41),
    ("Murcia", 355, 40),
    ("Salamanca", 185, 24),
    ("Toledo", 75, 15),
    ("Santiago de Compostela", 620, 65),
    ("Cadiz", 490, 46)
]


# Departure, duration multiplier, price multiplier,
# transfers, luggage, changeable, refundable,
# rating, emissions multiplier.

STYLE = {
    "SR": (
        "07:30", 1.18, 0.70, 1, 1,
        False, False, 3.8, 1.0
    ),

    "CE": (
        "09:15", 0.78, 1.68, 0, 1,
        True, False, 4.5, 0.9
    ),

    "CL": (
        "11:00", 1.00, 1.18, 0, 2,
        True, True, 4.2, 0.8
    ),

    "VB": (
        "08:40", 1.08, 1.15, 0, 2,
        True, True, 4.6, 0.6
    ),

    "NV": (
        "22:30", 1.21, 0.85, 1, 1,
        False, True, 3.9, 1.1
    )
}


COLS = [
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
    "rating",
    "emissions"
]


def write_csv(path, cols, vals):
    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        wr = csv.DictWriter(
            f,
            fieldnames=cols
        )

        wr.writeheader()
        wr.writerows(vals)


def generate():
    DATA.mkdir(
        exist_ok=True
    )

    write_csv(
        DATA / "companies.csv",
        ["code", "name", "description"],
        [
            dict(
                zip(
                    ["code", "name", "description"],
                    co
                )
            )
            for co in COMPANIES
        ]
    )

    write_csv(
        DATA / "destinations.csv",
        ["name"],
        [
            {"name": name}
            for name, _, _ in DESTINATIONS
        ]
    )

    offers = []

    def add(
        co, dst, day, mins, price, hour,
        tr, bag, ch, rf, rt, eco
    ):
        dep = datetime.fromisoformat(
            f"{day}T{hour}"
        )

        arr = dep + timedelta(
            minutes=mins
        )

        offers.append({
            "offer_id": f"OF-{len(offers) + 1:04d}",
            "company": co,
            "origin": "Madrid",
            "destination": dst,
            "depart": dep.isoformat(
                timespec="minutes"
            ),
            "arrive": arr.isoformat(
                timespec="minutes"
            ),
            "minutes": mins,
            "price": f"{price:.2f}",
            "transfers": tr,
            "luggage": bag,
            "changeable": str(ch).lower(),
            "refundable": str(rf).lower(),
            "seats": 18,
            "rating": rt,
            "emissions": f"{eco:.2f}"
        })

    for day in (
        "2026-11-12",
        "2026-11-13"
    ):
        for dst, mins, price in DESTINATIONS:
            for co in STYLE:

                (
                    hour, dm, pm, tr, bag,
                    ch, rf, rt, eco
                ) = STYLE[co]

                add(
                    co,
                    dst,
                    day,
                    round(mins * dm),
                    price * pm,
                    hour,
                    tr,
                    bag,
                    ch,
                    rf,
                    rt,
                    mins * 0.025 * eco
                )

    add(
        "SR", "Malaga", "2026-11-12",
        520, 27, "14:15",
        1, 1, False, False, 3.8, 12
    )

    add(
        "CE", "Malaga", "2026-11-12",
        350, 76, "08:45",
        0, 1, True, False, 4.6, 8
    )

    bad = []

    changes = [
        {"offer_id": "INVALID"},

        {
            "offer_id": "OF-0901",
            "price": "-5"
        },

        {
            "offer_id": "OF-0902",
            "destination": "Atlantis"
        },

        {
            "offer_id": "OF-0903",
            "depart": "2026-13-99T09:00"
        },

        {
            "offer_id": "OF-0904",
            "arrive": "2026-11-11T00:00"
        },

        {
            "offer_id": "OF-0905",
            "rating": "8"
        },

        {
            "offer_id": "OF-0906",
            "seats": "-1"
        },

        {
            "offer_id": "OF-0907",
            "changeable": "maybe"
        },

        {
            "offer_id": "OF-0908",
            "company": "XX"
        },

        {
            "offer_id": "OF-0001"
        }
    ]

    for fix in changes:
        row = offers[0].copy()
        row.update(fix)
        bad.append(row)

    write_csv(
        DATA / "offers.csv",
        COLS,
        offers + bad
    )

    profiles = {
        "Budget": {
            "price": 80,
            "duration": 12,
            "time": 5,
            "flexibility": 3
        },

        "Business": {
            "price": 8,
            "duration": 60,
            "time": 30,
            "flexibility": 2
        },

        "Flexible": {
            "price": 15,
            "duration": 15,
            "time": 10,
            "flexibility": 60
        }
    }

    (
        DATA / "profiles.json"
    ).write_text(
        json.dumps(
            profiles,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Created {len(offers)} valid "
        f"and {len(bad)} invalid offers."
    )


if __name__ == "__main__":
    generate()