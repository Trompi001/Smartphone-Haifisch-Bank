from datetime import datetime
import calendar
import speicherung
import buchung

def _parse_datum(zeitstempel):
    if not zeitstempel:
        return None
    ts = zeitstempel.replace("Z", "")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        try:
            return datetime.strptime(ts, "%Y-%m-%d")
        except ValueError:
            return None

def _add_monate(datum, monate):
    if not datum:
        return None
    jahr = datum.year + (datum.month - 1 + monate) // 12
    monat = (datum.month - 1 + monate) % 12 + 1
    tag = min(datum.day, calendar.monthrange(jahr, monat)[1])
    return datum.replace(year=jahr, month=monat, day=tag)

def kredit_vergeben(iban, betrag, zeitstempel):
    """
    Vergibt einen Kredit zwischen CHF 1'000 und 15'000.
    FIX: kredit_initial wird jetzt korrekt im Konto gespeichert.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False

    if not (1000 <= betrag <= 15000):
        return False
    if konto.get("kredit_stand", 0) > 0:
        return False

    # FIX: Originalbetrag für spätere Ratenberechnung speichern
    konto["kredit_initial"] = betrag
    konto["kontostand"] += betrag
    konto["kredit_stand"] = betrag

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_auszahlung",
        "betrag": betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    # Bearbeitungsgebühr CHF 250 sofort belasten
    konto["kontostand"] -= 250.0
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_gebuehr",
        "betrag": -250.0,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    buchung.verbuchen("Kreditauszahlung", betrag,
                      zeitstempel=zeitstempel, referenz=f"Kredit an {iban}")
    buchung.verbuchen("Kreditgebuehr", 250.0,
                      zeitstempel=zeitstempel, referenz="Bearbeitungsgebühr Kredit")

    speicherung.speichere_konto(konto)
    return True

def kredit_zinsen_berechnen(iban, zeitstempel):
    """
    Berechnet monatlich 15% p.a. Zinsen auf die Restschuld vor der Tilgung.
    Zinsen werden immer vom Kundenkonto abgezogen, auch wenn Saldo negativ wird.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return
    restschuld = konto.get("kredit_stand", 0)
    if restschuld <= 0:
        return

    zinsbetrag = round(restschuld * 0.15 / 12, 2)
    if zinsbetrag <= 0:
        return

    konto["kontostand"] -= zinsbetrag

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_zinsen",
        "betrag": -zinsbetrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    buchung.verbuchen("Kreditzinsen", zinsbetrag,
                      zeitstempel=zeitstempel + "T01:00:00Z",
                      referenz="Monatliche Kreditzinsen")
    speicherung.speichere_konto(konto)

def kredit_amortisation(iban, zeitstempel):
    """
    Lineare Amortisation über 12 Monate.
    FIX: Verwendet kredit_initial statt Hardcode-Fallback.
    Bei mangelnder Deckung wird das Konto gesperrt.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return
    if konto.get("kredit_stand", 0) <= 0:
        return
    if konto.get("status") == "gesperrt":
        return

    kredit_initial = konto.get("kredit_initial", 0)
    if kredit_initial <= 0:
        return

    rate = min(round(kredit_initial / 12, 2), round(konto.get("kredit_stand", 0), 2))
    if rate <= 0:
        return

    if konto["kontostand"] >= rate:
        konto["kontostand"] -= rate
        konto["kredit_stand"] = max(0, round(konto["kredit_stand"] - rate, 2))
        konto["transaktionen"].append({
            "zeitstempel": zeitstempel,
            "typ": "kredit_amortisation",
            "betrag": -rate,
            "saldo_nachher": konto["kontostand"],
            "status": "ausgefuehrt"
        })

        if konto["kredit_stand"] == 0:
            konto["kredit_initial"] = 0.0

        buchung.verbuchen("Kredittilgung", rate,
                          zeitstempel=zeitstempel + "T01:10:00Z",
                          referenz="Kredittilgung")
    else:
        konto["status"] = "gesperrt"
        konto["transaktionen"].append({
            "zeitstempel": zeitstempel + "T01:15:00Z",
            "typ": "konto_gesperrt",
            "betrag": 0.0,
            "saldo_nachher": konto["kontostand"],
            "status": "ausgefuehrt",
            "grund": "Amortisation nicht moeglich"
        })

    speicherung.speichere_konto(konto)

def kredit_strafzinsen(iban, zeitstempel):
    """
    Täglicher Strafzins von 30% p.a. auf die Restschuld bei gesperrten Konten.
    Erhöht die Restschuld (Kreditkonto), nicht den Kontostand des Kunden.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return
    if konto.get("status") != "gesperrt":
        return
    restschuld = konto.get("kredit_stand", 0)
    if restschuld <= 0:
        return

    strafzins = round(restschuld * (0.30 / 365), 2)
    if strafzins <= 0:
        return

    konto["kredit_stand"] = round(konto["kredit_stand"] + strafzins, 2)

    # Transaktion im Konto aufzeichnen
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel + "T02:00:00Z",
        "typ": "strafzinsen",
        "betrag": -strafzins,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    buchung.verbuchen("Strafzinsen", strafzins,
                      zeitstempel=zeitstempel + "T02:00:00Z",
                      referenz="Tägliche Strafzinsen")
    speicherung.speichere_konto(konto)

