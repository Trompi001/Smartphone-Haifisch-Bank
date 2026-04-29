import json
import os

# Pfadkonfiguration basierend auf deinem Feedback
KONTEN_ORDNER = "konten"

def initialisiere_ordner():
    """Stellt sicher, dass der Zielordner für die Konten existiert."""
    if not os.path.exists(KONTEN_ORDNER):
        os.makedirs(KONTEN_ORDNER)

def generiere_dateiname_fuer_konto(konto_daten):
    """Erstellt einen Dateinamen basierend auf dem Namen des Kunden."""
    name = konto_daten["kunde"]["name"]
    # Formatiert den Namen (z.B. "Anna Muster" -> "anna_muster")
    dateiname = name.lower().replace(" ", "_")
    return os.path.join(KONTEN_ORDNER, f"{dateiname}.json")

def speichere_konto(konto_daten):
    """
    Speichert ein einzelnes Kundenkonto als JSON-Datei.
    Der Dateiname entspricht dem formatierten Namen des Kunden.
    """
    initialisiere_ordner()
    dateipfad = generiere_dateiname_fuer_konto(konto_daten)
    
    with open(dateipfad, 'w', encoding='utf-8') as f:
        json.dump(konto_daten, f, indent=2, ensure_ascii=False)

def lade_konto(iban):
    """
    Lädt die Kontodaten einer spezifischen IBAN aus dem konten-Ordner.
    Durchsucht alle Dateien, da der Dateiname nun der Kundenname ist.
    Gibt None zurück, falls das Konto nicht existiert.
    """
    if not os.path.exists(KONTEN_ORDNER):
        return None
        
    for datei in os.listdir(KONTEN_ORDNER):
        if datei.endswith(".json") and datei != "bankkonten.json":
            dateipfad = os.path.join(KONTEN_ORDNER, datei)
            # Kurz reinladen um zu prüfen, ob die IBAN übereinstimmt
            try:
                with open(dateipfad, 'r', encoding='utf-8') as f:
                    daten = json.load(f)
                    if daten.get("konto_iban") == iban:
                        return daten
            except FileNotFoundError:
                continue
    return None

def speichere_json(dateipfad, daten):
    """Generische Funktion zum Speichern von JSON-Strukturen (z.B. Bank-Status)."""
    # Sicherstellen, dass das Verzeichnis existiert
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