
import csv
import json

from datetime import datetime, timedelta
from pathlib import Path


DATAMAPPE = Path(__file__).resolve().parent / "data"        # Data-folder


SELSKAPER = [       # Companies
    ("SR", "SolRuta", "Low-cost daytime journeys"),
    ("CE", "Camino Express", "Fast direct journeys"),
    ("CL", "CostaLink", "Coastal connections"),
    ("VB", "VerdeBus", "Environment-focused journeys"),
    ("NV", "NocheVia", "Evening and night departures")
]


REISEMAAL = [       # Destinations
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


# Company settings: departure time, duration and price multipliers,
# transfers, luggage, changeable, refundable, rating and emissions
STIL = {
    "SR": (     # SolRuta
        "07:30", 1.18, 0.70, 1, 1,
        False, False, 3.8, 1.0
    ),

    "CE": (     # Camino Express
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


# Columns
KOLONNER = [
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


# Write CSV (path, columns, values)
def skriv_csv(sti, kolonner, verdier):
    with sti.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as fil:

        skriver = csv.DictWriter(       # writer
            fil,
            fieldnames=kolonner
        )

        skriver.writeheader()
        skriver.writerows(verdier)


# Generate data
def lag_data():
    DATAMAPPE.mkdir(
        exist_ok=True
    )

    skriv_csv(
        DATAMAPPE / "companies.csv",
        ["code", "name", "description"],
        [
            dict(
                zip(
                    ["code", "name", "description"],
                    sels
                )
            )
            for sels in SELSKAPER
        ]
    )

    skriv_csv(
        DATAMAPPE / "destinations.csv",
        ["name"],
        [
            {"name": navn}              # name
            for navn, _, _ in REISEMAAL
        ]
    )

    tilbud = []                         # offers

    # Add journey (company, destination, day, minutes, price, time,
    # transfers, luggage, changeable, refundable, rating, emissions)
    def legg_til_tur(
        sels, maal, dag, minutter, pris, klokke,
        bytter, bagasje, kan_endres, kan_refunderes,
        vurdering, utslipp
    ):
        avgang = datetime.fromisoformat(    # departure
            f"{dag}T{klokke}"
        )

        ankomst = avgang + timedelta(       #arrival
            minutes=minutter
        )

        tilbud.append({
            "offer_id": f"OF-{len(tilbud) + 1:04d}",
            "company": sels,
            "origin": "Madrid",
            "destination": maal,
            "depart": avgang.isoformat(
                timespec="minutes"
            ),
            "arrive": ankomst.isoformat(
                timespec="minutes"
            ),
            "minutes": minutter,
            "price": f"{pris:.2f}",
            "transfers": bytter,
            "luggage": bagasje,
            "changeable": str(kan_endres).lower(),
            "refundable": str(kan_refunderes).lower(),
            "seats": 18,
            "rating": vurdering,
            "emissions": f"{utslipp:.2f}"
        })

    for dag in (
        "2026-11-12",
        "2026-11-13"
    ):
        for maal, minutter, pris in REISEMAAL:
            for sels in STIL:

                # tid_faktor = duration multiplier
                # pris_faktor = price multiplier
                (
                    klokke, tid_faktor, pris_faktor, bytter, bagasje,
                    kan_endres, kan_refunderes, vurdering, utslipp
                ) = STIL[sels]

                legg_til_tur(
                    sels,
                    maal,
                    dag,
                    round(minutter * tid_faktor),
                    pris * pris_faktor,
                    klokke,
                    bytter,
                    bagasje,
                    kan_endres,
                    kan_refunderes,
                    vurdering,
                    minutter * 0.025 * utslipp
                )

    # add offers 
    legg_til_tur(
        "SR", "Malaga", "2026-11-12",
        520, 27, "14:15",
        1, 1, False, False, 3.8, 12
    )

    legg_til_tur(
        "CE", "Malaga", "2026-11-12",
        350, 76, "08:45",
        0, 1, True, False, 4.6, 8
    )

    avvist = []             #rejected offers

    # changes -> invalid offers
    endringer = [
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

    for endring in endringer:            # change
        rad = tilbud[0].copy()            # row
        rad.update(endring)
        avvist.append(rad)

    skriv_csv(
        DATAMAPPE / "offers.csv",
        KOLONNER,
        tilbud + avvist
    )

    # traveller-profiles
    profiler = {
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
        DATAMAPPE / "profiles.json"
    ).write_text(
        json.dumps(
            profiler,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Created {len(tilbud)} valid "
        f"and {len(avvist)} invalid offers."
    )


if __name__ == "__main__":
    lag_data()
