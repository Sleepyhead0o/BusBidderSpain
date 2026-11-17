
import csv
import json
import logging
import math
import re

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Company, DataError, Offer, Score, Weights


LOGG = logging.getLogger(__name__)

# ID pattern
ID_REGEL = re.compile(r"OF-\d{4,6}$")


# read CSV (path, required fields )
def les_csv(sti, feltkrav):
    try:
        with sti.open(
            newline="",
            encoding="utf-8-sig"
        ) as fil:

            leser = csv.DictReader(fil)     # read

            if not leser.fieldnames:
                raise DataError(
                    f"Missing headers in {sti.name}."
                )

            if not set(feltkrav).issubset(leser.fieldnames):
                raise DataError(
                    f"Missing columns in {sti.name}."
                )

            return list(leser)

    except (OSError, UnicodeError, csv.Error) as err:
        raise DataError(
            f"Cannot read {sti}: {err}"
        ) from err


# read integer (row, field, min)
def les_heltall(rad, felt, minst=0):
    verdi = (rad.get(felt) or "").strip()

    if not verdi.isdigit():
        raise DataError(
            f"Invalid {felt}."
        )

    nr = int(verdi)

    if nr < minst:
        raise DataError(
            f"Invalid {felt}."
        )

    return nr


# read boolean
def les_boolsk(rad, felt):
    verdi = (rad.get(felt) or "").strip().lower()

    # If not boolean then "wrong" 
    if verdi not in ("true", "false"):
        raise DataError(        
            f"Invalid {felt}."
        )

    return verdi == "true"


