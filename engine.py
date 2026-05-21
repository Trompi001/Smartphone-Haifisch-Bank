import json
import os
from datetime import datetime, date
import konten
import kredit
import buchung
import speicherung


def _datum_aus_tx(tx):
    if tx.get("typ") == "zeit" and tx.get("datum"):
        return tx["datum"]
    zeitstempel = tx.get("zeitstempel")
    if zeitstempel and "T" in zeitstempel:
        return zeitstempel.split("T")[0]
    return zeitstempel

def erstelle_zusammenfassung(alle_transaktionen, simulation_start, simulation_end):
    konten_uebersicht = {}
    if os.path.exists("konten"):
        for datei in os.listdir("konten"):
            if not datei.endswith(".json"):
                continue
            try:
                with open(os.path.join("konten", datei), 'r', encoding='utf-8') as f:
                    konto = json.load(f)
            except Exception:
                continue

            iban = konto.get("konto_iban")
            if not iban:
                continue

            konten_uebersicht[iban] = {
                "name": konto.get("kunde", {}).get("name"),
                "kontostand": round(konto.get("kontostand", 0.0), 2),
                "kredit_stand": round(konto.get("kredit_stand", 0.0), 2),
                "status": konto.get("status"),
                "anzahl_transaktionen": len(konto.get("transaktionen", []))
            }

    bankkonten = speicherung.lade_json("bankkonten.json") or {}
    zusammenfassung = {
        "simulation_start": simulation_start,
        "simulation_end": simulation_end,
        "anzahl_kunden": len(konten_uebersicht),
        "anzahl_transaktionen": len(alle_transaktionen),
        "anzahl_buchungen": len(bankkonten.get("buchungen", [])),
        "kontostande": konten_uebersicht,
        "bankkonten": {
            "zentralbankkonto": round(bankkonten.get("zentralbankkonto", 0.0), 2),
            "verpflichtungskonto": round(bankkonten.get("verpflichtungskonto", 0.0), 2),
            "kreditkonto_aktiva": round(bankkonten.get("kreditkonto_aktiva", 0.0), 2),
            "einnahmenkonto": round(bankkonten.get("einnahmenkonto", 0.0), 2)
        }
    }

    speicherung.speichere_json("zusammenfassung.json", zusammenfassung)
    return zusammenfassung

def _lade_alle_ibans():
    """Lädt alle aktiven IBANs aus dem konten-Ordner."""
    ibans = []
    if os.path.exists("konten"):
        for datei in sorted(os.listdir("konten")):
            if datei.endswith(".json"):
                try:
                    with open(os.path.join("konten", datei), 'r', encoding='utf-8') as f:
                        daten = json.load(f)
                        if "konto_iban" in daten and daten.get("status") != "geschlossen":
                            ibans.append(daten["konto_iban"])
                except Exception:
                    pass
    return ibans

def _fuehre_monatsverarbeitung(monat_datum_str, alle_ibans):
    """Zinsen, Amortisation, Abschreibung für alle Konten."""
    for iban in alle_ibans:
        kredit.kredit_zinsen_berechnen(iban, monat_datum_str)
        kredit.kredit_amortisation(iban, monat_datum_str)
        kredit.kredit_abschreibung_pruefen(iban, monat_datum_str)

def _fuehre_quartalsverarbeitung(quartal_datum_str, alle_ibans):
    """Kontoführungsgebühr CHF 25 für alle Konten."""
    for iban in alle_ibans:
        kunden_konto = speicherung.lade_konto(iban)
        if kunden_konto:
            # Gebühr immer belasten, auch bei negativem Saldo (Spez. 2.2.5)
            kunden_konto["kontostand"] -= 25.0
            kunden_konto["transaktionen"].append({
                "zeitstempel": quartal_datum_str + "T08:00:00Z",
                "typ": "kontogebuehr",
                "betrag": -25.0,
                "saldo_nachher": kunden_konto["kontostand"],
                "status": "ausgefuehrt"
            })
            buchung.verbuchen("Kontogebuehr", 25.0,
                              zeitstempel=quartal_datum_str + "T08:00:00Z",
                              referenz="Quartalsgebühr")
            speicherung.speichere_konto(kunden_konto)

def verarbeite_periodische_aufgaben(datum_str):
    """
    Führt automatisierte Buchungen basierend auf dem Datum aus.
    """
    datum = datetime.strptime(datum_str, "%Y-%m-%d")
    alle_ibans = _lade_alle_ibans()

    # --- Täglich: Strafzinsen für gesperrte Konten ---
    for iban in alle_ibans:
        kredit.kredit_strafzinsen(iban, datum_str)

    # --- Monatlich: nur am Monatsersten ---
    if datum.day == 1:
        _fuehre_monatsverarbeitung(datum_str, alle_ibans)

    # --- Quartalsweise: Januar, April, Juli, Oktober (fixer Monatserster) ---
    if datum.day == 1 and datum.month in [1, 4, 7, 10]:
        _fuehre_quartalsverarbeitung(datum_str, alle_ibans)

iban_zaehler_global = 1

