import speicherung
import buchung

def kredit_vergeben(iban, betrag, zeitstempel):
    """
    Vergibt einen Kredit zwischen CHF 1'000 und 15'000.
    Prüft, ob bereits ein laufender Kredit besteht.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False

    # Prüfung der Kreditbedingungen
    if not (1000 <= betrag <= 15000):
        return False
    if konto.get("kredit_stand", 0) > 0:
        return False # Maximal ein laufender Kredit pro Kunde

    # 1. Kreditbetrag auszahlen
    konto["kontostand"] += betrag
    konto["kredit_stand"] = betrag
    
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_auszahlung",
        "betrag": betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    # 2. Bearbeitungsgebühr CHF 250 sofort belasten
    konto["kontostand"] -= 250.0
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel, # Geringfügig späterer Zeitstempel in Realität
        "typ": "kredit_gebuehr",
        "betrag": -250.0,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    # Buchung im Bankensystem
    buchung.verbuchen("Kreditauszahlung", betrag)
    buchung.verbuchen("Kreditgebuehr", 250.0)

    speicherung.speichere_konto(konto)
    return True

def kredit_zinsen_berechnen(iban, zeitstempel):
    """
    Berechnet monatlich 15% p.a. Zinsen auf die Restschuld vor der Tilgung.
    Zinsen werden vom Kundenkonto abgezogen.
    """
    konto = speicherung.lade_konto(iban)
    restschuld = konto.get("kredit_stand", 0)
    
    if restschuld <= 0:
        return

    zinsbetrag = round(restschuld * (0.15 / 12), 2)
    konto["kontostand"] -= zinsbetrag
    
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_zinsen",
        "betrag": -zinsbetrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })
    
    buchung.verbuchen("Kreditzinsen", zinsbetrag)
    speicherung.speichere_konto(konto)

def kredit_amortisation(iban, zeitstempel):
    """
    Lineare Amortisation über 12 Monate.
    Bei mangelnder Deckung wird das Konto gesperrt.
    """
    konto = speicherung.lade_konto(iban)
    # Annahme: Der ursprüngliche Kreditbetrag muss für die lineare Rate bekannt sein
    # In einer JSON-Struktur sollte dieser beim kredit_antrag gespeichert werden.
    ursprünglicher_betrag = konto.get("kredit_initial", 10000) # Beispielwert
    rate = round(ursprünglicher_betrag / 12, 2)

    if konto["kontostand"] >= rate:
        konto["kontostand"] -= rate
        konto["kredit_stand"] -= rate
        status = "ausgefuehrt"
        # Prüfung auf Entsperrung
        if konto["status"] == "gesperrt":
            konto["status"] = "aktiv"
    else:
        # Zahlungsausfall[cite: 1]
        konto["status"] = "gesperrt"
        status = "abgelehnt"

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_amortisation",
        "betrag": -rate if status == "ausgefuehrt" else 0.0,
        "saldo_nachher": konto["kontostand"],
        "status": status
    })
    
    if status == "ausgefuehrt":
        buchung.verbuchen("Kredittilgung", rate)
    
    speicherung.speichere_konto(konto)

def kredit_strafzinsen(iban, zeitstempel):
    """
    Täglicher Strafzins von 30% p.a. auf die Restschuld bei gesperrten Konten.
    Erhöht die Restschuld (Kreditkonto), nicht das Kundenkonto.
    """
    konto = speicherung.lade_konto(iban)
    if konto["status"] == "gesperrt":
        strafzins = round(konto["kredit_stand"] * (0.30 / 365), 2)
        konto["kredit_stand"] += strafzins
        # Keine Belastung des Kundenkontos, nur Buchung im Bankensystem
        buchung.verbuchen("Strafzinsen", strafzins)
        speicherung.speichere_konto(konto)