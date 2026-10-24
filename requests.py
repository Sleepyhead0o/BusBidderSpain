
from datetime import date, time

from data_manager import DESTINATIONS
from models import TravellerRequest


REQUESTS = {
    "1": {
        "name": "Budget trip to Malaga",
        "data": {
            "dest": "Malaga",
            "startD": date(2026, 11, 12),
            "endD": date(2026, 11, 12),
            "max_p": 50,
            "max_tr": 1,
            "min_lug": 1,
            "pref_t": time(9, 0),
            "seats": 1
        }
    },
    "2": {
        "name": "Business trip to Barcelona",
        "data": {
            "dest": "Barcelona",
            "startD": date(2026, 11, 12),
            "endD": date(2026, 11, 12),
            "max_p": 80,
            "max_tr": 0,
            "max_dur": 500,
            "pref_t": time(9, 0),
            "seats": 1
        }
    },
    "3": {
        "name": "Flexible holiday to Valencia",
        "data": {
            "dest": "Valencia",
            "startD": date(2026, 11, 13),
            "endD": date(2026, 11, 13),
            "max_p": 60,
            "req_ch": True,
            "req_ref": True,
            "pref_t": time(12, 0),
            "seats": 1
        }
    },
    "4": {
        "name": "Direct journey to Seville",
        "data": {
            "dest": "Seville",
            "startD": date(2026, 11, 14),
            "endD": date(2026, 11, 14),
            "max_p": 60,
            "max_tr": 0,
            "pref_t": time(14, 0),
            "seats": 1
        }
    },
    "5": {
        "name": "Family trip to Granada",
        "data": {
            "dest": "Granada",
            "startD": date(2026, 11, 13),
            "endD": date(2026, 11, 13),
            "max_p": 150,
            "max_tr": 1,
            "min_lug": 1,
            "pref_t": time(10, 0),
            "seats": 4
        }
    },
    "6": {
        "name": "Evening journey to Alicante",
        "data": {
            "dest": "Alicante",
            "startD": date(2026, 11, 12),
            "endD": date(2026, 11, 12),
            "max_p": 50,
            "max_tr": 1,
            "pref_t": time(21, 0),
            "seats": 1
        }
    },
    "7": {
        "name": "Strict budget trip to Cordoba",
        "data": {
            "dest": "Cordoba",
            "startD": date(2026, 11, 14),
            "endD": date(2026, 11, 14),
            "max_p": 20,
            "max_tr": 0,
            "pref_t": time(9, 0),
            "seats": 1
        }
    },
    "8": {
        "name": "No matching offers",
        "data": {
            "dest": "Malaga",
            "startD": date(2026, 11, 12),
            "endD": date(2026, 11, 12),
            "max_p": 10,
            "max_tr": 0,
            "req_ch": True,
            "req_ref": True,
            "pref_t": time(9, 0),
            "seats": 1
        }
    }
}


class RequestValidationError(ValueError):
    pass


def validate_request(d):
    try:
        req = TravellerRequest(**d)
    except (TypeError, ValueError) as e:
        raise RequestValidationError(str(e)) from e

    if req.dest not in DESTINATIONS:
        raise RequestValidationError("Unknown destination")

    return req


def select_request(n):
    if n not in REQUESTS:
        raise RequestValidationError("Invalid selection")

    r = REQUESTS[n]
    req = validate_request(r["data"])

    return r["name"], req


def display_requests():
    print("\n=== Traveller Requests ===")

    for n, r in REQUESTS.items():
        print(f"{n}. {r['name']}")

    print("0. Exit")
