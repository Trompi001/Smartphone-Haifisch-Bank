import json
import os
from datetime import datetime
import konten
import kredit
import buchung
import speicherung

def verarbeite_periodische_aufgaben(datum_str, bank_daten):
    """
    Führt automatisierte Buchungen basierend auf dem Datum aus.
    Wird nach den Einzahlungen des Tages angestossen.
    """
    datum = datetime.strptime(datum_str, "%Y-%m-%d")
    
    # IBANs laden, indem wir alle Kundenkonten kurz einlesen
    alle_ibans = []
    if os.path.exists("konten"):
        for datei in os.listdir("konten"):
            if datei.endswith(".json") and datei != "bankkonten.json":
                try:
                    with open(os.path.join("konten", datei), 'r', encoding='utf-8') as f:
                        daten = json.load(f)
                        if "konto_iban" in daten:
                            alle_ibans.append(daten["konto_iban"])
                except Exception:
                    pass

    for iban in alle_ibans:
        # 1. Täglich: Strafzinsen bei gesperrten Konten
        kredit.kredit_strafzinsen(iban, datum_str)
        
        # 2. Monatlich (am 1. des Monats): Kreditzinsen & Amortisation
        if datum.day == 1:
            # Reihenfolge beachten: erst Zinsen, dann Amortisation
            kredit.kredit_zinsen_berechnen(iban, datum_str)
            kredit.kredit_amortisation(iban, datum_str)
            # Prüfung auf Abschreibung nach 6 Monaten ohne Zahlung
            kredit.kredit_abschreibung_pruefen(iban, datum_str)
            
        # 3. Quartalsweise: Kontoführungsgebühr CHF 25
        # (Januar, April, Juli, Oktober)
        if datum.day == 1 and datum.month in [1, 4, 7, 10]:
            kunden_konto = speicherung.lade_konto(iban)
            if kunden_konto:
                kunden_konto["kontostand"] -= 25.0
                kunden_konto["transaktionen"].append({
                    "zeitstempel": datum_str + "T08:00:00Z",
                    "typ": "kontogebuehr",
                    "betrag": -25.0,
                    "saldo_nachher": kunden_konto["kontostand"],
                    "status": "ausgefuehrt"
                })
                buchung.verbuchen("Kontogebuehr", 25.0, zeitstempel=datum_str + "T08:00:00Z", referenz="Quartalsgebühr")
                speicherung.speichere_konto(kunden_konto)

iban_zaehler_global = 1

def verarbeite_tages_batch(tag_datum, tx_liste):
    global iban_zaehler_global
    """Verarbeitet den Tages-Batch in der korrekten Reihenfolge."""
    
    # a) Kontoeröffnungen
    for tx in [t for t in tx_liste if t["typ"] == "konto_eroeffnen"]:
        # zaehler wird global verwaltet
        konten.konto_eroeffnen(tx["kunde"], iban_zaehler=iban_zaehler_global, zeitstempel=tx["zeitstempel"])
        iban_zaehler_global += 1

    # b) Alle Einzahlungen
    for tx in [t for t in tx_liste if t["typ"] == "ueberweisung_ein"]:
        konten.einzahlung_verbuchen(tx["ziel_iban"], tx["betrag"], tx["zeitstempel"], tx.get("referenz"))

    # c) Periodische Verarbeitungen (Zinsen, Gebühren etc.)
    verarbeite_periodische_aufgaben(tag_datum, {})

    # d) Kreditanträge und Rückzahlungen
    for tx in [t for t in tx_liste if t["typ"] == "kredit_antrag"]:
        kredit.kredit_vergeben(tx["kunden_iban"], tx["betrag"], tx["zeitstempel"])
    for tx in [t for t in tx_liste if t["typ"] == "kredit_rueckzahl"]:
        # Logik für freiwillige Rückzahlung
        pass

    # e) Datenänderungen / Schliessungen
    # (Logik hier implementieren)

    # f) Alle Auszahlungen
    for tx in [t for t in tx_liste if t["typ"] == "ueberweisung_aus"]:
        konten.ueberweisung_ausfuehren(tx["quell_iban"], tx["ziel_iban"], tx["betrag"], tx["zeitstempel"], tx.get("referenz"))

def main():
    """Startet die Simulation für die bereitgestellten Testdaten."""
    # Initialisierung
    buchung.initialisiere_bank()
    
    # Alle Transaktionsdateien aus dem Ordner "transaktionen" laden und sortieren
    transaktionen_ordner = "transaktionen"
    if not os.path.exists(transaktionen_ordner):
        return

    dateien = sorted([f for f in os.listdir(transaktionen_ordner) if f.endswith(".json")])

    for datei in dateien:
        monats_datei = os.path.join(transaktionen_ordner, datei)
        with open(monats_datei, 'r', encoding='utf-8') as f:
            transaktionen = json.load(f)
            
        tages_batches = {}
        aktuelles_datum = datei.replace(".json", "") + "-01" # Default falls kein Zeit-Tag existiert
        
        for tx in transaktionen:
            if tx.get("typ") == "zeit":
                aktuelles_datum = tx["datum"]
            if aktuelles_datum not in tages_batches:
                tages_batches[aktuelles_datum] = []
            tages_batches[aktuelles_datum].append(tx)
            
        for tag in sorted(tages_batches.keys()):
            verarbeite_tages_batch(tag, tages_batches[tag])

if __name__ == "__main__":
    main()