# create offer (row, companies, destinations)
def lag_tilbud(rad, selskap, reisemaal):
    try:
        
        tilbuds_id = (rad.get("offer_id") or "").strip()  # offer ID
        sels = (rad.get("company") or "").strip()         # company
        maal = (rad.get("destination") or "").strip()     # destination

        if not ID_REGEL.fullmatch(tilbuds_id):
            raise DataError(
                "Invalid offer ID."
            )

        if sels not in selskap or maal not in reisemaal:
            raise DataError(
                "Unknown company or destination."
            )

        if (rad.get("origin") or "").strip() != "Madrid":
            raise DataError(
                "Origin must be Madrid."
            )

        
        avgang = datetime.fromisoformat(rad["depart"])    # departure
        ankomst = datetime.fromisoformat(rad["arrive"])   # arrival

        if avgang.tzinfo or ankomst.tzinfo or ankomst <= avgang:
            raise DataError(
                "Invalid departure/arrival order."
            )

        
        minutter = les_heltall(rad, "minutes", 1)       # minutes 

        if (ankomst - avgang).total_seconds() != minutter * 60:
            raise DataError(
                "Duration does not match the times."
            )

        
        pris = Decimal(rad["price"])        # price
        vurdering = float(rad["rating"])    # rating

        if pris <= 0 or not pris.is_finite():           
            raise DataError("Price must be positive")

        if not math.isfinite(vurdering) or not 1 <= vurdering <= 5:
            raise DataError(
                "Invalid rating, since the number must be between 1 and 5"
            )

        
        utslipp = (rad.get("emissions") or "").strip()      # emissions

        if utslipp:
            utslipp = float(utslipp)
        else:
            utslipp = None

        if utslipp is not None:
            if not math.isfinite(utslipp) or utslipp < 0:
                raise DataError(
                    "Invalid emissions."
                )

        return Offer(
            tilbuds_id,
            sels,
            maal,
            avgang,
            ankomst,
            pris,
            les_heltall(rad, "transfers"),
            les_heltall(rad, "luggage"),
            les_boolsk(rad, "changeable"),
            les_boolsk(rad, "refundable"),
            les_heltall(rad, "seats"),
            vurdering,
            utslipp
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


# last_marked = load market data
# mappe = folder
def last_marked(mappe):
    # selskap = companies
    selskap = {}

    # s_rader = company rows
    s_rader = les_csv(
        mappe / "companies.csv",
        ["code", "name", "description"]
    )

    for rad in s_rader:
        
        sels = (rad["code"] or "").strip()                      # company code
        navn = (rad["name"] or "").strip()                      # name
        beskrivelse = (rad["description"] or "").strip()        # description

        if not sels or not navn or not beskrivelse or sels in selskap:
            raise DataError(
                "Invalid or duplicate company."
            )

        selskap[sels] = Company(
            sels,
            navn,
            beskrivelse
        )

    
    reisemaal = set()       # several destinations

    
    m_rader = les_csv(          # destination rows
        mappe / "destinations.csv",
        ["name"]
    )

    for rad in m_rader:
        maal = (rad["name"] or "").strip()          # name of one destination

        if not maal or maal in reisemaal or maal == "Madrid":
            raise DataError(
                "Invalid or duplicate destination."
            )

        reisemaal.add(maal)

    
    kolonner = [        # columns
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

    
    tilbud = []         # offers
    avvist = []         # rejected
    brukte = set()      # used IDs

    # line number
    for linje, rad in enumerate(
        les_csv(mappe / "offers.csv", kolonner),
        2
    ):
        try:
            # tur = offer
            tur = lag_tilbud(
                rad,
                selskap,
                reisemaal
            )

            if tur.id in brukte:
                raise DataError(
                    "Duplicate offer ID."
                )

            brukte.add(tur.id)
            tilbud.append(tur)

        except DataError as err:
            LOGG.warning(
                "Rejected line %d: %s",
                linje,
                err
            )

            avvist.append({
                "line": linje,
                "id": rad.get("offer_id", ""),
                "reason": str(err)
            })

    # output file
    utfil = mappe.parent / "output" / "rejected.csv"
    utfil.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with utfil.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as fil:

        skriver = csv.DictWriter(
            fil,
            ["line", "id", "reason"]
        )

        skriver.writeheader()
        skriver.writerows(avvist)

    if not tilbud:
        raise DataError(
            "No valid offers were found."
        )

    return selskap, reisemaal, tilbud, len(avvist)


# load profiles
def last_profiler(sti):
    try:
        with sti.open(encoding="utf-8") as fil:
            data = json.load(fil)

        
        profiler = {                    # profiles
            navn: Weights(**vekt)       # weights
            for navn, vekt in data.items()
        }

        if len(profiler) < 3:
            raise DataError(
                "At least three profiles are required."
            )

        return profiler

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError
    ) as err:

        raise DataError(
            f"Cannot load profiles: {err}"
        ) from err


# check offer (offer, request)
def sjekk_tilbud(tur, krav):
    
    avvist = []         # rejection reasons

    if tur.destination != krav.destination:
        avvist.append("destination")

    if not krav.start <= tur.day <= krav.end:       # hard constraint, bus departue is outside selcted dates
        avvist.append("date")

    if krav.budget is not None:
        if tur.price > krav.budget:
            avvist.append("budget")

    if tur.seats < krav.seats:
        avvist.append("seats")

    if krav.max_transfers is not None:
        if tur.transfers > krav.max_transfers:
            avvist.append("transfers")

    if tur.luggage < krav.luggage:
        avvist.append("luggage")

    if krav.max_dur is not None:
        if tur.duration > krav.max_dur:
            avvist.append("duration")

    if krav.changeable and not tur.changeable:
        avvist.append("changeable")

    if krav.refundable and not tur.refundable:
        avvist.append("refundable")

    return avvist


# find matching offers
def finn_tilbud(tilbud, krav):
    
    gyldige = []            # valid offers
    avvist = Counter()      # rejection counts

    for tur in tilbud:
        
        arsaker = sjekk_tilbud(tur, krav)       # reasons

        if arsaker:
            avvist.update(arsaker)
        else:
            gyldige.append(tur)

    return gyldige, avvist


# limit score
def begrens_poeng(nr):
    return max(
        0.0,
        min(100.0, nr)
    )


# score bounds
def poenggrenser(tilbud):
    # find lowest and highest value from all valid offers
    if not tilbud:      # offers
        raise DataError("No offers available for normalization.")

    return {
        "price": (
            min(float(tur.price) for tur in tilbud),    # lowest
            max(float(tur.price) for tur in tilbud)     # highest 
        ),
        "duration": (
            min(tur.duration for tur in tilbud),        # lowest
            max(tur.duration for tur in tilbud)         # highest 
        )
    }


# normalize lower values (value, low, high)
def skaler_lavt(verdi, lav, hoy):
    # Smaller receive more points
    if lav == hoy:
        return 100.0

    return begrens_poeng(
        100 * (hoy - float(verdi)) / (hoy - lav)
    )


# time difference (offer, preferred time)
def tidsavstand(tur, onsket):
    # Time difference between bus departure time and user's preferred one
    
    avgang_min = tur.depart.hour * 60 + tur.depart.minute       # departure minutes
    onsket_min = onsket.hour * 60 + onsket.minute               # preferred minutes

    
    avstand = abs(avgang_min - onsket_min)      # difference

    if avstand > 720:       # time diff greater then 12 hours
        avstand = 1440 - avstand

    return avstand


# time bounds
def tidsgrenser(tilbud, onsket):
    # once per request from all valid offers
    if onsket is None:
        return None

    if not tilbud:
        raise DataError("No offers available for normalization.")

    
    avstander = [tidsavstand(tur, onsket) for tur in tilbud]        # time differences
    return min(avstander), max(avstander)


# rank offers
def ranger_tilbud(tilbud, krav, vekt, grenser, tid_grenser):
   
    rangering = []      # ranking

    
    min_pris, maks_pris = grenser["price"]          # min/max price
    min_tid, maks_tid = grenser["duration"]         # min/max duration
    
    if krav.preferred is not None and tid_grenser is None:      
        raise DataError("Departure-time bounds are required.")

    for tur in tilbud:
        
        p = skaler_lavt(tur.price, min_pris, maks_pris)         # price score
        d = skaler_lavt(tur.duration, min_tid, maks_tid)        # duration score

        
        if krav.preferred is None:
            t = 50.0        # time score
        else:
            dt = tidsavstand(tur, krav.preferred)       # time difference
            t = skaler_lavt(dt, *tid_grenser)           # time score

        
        fleks = 50.0 * (            # flexibility score
            int(tur.changeable)
            + int(tur.refundable)
        )

        
        poeng = {       # scores
            "price": p,
            "duration": d,
            "time": t,
            "flexibility": fleks
        }

        
        sum_poeng = sum(        # total score
            poeng[navn] * getattr(vekt, navn) / 100
            for navn in poeng
        )

        rangering.append(
            Score(tur, poeng, sum_poeng)
        )

    return sorted(
        rangering,
        key=lambda res: (
            -res.total,
            res.offer.price,
            res.offer.duration,
            res.offer.id
        )
    )


# explain top recommendation
def forklar_topp(rangering, selskap):
    if not rangering:
        return "No matching offers."

    
    beste = rangering[0]        # best result
    tur = beste.offer

    
    pluss = []          # advantages
    minus = []          # disadvantages

    if tur.transfers == 0:      # no transfer
        pluss.append("direct journey")

    if beste.points["time"] >= 85:
        pluss.append("relatively convenient departure")

    if tur.changeable and tur.refundable:
        pluss.append(
            "flexible and refundable fare"
        )

    
    lav = min(          # lowest price
        res.offer.price
        for res in rangering
    )

    
    raskest = min(          # shortest duration
        res.offer.duration
        for res in rangering
    )

    if tur.price > lav:
        minus.append(
            "not the cheapest offer"
        )

    if tur.duration > raskest:
        minus.append(
            "not the fastest offer"
        )

    if not tur.refundable:
        minus.append(
            "non-refundable fare"
        )

    if not tur.changeable:
        minus.append(
            "cannot be changed"
        )

    
    fordeler = (        # advantages
        ", ".join(pluss)
        or "strong weighted score"
    )

    ulemper = (             # trade-offs
        ", ".join(minus)
        or "no major disadvantage in these criteria"
    )

    return (
        f"{selskap[tur.company].name} ranks first "
        f"({beste.total:.1f}/100). "
        f"Advantages: {fordeler}. "
        f"Trade-offs: {ulemper}. "
        "This ranking depends on the chosen preferences."
    )
