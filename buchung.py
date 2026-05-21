from datetime import datetime
import speicherung

BANK_STATUS_FILE = "bankkonten.json"

def initialisiere_bank():
    """Erstellt die initialen Bankkonten, falls noch nicht vorhanden."""
    status = {
        "zentralbankkonto": 0.0,
        "verpflichtungskonto": 0.0,
        "kreditkonto_aktiva": 0.0,
        "einnahmenkonto": 0.0,
        "buchungen": []
    }
    speicherung.speichere_json(BANK_STATUS_FILE, status)
    return status

def verbuchen(vorgang, betrag, intern=False, zeitstempel=None, referenz=None):
    """
    Aktualisiert die internen Bankkonten basierend auf Tabelle 3.
    FIX: intern=True verhindert Zentralbankbuchung bei internen Überweisungen.
    """
    if intern and vorgang in {"Einzahlung", "Auszahlung"}:
        return

    bank = speicherung.lade_json(BANK_STATUS_FILE)
    if not bank:
        bank = initialisiere_bank()

    if not zeitstempel:
        zeitstempel = datetime.now().isoformat() + "Z"

    soll_konto = None
    haben_konto = None

    if vorgang == "Einzahlung":
        # FIX: Bei interner Überweisung (Empfänger) kein Zentralbankkonto berühren
        if not intern:
            bank["zentralbankkonto"] += betrag
            bank["verpflichtungskonto"] += betrag
            soll_konto = "zentralbankkonto"
            haben_konto = "verpflichtungskonto"
        else:
            # Interne Einzahlung: nur Verpflichtungskonto ändert sich (Sender hat bereits abgezogen)
            bank["verpflichtungskonto"] += betrag
            soll_konto = "intern_eingang"
            haben_konto = "verpflichtungskonto"

    elif vorgang == "Auszahlung":
        if not intern:
            bank["verpflichtungskonto"] -= betrag
            bank["zentralbankkonto"] -= betrag
            soll_konto = "verpflichtungskonto"
            haben_konto = "zentralbankkonto"
        else:
            # Interne Überweisung Sender: nur Verpflichtungskonto sinkt
            bank["verpflichtungskonto"] -= betrag
            soll_konto = "verpflichtungskonto"
            haben_konto = "intern_ausgang"

    elif vorgang == "Kreditauszahlung":
        bank["kreditkonto_aktiva"] += betrag
        bank["verpflichtungskonto"] += betrag
        soll_konto = "kreditkonto_aktiva"
        haben_konto = "verpflichtungskonto"

    elif vorgang == "Kreditgebuehr":
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang in {"Kredittilgung", "Kreditrueckzahlung"}:
        bank["verpflichtungskonto"] -= betrag
        bank["kreditkonto_aktiva"] -= betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "kreditkonto_aktiva"

    elif vorgang == "Kreditzinsen":
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Strafzinsen":
        bank["kreditkonto_aktiva"] += betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "kreditkonto_aktiva"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Kontogebuehr":
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Abschreibung":
        bank["einnahmenkonto"] -= betrag
        bank["kreditkonto_aktiva"] -= betrag
        soll_konto = "einnahmenkonto"
        haben_konto = "kreditkonto_aktiva"

    if soll_konto and haben_konto:
        buchung_entry = {
            "zeitstempel": zeitstempel,
            "vorgang": vorgang,
            "soll_konto": soll_konto,
            "soll_betrag": round(betrag, 2),
            "haben_konto": haben_konto,
            "haben_betrag": round(betrag, 2)
        }
        if referenz:
            buchung_entry["referenz"] = referenz
        bank["buchungen"].append(buchung_entry)

    speicherung.speichere_json(BANK_STATUS_FILE, bank)
    bilanz_pruefen(bank)

def bilanz_pruefen(bank):
    """Validiert die Bilanzgleichung: Aktiva = Passiva + G&V."""
    aktiva = round(bank["zentralbankkonto"] + bank["kreditkonto_aktiva"], 2)
    passiva_erfolg = round(bank["verpflichtungskonto"] + bank["einnahmenkonto"], 2)
    if aktiva != passiva_erfolg:
        print(f"WARNUNG: Bilanzungleichgewicht! Aktiva: {aktiva}, Passiva/G&V: {passiva_erfolg}")
        return False
    return True
