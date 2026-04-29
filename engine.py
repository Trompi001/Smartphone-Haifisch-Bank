import json
import os
from datetime import datetime

# Import der noch zu erstellenden Module
# import konten
# import kredit
# import buchung
# import speicherung

def lade_transaktionen(dateipfad):
    """Liest eine monatliche JSON-Datei ein."""
    if not os.path.exists(dateipfad):
        print(f"Datei {dateipfad} nicht gefunden.")
        return []
    with open(dateipfad, 'r', encoding='utf-8') as f:
        return json.load(f)

def gruppiere_nach_tag(transaktionen):
    """
    Gruppiert Transaktionen eines Monats in Tages-Batches.
    Nutzt das 'datum' der zeit-Transaktion oder extrahiert es aus dem zeitstempel.
    """
    tage = {}
    aktueller_tag = None
    
    for tx in transaktionen:
        # Wenn eine Zeit-Transaktion kommt, aktualisieren wir das Datum
        if tx.get("typ") == "zeit":
            aktueller_tag = tx.get("datum")
        
        # Falls keine Zeit-Transaktion am Anfang steht, Zeitstempel nutzen
        tag_key = aktueller_tag or tx["zeitstempel"][:10]
        
        if tag_key not in tage:
            tage[tag_key] = []
        tage[tag_key].append(tx)
    return tage

def verarbeite_tages_batch(tag, tx_liste):
    """
    Verarbeitet alle Transaktionen eines Tages in der festen 
    Reihenfolge (a-f) gemäß Spezifikation 2.7
    """
    print(f"--- Verarbeite Tag: {tag} ---")
    
    # Definition der Prioritäten gemäß Abschnitt 2.7
    prioritaet = {
        "konto_eroeffnen": 1,
        "ueberweisung_ein": 2,
        "periodische_verarbeitung": 3, # Zinsen, Amortisation etc.
        "kredit_antrag": 4,
        "kredit_rueckzahl": 4,
        "daten_aendern": 5,
        "konto_schliessen": 5,
        "ueberweisung_aus": 6
    }

    # 1. Periodische Verarbeitungen müssen durch die Zeit-Transaktion angestoßen werden,
    # aber erst nach den Einzahlungen erfolgen.

    # Sortierung der Liste basierend auf der Priorität
    # Transaktionen ohne explizite Prio werden ans Ende sortiert
    sortierte_tx = sorted(tx_liste, key=lambda x: prioritaet.get(x["typ"], 99))

    for tx in sortierte_tx:
        typ = tx["typ"]
        
        if typ == "zeit":
            # Zeit-Transaktion stellt interne Uhr um
            print(f"Systemzeit auf {tx['datum']} gestellt.")
            # Hier würden später die periodischen Berechnungen folgen (Zinsen, etc.)
            continue
            
        # Dispatch-Logik an die anderen Module
        if typ == "konto_eroeffnen":
            # konten.konto_eroeffnen(tx["kunde"])
            pass
        elif typ == "ueberweisung_ein":
            # konten.einzahlung_verbuchen(tx["ziel_iban"], tx["betrag"])
            pass
        elif typ == "ueberweisung_aus":
            # konten.ueberweisung_ausfuehren(tx["quell_iban"], tx["ziel_iban"], tx["betrag"])
            pass
        # ... weitere Typen entsprechend Tabelle 1

def run_simulation(dateiliste):
    """Hauptschleife über alle Monatsdateien."""
    for datei in dateiliste:
        alle_tx = lade_transaktionen(datei)
        tages_batches = gruppiere_nach_tag(alle_tx)
        
        # Sortierte Verarbeitung der Tage eines Monats
        for tag in sorted(tages_batches.keys()):
            verarbeite_tages_batch(tag, tages_batches[tag])

# Beispielaufruf für deine Datei
# run_simulation(["transaktionen/2026-01.json"])