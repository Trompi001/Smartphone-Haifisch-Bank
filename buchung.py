from datetime import datetime
import speicherung

# Pfad zur zentralen Bankbilanz
BANK_STATUS_FILE = "bankkonten.json"

def initialisiere_bank():
    """Erstellt die initialen Bankkonten, falls noch nicht vorhanden."""
    status = {
        "zentralbankkonto": 0.0,    # Aktiva
        "verpflichtungskonto": 0.0, # Passiva (Kundenguthaben)
        "kreditkonto_aktiva": 0.0,  # Aktiva (Ausstehende Kredite)
        "einnahmenkonto": 0.0,      # G&V (Gewinn/Verlust)
        "buchungen": []
    }
    speicherung.speichere_json(BANK_STATUS_FILE, status)
    return status

def verbuchen(vorgang, betrag, intern=False, zeitstempel=None, referenz=None):
    """
    Aktualisiert die internen Bankkonten basierend auf Tabelle 3.
    """
    bank = speicherung.lade_json(BANK_STATUS_FILE)
    if not bank:
        bank = initialisiere_bank()
        
    soll_konto = None
    haben_konto = None
    if not zeitstempel:
        zeitstempel = datetime.now().isoformat() + "Z"

    if vorgang == "Einzahlung":
        # Zentralbank + / Verpflichtung +
        bank["zentralbankkonto"] += betrag
        bank["verpflichtungskonto"] += betrag
        soll_konto = "zentralbankkonto"
        haben_konto = "verpflichtungskonto"

    elif vorgang == "Auszahlung":
        if not intern:
            # Verpflichtung - / Zentralbank - (Achtung: Minus auf Passiv = Soll, Minus auf Aktiv = Haben)
            bank["verpflichtungskonto"] -= betrag
            bank["zentralbankkonto"] -= betrag
            soll_konto = "verpflichtungskonto"
            haben_konto = "zentralbankkonto"
        else:
            # Interne Überweisung: Keine Buchung auf Zentralbankkonto
            pass

    elif vorgang == "Kreditauszahlung":
        # Kreditkonto + / Verpflichtung +
        bank["kreditkonto_aktiva"] += betrag
        bank["verpflichtungskonto"] += betrag
        soll_konto = "kreditkonto_aktiva"
        haben_konto = "verpflichtungskonto"

    elif vorgang == "Kreditgebuehr":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Kredittilgung":
        # Verpflichtung - / Kreditkonto -
        bank["verpflichtungskonto"] -= betrag
        bank["kreditkonto_aktiva"] -= betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "kreditkonto_aktiva"

    elif vorgang == "Kreditzinsen":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Strafzinsen":
        # Kreditkonto + / Einnahmen +
        bank["kreditkonto_aktiva"] += betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "kreditkonto_aktiva"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Kontogebuehr":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag
        soll_konto = "verpflichtungskonto"
        haben_konto = "einnahmenkonto"

    elif vorgang == "Abschreibung":
        # Einnahmen - / Kreditkonto -
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
    """Validiert die Bilanzgleichung: Aktiva = Passiva."""
    aktiva = round(bank["zentralbankkonto"] + bank["kreditkonto_aktiva"], 2)
    passiva_erfolg = round(bank["verpflichtungskonto"] + bank["einnahmenkonto"], 2)
    
    if aktiva != passiva_erfolg:
        print(f"WARNUNG: Bilanzungleichgewicht! Aktiva: {aktiva}, Passiva/G&V: {passiva_erfolg}")
        return False
    return True