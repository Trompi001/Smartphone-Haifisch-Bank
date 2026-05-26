# Smartphone-Haifisch-Bank

Willkommen im Repository der **Smartphone-Haifisch-Bank**. Dieses Projekt simuliert ein grundlegendes Bankensystem, das Transaktionen für Kundenkonten verarbeitet, Kredite verwaltet und die interne doppelte Buchführung einer Bank abbildet. 

## Architektur & Modulübersicht

Die Anwendung ist modular aufgebaut und folgt einem **strikt funktionalen Ansatz** (keine Klassen, keine objektorientierte Programmierung gemäss den Vorgaben). Die Datenhaltung basiert vollständig auf verschachtelten Python-Dictionaries und Listen. Die Separation of Concerns wird durch folgende Skripte und Funktionen umgesetzt:

- **`engine.py` (Steuerung & Batch-Verarbeitung):**  
  Die Kernschleife der Simulation. Hier werden eingehende Transaktions-Batches verarbeitet. Sie sorgt für die korrekte Reihenfolge der Buchungen gemäss Spezifikation (Abschnitt 2.7): 1. Kontoeröffnungen -> 2. Einzahlungen -> 3. Periodische Verarbeitungen -> 4. Kreditanträge und -rückzahlungen -> 5. Datenänderungen und -schliessungen -> 6. Auszahlungen.

- **`konten.py` (Kundenverwaltung):**  
  Zuständig für das operative Endkundengeschäft. Hier werden IBANs generiert, Konten eröffnet/geschlossen, Kundendaten geändert sowie klassische Ein- und Auszahlungen (inklusive Überweisungen zwischen Kunden) geprüft und ausgeführt.

- **`kredit.py` (Kreditwesen):**  
  Implementiert die Geschäftsregeln für Kredite. Dazu gehören die Kreditvergabe, die Berechnung von monatlichen Zinsen (15% p.a.), die lineare Amortisation über 12 Monate, sowie das Sperren von Konten und Berechnen von Strafzinsen (30% p.a.) bei Zahlungsausfall.

- **`buchung.py` (Bankinterne Verbuchung):**  
  Setzt die Bankensicht um. Alle finanziellen Bewegungen der Kunden werden hier als doppelte Buchhaltung auf den Hauptbüchern (`Zentralbank`, `Verpflichtung`, `Kreditkonto`, `Einnahmen`) nachvollzogen. Eine integrierte Bilanzprüfung (`Aktiva = Passiva + G&V`) stellt sicher, dass das Bankensystem immer im Gleichgewicht ist.

- **`speicherung.py` (Persistenzschicht):**  
  Regelt den Lese- und Schreibzugriff auf das Dateisystem per JSON-Serialisierung.

## Daten- und Speichermodell

Anstatt einer relationalen Datenbank nutzt das Projekt ein leicht lesbares Dateisystem-Konstrukt aus **JSON-Dateien**. Das erleichtert das Nachvollziehen einzelner Transaktionsschritte und Modifikationen (Tracing).

* **Kundenkonten:** Befinden sich im Verzeichnis `konten/`. Für jeden Kunden wird eine eigene Datei (z.B. `anna_muster.json`) erstellt, in der Stammdaten, Kontostände (Giro & Kredit) und der gesamte Transaktionsverlauf gespeichert sind.
* **Tages-Transaktionen:** Befinden sich typischerweise im Ordner `transaktionen/` (z.B. nach Datum gruppiert wie `2026-01.json`), wo sie vom Hauptprogramm gelesen werden.
* **Hauptbuch (`bankkonten.json`):** Enthält das interne Hauptbuch der Bank inklusive Kontostände und Journal (Log) aller Verbuchungen der Bank.
* **Simulator-Output (`zusammenfassung.json`):** Dient am Ende der Simulation als Nachweis über alle verarbeiteten Datenstrukturen, Kontostände und Bankreserven.

## Wichtige Designentscheidungen

1. **Ereignisgesteuerte Architektur (Batch-Verarbeitung):**  
   Damit zeitliche Abhängigkeiten (Zinsen, Strafzinsen, Quartalsgebühren) deterministisch bleiben, durchläuft die Applikation festgelegte Tages-, Monats- und Quartals-Batches, bevor Ein-/Überweisungen abgerechnet werden.

2. **Fehlertoleranz bei Buchungen:**  
   Bei fehlender Deckung auf dem Kundenkonto wird eine Transaktion nicht einfach gelöscht, sondern als `abgelehnt` direkt in das Array der Transaktionen des Kontos eingetragen (`konten.py`). So bleibt die Fehlerhistorie des Kunden erhalten. Ebenso führt eine fehlgeschlagene Amortisation sofort zur Sperrung.

3. **Strenge Konsistenz durch Doppelte Buchführung:**  
   Jeglicher Kundeneingang / -verlust spiegelt sich sofort im Hauptbuch der Bank (`buchung.py`) wider, ohne dass die `konten.py` die Bankkonten direkt bearbeiten muss. Die Validierungsfunktion `bilanz_pruefen()` dient hier als ständige Sicherheitskarte.

## Nutzung

Um die Simulation auszuführen, starte einfach das Skript in der Konsole:

```bash
python engine.py
```

Die JSON-Batches mit den Kunden-Transaktionen werden dann eingelesen und verarbeitet. Die Ergebnisse können danach bequem in den `konten/*.json` und der finalen `zusammenfassung.json` abgelesen werden.