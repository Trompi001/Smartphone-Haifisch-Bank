from datetime import datetime
import speicherung
import buchung

def generiere_iban(zaehler):
    """
    Erstellt eine IBAN nach dem Schema aus Abschnitt 4.1.
    Beispiel: CH00 0076 2000 0000 0001 0
    """
    land = "CH"
    pruefziffer_bank = "00"
    clearing = "00762"
    # 12-stellig, links mit Nullen aufgefüllt
    konto_nr = f"{zaehler:012d}"
    # Letzte Stelle der Kontonummer als Prüfziffer
    letzte_stelle = konto_nr[-1]
    
    # Formatierung für die Speicherung (ohne Leerzeichen für Dateinamen)
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
        "status": "aktiv",
        "transaktionen": []
    }
    
    # Initiale Transaktion aufzeichnen
    eroeffnung_tx = {
        "zeitstempel": zeitstempel, # Platzhalter für Engine-Zeit
        "typ": "konto_eroeffnen",
        "betrag": 0.0,
        "saldo_nachher": 0.0,
        "status": "ausgefuehrt"
    }
    neues_konto["transaktionen"].append(eroeffnung_tx)
    
    speicherung.speichere_konto(neues_konto)
    return neue_iban

def einzahlung_verbuchen(iban, betrag, zeitstempel, referenz="Einzahlung"):
    """
    Verbucht eine Gutschrift auf dem Kundenkonto (z.B. Lohn).
    """
    konto = speicherung.lade_konto(iban)
    if not konto:
        return False
    
    konto["kontostand"] += betrag
    
    historie_eintrag = {
        "zeitstempel": zeitstempel,
        "typ": "ueberweisung_ein",
        "betrag": betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "referenz": referenz
    }
    konto["transaktionen"].append(historie_eintrag)
    
    # Gegenbuchung im Buchungssystem
    buchung.verbuchen("Einzahlung", betrag, zeitstempel=zeitstempel, referenz=referenz)
    
    speicherung.speichere_konto(konto)
    return True

def ueberweisung_ausfuehren(von_iban, nach_iban, betrag, zeitstempel, referenz):
    """
    Führt eine ausgehende Überweisung mit Deckungsprüfung aus.
    """
    konto = speicherung.lade_konto(von_iban)
    if not konto or konto["status"] == "gesperrt":
        return False # Oder abgelehnt-Eintrag erstellen
    
    # Deckungsprüfung: Kontokorrent darf nicht negativ werden (ausser Gebühren)
    if konto["kontostand"] < betrag:
        # Abgelehnte Transaktion speichern
        historie_eintrag = {
            "zeitstempel": zeitstempel,
            "typ": "ueberweisung_aus",
            "betrag": betrag,
            "saldo_nachher": konto["kontostand"],
            "status": "abgelehnt",
            "grund": "Deckung nicht ausreichend"
        }
        konto["transaktionen"].append(historie_eintrag)
        speicherung.speichere_konto(konto)
        return False

    konto["kontostand"] -= betrag
    
    historie_eintrag = {
        "zeitstempel": zeitstempel,
        "typ": "ueberweisung_aus",
        "betrag": -betrag,
        "saldo_nachher": konto["kontostand"],
        "status": "ausgefuehrt",
        "referenz": referenz
    }
    konto["transaktionen"].append(historie_eintrag)
    
    # Interne vs. Externe Buchung prüfen
    is_intern = nach_iban.startswith("CH0000762")
    buchung.verbuchen("Auszahlung", betrag, intern=is_intern, zeitstempel=zeitstempel, referenz=referenz)
    
    speicherung.speichere_konto(konto)
    return True