def verarbeite_tages_batch(tag_datum, tx_liste):
    """Verarbeitet den Tages-Batch in der korrekten Reihenfolge (a–f gemäss Spez. 2.7)."""
    global iban_zaehler_global

    # a) Kontoeröffnungen
    for tx in [t for t in tx_liste if t["typ"] == "konto_eroeffnen"]:
        konten.konto_eroeffnen(
            tx["kunde"],
            iban_zaehler=iban_zaehler_global,
            zeitstempel=tx["zeitstempel"]
        )
        iban_zaehler_global += 1

    # b) Alle Einzahlungen
    for tx in [t for t in tx_liste if t["typ"] == "ueberweisung_ein"]:
        konten.einzahlung_verbuchen(
            tx["ziel_iban"],
            tx["betrag"],
            tx["zeitstempel"],
            tx.get("referenz")
        )

    # c) Periodische Verarbeitungen (Zinsen, Amortisation, Gebühren, Strafzinsen)
    verarbeite_periodische_aufgaben(tag_datum)

    # d) Kreditanträge und Rückzahlungen
    for tx in [t for t in tx_liste if t["typ"] == "kredit_antrag"]:
        kredit.kredit_vergeben(tx["kunden_iban"], tx["betrag"], tx["zeitstempel"])

    # Kreditrueckzahlungen (Alias fuer Alt-Daten)
    for tx in [t for t in tx_liste if t["typ"] in ("kredit_rueckzahlung", "kredit_rueckzahl")]:
        kredit.kredit_rueckzahlung(
            tx["kunden_iban"],
            tx["betrag"],
            tx["zeitstempel"]
        )

    # e) Datenänderungen / Kontoschliessung
    # FIX: daten_aendern und konto_schliessen sind jetzt implementiert
    for tx in [t for t in tx_liste if t["typ"] == "daten_aendern"]:
        konten.kunden_daten_aendern(
            tx["kunden_iban"],
            tx.get("neue_daten", {}),
            tx["zeitstempel"]
        )

    for tx in [t for t in tx_liste if t["typ"] == "konto_schliessen"]:
        konten.konto_schliessen(tx["kunden_iban"], tx["zeitstempel"])

    # f) Alle Auszahlungen (ausgehende Überweisungen)
    # FIX: Interne Überweisungen werden hier NICHT separat behandelt –
    #      ueberweisung_ausfuehren erkennt interne Transfers selbst und bucht
    #      den Empfänger direkt, ohne eine zweite ueberweisung_ein-Transaktion
    #      in der Eingabedatei zu benötigen.
    for tx in [t for t in tx_liste if t["typ"] == "ueberweisung_aus"]:
        konten.ueberweisung_ausfuehren(
            tx["quell_iban"],
            tx["ziel_iban"],
            tx["betrag"],
            tx["zeitstempel"],
            tx.get("referenz")
        )

def main():
    """Startet die Simulation für die bereitgestellten Testdaten."""
    global iban_zaehler_global
    iban_zaehler_global = 1
    buchung.initialisiere_bank()

    transaktionen_ordner = "transaktionen"
    if not os.path.exists(transaktionen_ordner):
        print(f"Ordner '{transaktionen_ordner}' nicht gefunden.")
        return

    dateien = sorted([f for f in os.listdir(transaktionen_ordner) if f.endswith(".json")])

    alle_transaktionen = []
    simulation_start = None
    simulation_end = None

    for datei in dateien:
        monats_datei = os.path.join(transaktionen_ordner, datei)
        with open(monats_datei, 'r', encoding='utf-8') as f:
            transaktionen = json.load(f)

        for tx in transaktionen:
            alle_transaktionen.append(tx)
            datum = _datum_aus_tx(tx)
            if datum:
                if not simulation_start or datum < simulation_start:
                    simulation_start = datum
                if not simulation_end or datum > simulation_end:
                    simulation_end = datum

        # FIX: Datum wird aus dem zeit-Eintrag bestimmt, der VOR den anderen
        #      Transaktionen desselben Tages steht. Einträge ohne vorherigen
        #      zeit-Eintrag (z.B. konto_eroeffnen am Dateianfang) erhalten das
        #      Datum des ersten gefundenen zeit-Eintrags in der Datei.
        #      Damit werden alle konto_eroeffnen-Einträge korrekt dem
        #      ersten Arbeitstag zugeordnet.

        # Erstes Datum in der Datei vorausschauend bestimmen
        erstes_datum = None
        for tx in transaktionen:
            if tx.get("typ") == "zeit":
                erstes_datum = tx["datum"]
                break

        # Fallback: Dateiname als Monatsstart
        if not erstes_datum:
            erstes_datum = datei.replace(".json", "") + "-01"

        tages_batches = {}
        aktuelles_datum = erstes_datum

        for tx in transaktionen:
            if tx.get("typ") == "zeit":
                aktuelles_datum = tx["datum"]
            # zeit-Transaktionen selbst nicht in den Batch aufnehmen
            if tx.get("typ") == "zeit":
                continue
            if aktuelles_datum not in tages_batches:
                tages_batches[aktuelles_datum] = []
            tages_batches[aktuelles_datum].append(tx)

        for tag in sorted(tages_batches.keys()):
            verarbeite_tages_batch(tag, tages_batches[tag])

    if simulation_start and simulation_end:
        erstelle_zusammenfassung(alle_transaktionen, simulation_start, simulation_end)

if __name__ == "__main__":
    main()