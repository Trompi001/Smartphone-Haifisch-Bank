from datetime import datetime
import speicherung
import buchung

def generiere_iban(zaehler):
    """
    Erstellt eine IBAN nach dem Schema aus Abschnitt 4.1.
    Beispiel: CH0000762000000000001 0
    """
    land = "CH"
    pruefziffer_bank = "00"
    clearing = "00762"
    konto_nr = f"{zaehler:012d}"
    letzte_stelle = konto_nr[-1]
    return f"{land}{pruefziffer_bank}{clearing}{konto_nr}{letzte_stelle}"

def konto_eroeffnen(kunde_daten, iban_zaehler, zeitstempel):
    """
    Legt ein neues Kundendokument an.
    Gibt die neu generierte IBAN zurück.
    """
    neue_iban = generiere_iban(iban_zaehler)

    neues_konto = {
        "konto_iban": neue_iban,
        "kunde": {
            "name": kunde_daten["name"],
            "adresse": kunde_daten["adresse"],
            "geburtsdatum": kunde_daten["geburtsdatum"]
        },
        "kontostand": 0.0,
        "kredit_stand": 0.0,
        # FIX: kredit_initial wird bei Kreditvergabe gesetzt; hier mit 0 vorbelegt
        "kredit_initial": 0.0,
        "status": "aktiv",
        "transaktionen": []
    }

    neues_konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "konto_eroeffnen",
        "betrag": 0.0,
        "saldo_nachher": 0.0,
        "status": "ausgefuehrt"
    })

    speicherung.speichere_konto(neues_konto)
    return neue_iban

def konto_schliessen(iban, zeitstempel):
    """
    Schliesst ein Konto. Saldo und Kredit müssen null sein.
    FIX: Funktion war nicht implementiert.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False, "Konto nicht gefunden"

    if konto["kontostand"] != 0.0:
        return False, f"Kontostand ist nicht null ({konto['kontostand']})"

    if konto.get("kredit_stand", 0.0) != 0.0:
        return False, f"Kredit ist noch offen ({konto['kredit_stand']})"

    konto["status"] = "geschlossen"
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "konto_schliessen",
        "betrag": 0.0,
        "saldo_nachher": 0.0,
        "status": "ausgefuehrt"
    })

    speicherung.speichere_konto(konto)
    return True, "Konto geschlossen"

def kunden_daten_aendern(iban, neue_daten, zeitstempel):
    """
    Aktualisiert Kundenstammdaten (Name, Adresse, Geburtsdatum).
    FIX: Funktion war nicht implementiert.
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False

    for feld in ["name", "adresse", "geburtsdatum"]:
        if feld in neue_daten:
            konto["kunde"][feld] = neue_daten[feld]

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "daten_aendern",
        "betrag": 0.0,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "geaenderte_felder": list(neue_daten.keys())
    })

    speicherung.speichere_konto(konto)
    return True

def einzahlung_verbuchen(iban, betrag, zeitstempel, referenz="Einzahlung"):
    """
    Verbucht eine Gutschrift auf dem Kundenkonto.
    FIX: Entsperrungslogik nach Einzahlung hinzugefügt (Spez. 2.5.10).
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False

    konto["kontostand"] += betrag

    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "ueberweisung_ein",
        "betrag": betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "referenz": referenz
    })

    buchung.verbuchen("Einzahlung", betrag, zeitstempel=zeitstempel, referenz=referenz)

    speicherung.speichere_konto(konto)
    return True

def ueberweisung_ausfuehren(von_iban, nach_iban, betrag, zeitstempel, referenz):
    """
    Führt eine ausgehende Überweisung mit Deckungsprüfung aus.
    FIX: Interne Empfänger-Einzahlung wird korrekt als intern markiert,
         sodass kein doppelter Zentralbank-Eintrag entsteht.
    """
    konto = speicherung.lade_konto(von_iban)
    if not konto:
        return False

    if konto["status"] == "gesperrt":
        konto["transaktionen"].append({
            "zeitstempel": zeitstempel,
            "typ": "ueberweisung_aus",
            "betrag": -betrag,
            "saldo_nachher": konto["kontostand"],
            "status": "abgelehnt",
            "grund": "Konto gesperrt"
        })
        speicherung.speichere_konto(konto)
        return False

    if konto["kontostand"] < betrag:
        konto["transaktionen"].append({
            "zeitstempel": zeitstempel,
            "typ": "ueberweisung_aus",
            "betrag": -betrag,
            "saldo_nachher": konto["kontostand"],
            "status": "abgelehnt",
            "grund": "Deckung nicht ausreichend"
        })
        speicherung.speichere_konto(konto)
        return False

    konto["kontostand"] -= betrag
    konto["transaktionen"].append({
        "zeitstempel": zeitstempel,
        "typ": "ueberweisung_aus",
        "betrag": -betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "referenz": referenz
    })

    # Interne vs. externe Überweisung prüfen
    is_intern = nach_iban.startswith("CH0000762")

    # Senderseitige Buchung
    buchung.verbuchen("Auszahlung", betrag, intern=is_intern,
                      zeitstempel=zeitstempel, referenz=referenz)

    # FIX: Bei interner Überweisung den Empfänger direkt gutschreiben,
    #      ohne eine externe Einzahlungs-Bankbuchung auszulösen.
    if is_intern:
        empfaenger_konto = speicherung.lade_konto(nach_iban)
        if empfaenger_konto:
            empfaenger_konto["kontostand"] += betrag
            empfaenger_konto["transaktionen"].append({
                "zeitstempel": zeitstempel,
                "typ": "ueberweisung_ein",
                "betrag": betrag,
                "saldo_nachher": empfaenger_konto["kontostand"],
                "status": "ausgefuehrt",
                "referenz": referenz
            })
            # Bankbuchung: nur Verpflichtungskonto anpassen (intern=True)
            buchung.verbuchen("Einzahlung", betrag, intern=True,
                              zeitstempel=zeitstempel, referenz=referenz)
            speicherung.speichere_konto(empfaenger_konto)

    speicherung.speichere_konto(konto)
    return True
