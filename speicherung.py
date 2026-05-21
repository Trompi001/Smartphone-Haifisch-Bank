import json
import os

KONTEN_ORDNER = "konten"

def initialisiere_ordner():
    """Stellt sicher, dass der Zielordner für die Konten existiert."""
    if not os.path.exists(KONTEN_ORDNER):
        os.makedirs(KONTEN_ORDNER)

def generiere_dateiname_fuer_konto(konto_daten):
    """Erstellt einen Dateinamen basierend auf dem Namen des Kunden."""
    name = konto_daten["kunde"]["name"]
    dateiname = name.lower().replace(" ", "_")
    return os.path.join(KONTEN_ORDNER, f"{dateiname}.json")

def speichere_konto(konto_daten):
    """Speichert ein einzelnes Kundenkonto als JSON-Datei."""
    initialisiere_ordner()
    dateipfad = generiere_dateiname_fuer_konto(konto_daten)
    with open(dateipfad, 'w', encoding='utf-8') as f:
        json.dump(konto_daten, f, indent=2, ensure_ascii=False)

def lade_konto(iban):
    """
    Lädt die Kontodaten einer spezifischen IBAN.
    Gibt None zurück, falls das Konto nicht existiert.
    """
    if not os.path.exists(KONTEN_ORDNER):
        return None
    for datei in os.listdir(KONTEN_ORDNER):
        if datei.endswith(".json"):
            dateipfad = os.path.join(KONTEN_ORDNER, datei)
            try:
                with open(dateipfad, 'r', encoding='utf-8') as f:
                    daten = json.load(f)
                    if daten.get("konto_iban") == iban:
                        return daten
            except (FileNotFoundError, json.JSONDecodeError):
                continue
    return None

def speichere_json(dateipfad, daten):
    """Generische Funktion zum Speichern von JSON-Strukturen."""
    ordner = os.path.dirname(dateipfad)
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    with open(dateipfad, 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)

def lade_json(dateipfad):
    """Generische Funktion zum Laden von JSON-Strukturen."""
    if not os.path.exists(dateipfad):
        return None
    with open(dateipfad, 'r', encoding='utf-8') as f:
        return json.load(f)
