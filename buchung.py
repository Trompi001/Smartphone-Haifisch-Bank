import speicherung

# Pfad zur zentralen Bankbilanz
BANK_STATUS_FILE = "konten/bank_status.json"

def initialisiere_bank():
    """Erstellt die initialen Bankkonten, falls noch nicht vorhanden."""
    status = {
        "zentralbankkonto": 0.0,    # Aktiva
        "verpflichtungskonto": 0.0, # Passiva (Kundenguthaben)
        "kreditkonto_bank": 0.0,    # Aktiva (Ausstehende Kredite)
        "einnahmenkonto": 0.0       # G&V (Gewinn/Verlust)
    }
    speicherung.speichere_json(BANK_STATUS_FILE, status)
    return status

def verbuchen(vorgang, betrag, intern=False):
    """
    Aktualisiert die internen Bankkonten basierend auf Tabelle 3.
    """
    bank = speicherung.lade_json(BANK_STATUS_FILE)
    if not bank:
        bank = initialisiere_bank()

    if vorgang == "Einzahlung":
        # Zentralbank + / Verpflichtung +
        bank["zentralbankkonto"] += betrag
        bank["verpflichtungskonto"] += betrag

    elif vorgang == "Auszahlung":
        if not intern:
            # Verpflichtung - / Zentralbank -
            bank["verpflichtungskonto"] -= betrag
            bank["zentralbankkonto"] -= betrag
        else:
            # Interne Überweisung: Keine Buchung auf Zentralbankkonto
            pass

    elif vorgang == "Kreditauszahlung":
        # Kreditkonto + / Verpflichtung +
        bank["kreditkonto_bank"] += betrag
        bank["verpflichtungskonto"] += betrag

    elif vorgang == "Kreditgebuehr":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag

    elif vorgang == "Kredittilgung":
        # Verpflichtung - / Kreditkonto -
        bank["verpflichtungskonto"] -= betrag
        bank["kreditkonto_bank"] -= betrag

    elif vorgang == "Kreditzinsen":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag

    elif vorgang == "Strafzinsen":
        # Kreditkonto + / Einnahmen +
        bank["kreditkonto_bank"] += betrag
        bank["einnahmenkonto"] += betrag

    elif vorgang == "Kontogebuehr":
        # Verpflichtung - / Einnahmen +
        bank["verpflichtungskonto"] -= betrag
        bank["einnahmenkonto"] += betrag

    elif vorgang == "Abschreibung":
        # Einnahmen - / Kreditkonto -
        bank["einnahmenkonto"] -= betrag
        bank["kreditkonto_bank"] -= betrag

    speicherung.speichere_json(BANK_STATUS_FILE, bank)
    bilanz_pruefen(bank)

def bilanz_pruefen(bank):
    """Validiert die Bilanzgleichung: Aktiva = Passiva."""
    aktiva = round(bank["zentralbankkonto"] + bank["kreditkonto_bank"], 2)
    passiva_erfolg = round(bank["verpflichtungskonto"] + bank["einnahmenkonto"], 2)
    
    if aktiva != passiva_erfolg:
        print(f"WARNUNG: Bilanzungleichgewicht! Aktiva: {aktiva}, Passiva/G&V: {passiva_erfolg}")
        return False
    return True