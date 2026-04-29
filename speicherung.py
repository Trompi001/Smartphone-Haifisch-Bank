import json
import os

# Pfadkonfiguration basierend auf deinem Feedback
KONTEN_ORDNER = "konten"

def initialisiere_ordner():
    """Stellt sicher, dass der Zielordner für die Konten existiert."""
    if not os.path.exists(KONTEN_ORDNER):
        os.makedirs(KONTEN_ORDNER)

def generiere_dateiname(iban):
    """Erstellt einen Dateinamen basierend auf der IBAN."""
    return os.path.join(KONTEN_ORDNER, f"{iban}.json")

def speichere_konto(konto_daten):
    """
    Speichert ein einzelnes Kundenkonto als JSON-Datei.
    Der Dateiname entspricht der IBAN des Kontos.
    """
    initialisiere_ordner()
    dateipfad = generiere_dateiname(konto_daten["konto_iban"])
    
    with open(dateipfad, 'w', encoding='utf-8') as f:
        json.dump(konto_daten, f, indent=2, ensure_ascii=False)

def lade_konto(iban):
    """
    Lädt die Kontodaten einer spezifischen IBAN aus dem konten-Ordner.
    Gibt None zurück, falls das Konto nicht existiert.
    """
    dateipfad = generiere_dateiname(iban)
    if not os.path.exists(dateipfad):
        return None
    
    with open(dateipfad, 'r', encoding='utf-8') as f:
        return json.load(f)

def speichere_json(dateipfad, daten):
    """Generische Funktion zum Speichern von JSON-Strukturen (z.B. Bank-Status)."""
    # Sicherstellen, dass das Verzeichnis existiert
    os.makedirs(os.path.dirname(dateipfad), exist_ok=True)
    with open(dateipfad, 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)

def lade_json(dateipfad):
    """Generische Funktion zum Laden von JSON-Strukturen."""
    if not os.path.exists(dateipfad):
        return None
    with open(dateipfad, 'r', encoding='utf-8') as f:
        return json.load(f)