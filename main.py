
import logging
import sqlite3
import tkinter as tk
from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from busbidder.booking import Booker
from busbidder.market import (
    finn_tilbud, forklar_topp, last_marked, last_profiler,
    poenggrenser, ranger_tilbud, tidsgrenser
)
from busbidder.models import BookingError, DataError, Request, Weights


ROT = Path(__file__).resolve().parent


def kjor_app():
    (ROT / "logs").mkdir(exist_ok=True)

    logging.basicConfig(
        filename=ROT / "logs" / "busbidder.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    rot = tk.Tk()
    rot.title("BusBidder Spain")
    rot.geometry("1050x740")
    rot.minsize(850, 620)

    try:
        selskap, maal, tilbud, avvist = last_marked(ROT / "data")
        profiler = last_profiler(ROT / "data" / "profiles.json")
        grenser = poenggrenser(tilbud)
        bok = Booker(ROT / "output" / "bookings.sqlite3", tilbud)

    except (DataError, sqlite3.Error, OSError) as err:
        logging.exception("Application failed")
        messagebox.showerror("Application error", str(err), parent=rot)
        rot.destroy()
        return

    faner = ttk.Notebook(rot)
    faner.pack(fill="both", expand=True, padx=12, pady=12)

    sok_fane = ttk.Frame(faner, padding=10)
    profil_fane = ttk.Frame(faner, padding=10)
    bok_fane = ttk.Frame(faner, padding=10)

    faner.add(sok_fane, text="Search and book")
    faner.add(profil_fane, text="Compare profiles")
    faner.add(bok_fane, text="Find booking")

    # Travel requirements
    krav_ramme = ttk.LabelFrame(
        sok_fane, text="Travel requirements", padding=10
    )
    krav_ramme.pack(fill="x")

    data = [
        ("maal", "Destination", "Malaga"),
        ("fra", "First date (YYYY-MM-DD)", "2026-11-12"),
        ("til", "Last date (YYYY-MM-DD)", "2026-11-13"),
        ("pris", "Maximum price (EUR)", ""),
        ("tid", "Preferred time (HH:MM)", ""),
        ("bytter", "Maximum transfers", ""),
        ("bag", "Luggage items", "0"),
        ("var", "Maximum duration (min)", ""),
        ("seter", "Seats needed", "1")
    ]

    felt = {}
    navn = {}

    for i, (kode, tekst, start) in enumerate(data):
        rad = i % 5
        kol = (i // 5) * 2

        ttk.Label(krav_ramme, text=tekst).grid(
            row=rad, column=kol,
            sticky="w", padx=(0, 8), pady=4
        )

        verdi = tk.StringVar(value=start)

        if kode == "maal":
            inp = ttk.Combobox(
                krav_ramme,
                textvariable=verdi,
                values=sorted(maal),
                state="readonly",
                width=23
            )
        else:
            inp = ttk.Entry(
                krav_ramme,
                textvariable=verdi,
                width=25
            )

        inp.grid(
            row=rad, column=kol + 1,
            sticky="ew", padx=(0, 18), pady=4
        )

        felt[kode] = verdi
        navn[kode] = tekst

    endres = tk.BooleanVar(value=False)
    refunderes = tk.BooleanVar(value=False)

    ttk.Checkbutton(
        krav_ramme,
        text="Must be changeable",
        variable=endres
    ).grid(
        row=5, column=0, columnspan=2,
        sticky="w", pady=5
    )

    ttk.Checkbutton(
        krav_ramme,
        text="Must be refundable",
        variable=refunderes
    ).grid(
        row=5, column=2, columnspan=2,
        sticky="w", pady=5
    )

    # Traveller profiles
    profil_ramme = ttk.LabelFrame(
        sok_fane, text="Traveller profile", padding=10
    )
    profil_ramme.pack(fill="x", pady=8)

    profil = tk.StringVar(value="Budget")

    ttk.Combobox(
        profil_ramme,
        textvariable=profil,
        values=list(profiler) + ["Custom"],
        state="readonly",
        width=13
    ).pack(side="left", padx=(0, 12))

    ttk.Label(
        profil_ramme,
        text="Custom weights:"
    ).pack(side="left")

    vekter = {}

    for kode in ("price", "duration", "time", "flexibility"):
        ttk.Label(
            profil_ramme,
            text=kode.capitalize()
        ).pack(side="left", padx=(10, 3))

        verdi = tk.StringVar(value="25")

        ttk.Entry(
            profil_ramme,
            textvariable=verdi,
            width=5
        ).pack(side="left")

        vekter[kode] = verdi

    knapper = ttk.Frame(sok_fane)
    knapper.pack(fill="x", pady=(0, 8))

    # Results table
    kolonner = (
        "nr", "selskap", "id", "avgang", "pris",
        "min", "bytter", "seter", "poeng"
    )

    titler = (
        "#", "Company", "Offer ID", "Departure", "EUR",
        "Minutes", "Transfers", "Seats", "Score"
    )

    bredder = (40, 115, 85, 150, 65, 70, 75, 60, 70)

    tabell_ramme = ttk.Frame(sok_fane)
    tabell_ramme.pack(fill="both", expand=True)
    tabell_ramme.columnconfigure(0, weight=1)
    tabell_ramme.rowconfigure(0, weight=1)

    tabell = ttk.Treeview(
        tabell_ramme,
        columns=kolonner,
        show="headings",
        selectmode="browse",
        height=10
    )

    for kode, tekst, bredde in zip(kolonner, titler, bredder):
        tabell.heading(kode, text=tekst)
        tabell.column(
            kode, width=bredde,
            anchor="center", stretch=True
        )

    tabell.grid(row=0, column=0, sticky="nsew")

    rull_y = ttk.Scrollbar(
        tabell_ramme,
        orient="vertical",
        command=tabell.yview
    )

    rull_x = ttk.Scrollbar(
        tabell_ramme,
        orient="horizontal",
        command=tabell.xview
    )

    rull_y.grid(row=0, column=1, sticky="ns")
    rull_x.grid(row=1, column=0, sticky="ew")

    tabell.configure(
        yscrollcommand=rull_y.set,
        xscrollcommand=rull_x.set
    )

    status = tk.StringVar(
        value=f"Loaded {len(tilbud)} valid offers; "
              f"rejected {avvist} invalid rows."
    )

    ttk.Label(
        sok_fane,
        textvariable=status
    ).pack(anchor="w", pady=(8, 3))

    info = tk.Text(
        sok_fane, height=5, wrap="word", state="disabled"
    )
    info.pack(fill="x", pady=(2, 4))

    # Profile comparison tab
    ttk.Label(
        profil_fane,
        text="Compare profiles using the requirements from the Search tab."
    ).pack(anchor="w", pady=(0, 12))

    ttk.Button(
        profil_fane,
        text="Compare now",
        command=lambda: sammenlikn()
    ).pack(anchor="w", pady=(0, 10))

    sammenligning = tk.Text(
        profil_fane, wrap="word", state="disabled"
    )
    sammenligning.pack(fill="both", expand=True)

    # Booking lookup tab
    rad = ttk.Frame(bok_fane)
    rad.pack(anchor="w", pady=(0, 10))

    ttk.Label(
        rad, text="Booking reference:"
    ).pack(side="left", padx=(0, 8))

    kode = tk.StringVar()

    ttk.Entry(
        rad, textvariable=kode, width=30
    ).pack(side="left", padx=(0, 10))

    bok_info = tk.Text(
        bok_fane, wrap="word", state="disabled", height=10
    )
    bok_info.pack(fill="both", expand=True)

    valgt = {"krav": None, "rang": []}

    def vis_tekst(rute, tekst):
        rute.config(state="normal")
        rute.delete("1.0", "end")
        rute.insert("end", tekst)
        rute.config(state="disabled")

    def hent_felt(k, type_=str, tom=None):
        tekst = felt[k].get().strip()

        if not tekst:
            if k in ("maal", "fra", "til"):
                raise DataError(f"{navn[k]} is required.")
            return tom

        try:
            return type_(tekst)
        except (ValueError, InvalidOperation):
            raise DataError(f"Invalid {navn[k]}.") from None

    def les_krav():
        return Request(
            destination=hent_felt("maal"),
            start=hent_felt("fra", date.fromisoformat),
            end=hent_felt("til", date.fromisoformat),
            budget=hent_felt("pris", Decimal),
            preferred=hent_felt("tid", time.fromisoformat),
            max_transfers=hent_felt("bytter", int),
            luggage=hent_felt("bag", int, 0),
            max_dur=hent_felt("var", int),
            changeable=endres.get(),
            refundable=refunderes.get(),
            seats=hent_felt("seter", int, 1)
        )

    def velg_vekt():
        if profil.get() != "Custom":
            return profiler[profil.get()]

        try:
            tall = [
                float(vekter[k].get())
                for k in ("price", "duration", "time", "flexibility")
            ]
        except ValueError:
            raise DataError("Invalid custom weights.") from None

        return Weights(*tall)

    def vis_info(_=None):
        rader = tabell.selection()

        if not rader or not valgt["rang"]:
            return

        res = valgt["rang"][int(rader[0])]
        tur = res.offer
        p = res.points

        tekst = (
            f"{selskap[tur.company].name} ({tur.id}) "
            f"| {res.total:.1f}/100\n"
            f"Price: {p['price']:.1f} "
            f"| Duration: {p['duration']:.1f} "
            f"| Time: {p['time']:.1f} "
            f"| Flexibility: {p['flexibility']:.1f}\n"
            f"Changeable: {tur.changeable} "
            f"| Refundable: {tur.refundable} "
            f"| Luggage: {tur.luggage} "
            f"| Rating: {tur.rating:.1f}/5\n"
            f"Recommendation: {forklar_topp(valgt['rang'], selskap)}"
        )

        vis_tekst(info, tekst)

    def finn_reiser():
        try:
            krav = les_krav()
            vekt = velg_vekt()

            ledige = bok.ledige_seter(tilbud)
            gyldige, avslag = finn_tilbud(ledige, krav)

            rang = ranger_tilbud(
                gyldige, krav, vekt, grenser,
                tidsgrenser(tilbud, krav.preferred)
            )

        except (DataError, sqlite3.Error) as err:
            messagebox.showerror(
                "Invalid request", str(err), parent=rot
            )
            return

        tabell.delete(*tabell.get_children())

        valgt["krav"] = krav
        valgt["rang"] = rang

        for i, res in enumerate(rang):
            tur = res.offer

            tabell.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    i + 1,
                    selskap[tur.company].name,
                    tur.id,
                    tur.depart.strftime("%Y-%m-%d %H:%M"),
                    f"{tur.price:.2f}",
                    tur.duration,
                    tur.transfers,
                    tur.seats,
                    f"{res.total:.1f}"
                )
            )

        status.set(
            f"Acceptable offers: {len(gyldige)} / {len(ledige)}"
        )

        if rang:
            tabell.selection_set("0")
            tabell.focus("0")
            vis_info()
        else:
            vis_tekst(
                info,
                "No matching offers. Change the travel requirements.\n"
                f"Hard-constraint rejections (may overlap): {dict(avslag)}"
            )

    def sammenlikn():
        try:
            krav = les_krav()
            ledige = bok.ledige_seter(tilbud)
            gyldige, _ = finn_tilbud(ledige, krav)
            tid = tidsgrenser(tilbud, krav.preferred)

        except (DataError, sqlite3.Error) as err:
            messagebox.showerror(
                "Invalid request", str(err), parent=rot
            )
            return

        faner.select(profil_fane)

        if not gyldige:
            vis_tekst(
                sammenligning,
                "No matching offers. Try different travel requirements."
            )
            return

        linjer = [
            f"Same {len(gyldige)} acceptable offers for all profiles.\n"
        ]

        for profilnavn, vekt in profiler.items():
            rang = ranger_tilbud(
                gyldige, krav, vekt, grenser, tid
            )

            linjer.append(f"=== {profilnavn} ===")
            linjer.append(forklar_topp(rang, selskap))

            for i, res in enumerate(rang[:3], 1):
                linjer.append(
                    f"{i}. {selskap[res.offer.company].name}: "
                    f"{res.total:.1f}/100"
                )

            linjer.append("")

        vis_tekst(sammenligning, "\n".join(linjer))

    def bestill_tur():
        rader = tabell.selection()

        if not rader or not valgt["rang"]:
            messagebox.showwarning(
                "Select an offer",
                "Select an offer first.",
                parent=rot
            )
            return

        navn = simpledialog.askstring(
            "Book offer",
            "Passenger name:",
            parent=rot
        )

        if navn is None:
            return

        tur = valgt["rang"][int(rader[0])].offer

        try:
            bestilling = bok.lag_bestilling(
                tur, navn, valgt["krav"].seats
            )

        except BookingError as err:
            messagebox.showerror(
                "Booking failed", str(err), parent=rot
            )
            return

        tekst = "\n".join(
            f"{k}: {v}" for k, v in bestilling.items()
        )

        messagebox.showinfo(
            "Booking confirmation",
            tekst + "\n\nNo payment details were collected.",
            parent=rot
        )

        finn_reiser()

    def sjekk_kode():
        try:
            bestilling = bok.finn_bestilling(
                kode.get().strip().upper()
            )

        except BookingError as err:
            messagebox.showerror(
                "Invalid booking reference",
                str(err),
                parent=rot
            )
            return

        if bestilling:
            tekst = "\n".join(
                f"{k}: {v}" for k, v in bestilling.items()
            )
        else:
            tekst = "No booking found."

        vis_tekst(bok_info, tekst)

    tabell.bind("<<TreeviewSelect>>", vis_info)

    ttk.Button(
        knapper,
        text="Find and rank offers",
        command=finn_reiser
    ).pack(side="left", padx=(0, 8))

    ttk.Button(
        knapper,
        text="Book selected offer",
        command=bestill_tur
    ).pack(side="left", padx=(0, 8))

    ttk.Button(
        knapper,
        text="Compare profiles",
        command=sammenlikn
    ).pack(side="left")

    ttk.Button(
        rad,
        text="Find booking",
        command=sjekk_kode
    ).pack(side="left")

    vis_tekst(
        info,
        "Enter travel requirements, then select Find and rank offers."
    )

    rot.mainloop()


if __name__ == "__main__":
    kjor_app()