def kredit_rueckzahlung(iban, betrag, zeitstempel):
    """
    Freiwillige (Teil-)Rückzahlung eines Kredits.
    FIX: Funktion war nicht implementiert.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False

    restschuld = konto.get("kredit_stand", 0)
    if restschuld <= 0:
        return False

    # Rückzahlung auf maximal die Restschuld begrenzen
    rueckzahlung = min(betrag, restschuld)

    if konto["kontostand"] < rueckzahlung:
        konto["transaktionen"].append({
            "zeitstempel": zeitstempel,
            "typ": "kredit_rueckzahlung",
            "betrag": -rueckzahlung,
            "saldo_nachher": konto["kontostand"],
            "status": "abgelehnt",
            "grund": "Deckung nicht ausreichend"
        })
        speicherung.speichere_konto(konto)
        return False

    konto["kontostand"] -= rueckzahlung
    konto["kredit_stand"] = round(restschuld - rueckzahlung, 2)

    # Wenn Kredit vollständig zurückgezahlt, kredit_initial zurücksetzen
    if konto["kredit_stand"] == 0:
        konto["kredit_initial"] = 0.0

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_rueckzahlung",
        "betrag": -rueckzahlung,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt"
    })

    buchung.verbuchen("Kreditrueckzahlung", rueckzahlung,
                      zeitstempel=zeitstempel,
                      referenz="Freiwillige Kreditrückzahlung")

    speicherung.speichere_konto(konto)
    return True

def kredit_abschreibung_pruefen(iban, zeitstempel):
    """
    Prüft, ob ein Kredit seit 6 Monaten nicht mehr bedient wurde.
    Falls ja, wird der Restbetrag als Verlust abgeschrieben.
    """
    konto = speicherung.lade_konto(iban)
    if not konto or konto.get("kredit_stand", 0) <= 0:
        return

    pruef_datum = _parse_datum(zeitstempel)
    if not pruef_datum:
        return

    # Letzte erfolgreiche Tilgung oder Kreditauszahlung suchen
    letzte_zahlung = None
    for tx in konto.get("transaktionen", []):
        if tx.get("typ") in ("kredit_amortisation", "kredit_rueckzahlung") \
                and tx.get("status") == "ausgefuehrt":
            tx_datum = _parse_datum(tx.get("zeitstempel"))
            if tx_datum and (letzte_zahlung is None or tx_datum > letzte_zahlung):
                letzte_zahlung = tx_datum

    if letzte_zahlung is None:
        for tx in konto.get("transaktionen", []):
            if tx.get("typ") == "kredit_auszahlung" and tx.get("status") == "ausgefuehrt":
                tx_datum = _parse_datum(tx.get("zeitstempel"))
                if tx_datum and (letzte_zahlung is None or tx_datum > letzte_zahlung):
                    letzte_zahlung = tx_datum

    if letzte_zahlung is None:
        return

    faellig_ab = _add_monate(letzte_zahlung, 6)
    if (pruef_datum.year, pruef_datum.month) < (faellig_ab.year, faellig_ab.month):
        return

    restbetrag = konto.get("kredit_stand", 0)
    if restbetrag <= 0:
        return

    konto["kredit_stand"] = 0
    konto["kredit_initial"] = 0.0
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "kredit_abschreibung",
        "betrag": 0.0,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "grund": "Abschreibung nach 6 Monaten ohne Zahlung"
    })

    buchung.verbuchen("Abschreibung", restbetrag,
                      zeitstempel=zeitstempel,
                      referenz="Kredit abgeschrieben")
    speicherung.speichere_konto(konto)
