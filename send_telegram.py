#!/usr/bin/env python3
"""
Telegram Sender
Sendet den Diabetes-Tagesbericht via Telegram.
"""

import os
import csv
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_ID", "").split(",")  # Komma-getrennte Liste
CSV_FILE = Path(__file__).parent / "data" / "diabetes_daily.csv"
STREAK_FILE = Path(__file__).parent / "data" / "streak.json"

# Streak-Schwellwert
STREAK_THRESHOLD = 80  # Zielbereich muss >= 80% sein für Streak

# Wochentage auf Deutsch
WOCHENTAGE = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag"
}


def read_all_data():
    """Liest alle Daten aus der CSV."""
    if not CSV_FILE.exists():
        print("ERROR: CSV-Datei nicht gefunden")
        return []

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    return reader


def read_data_for_dates(target_date, previous_date):
    """Liest die Daten für spezifische Daten aus der CSV."""
    reader = read_all_data()

    if len(reader) < 1:
        print("ERROR: Keine Daten in CSV")
        return None, None

    # Erstelle Dict für schnellen Zugriff
    data_by_date = {row['datum']: row for row in reader}

    target_data = data_by_date.get(target_date)
    previous_data = data_by_date.get(previous_date)

    return target_data, previous_data


def check_best_values(gestern_data, all_data):
    """Prüft ob gestern Bestwerte erreicht wurden (nur bei >= 10 Tagen Daten)."""
    if len(all_data) < 10:
        return None, None

    gestern_zielbereich = float(gestern_data['zielbereich_pct'])
    gestern_cv = float(gestern_data['cv_pct'])

    # Finde beste Werte aller Tage (außer gestern)
    andere_tage = [row for row in all_data if row['datum'] != gestern_data['datum']]

    if not andere_tage:
        return None, None

    # Höchster Zielbereich = bester
    max_zielbereich = max(float(row['zielbereich_pct']) for row in andere_tage)
    ist_bester_zielbereich = gestern_zielbereich > max_zielbereich

    # Niedrigster CV = bester (stabiler)
    min_cv = min(float(row['cv_pct']) for row in andere_tage)
    ist_bester_cv = gestern_cv < min_cv

    return ist_bester_zielbereich, ist_bester_cv


def get_trend_arrow(current, previous):
    """Berechnet den Trend-Pfeil."""
    if previous is None or current is None:
        return ""

    try:
        curr = float(current)
        prev = float(previous)

        if curr > prev:
            return "↑"
        elif curr < prev:
            return "↓"
        else:
            return "→"
    except (ValueError, TypeError):
        return ""


def load_streak():
    """Lädt die Streak-Daten aus der JSON-Datei."""
    if not STREAK_FILE.exists():
        return {"current_streak": 0, "best_streak": 0, "last_date": None}

    try:
        with open(STREAK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"current_streak": 0, "best_streak": 0, "last_date": None}


def save_streak(streak_data):
    """Speichert die Streak-Daten in die JSON-Datei."""
    STREAK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STREAK_FILE, 'w', encoding='utf-8') as f:
        json.dump(streak_data, f, indent=2)


def update_streak(zielbereich, datum):
    """
    Aktualisiert die Streak basierend auf dem Zielbereich-Wert.
    Gibt (neue_streak, streak_gebrochen, alte_streak) zurück.
    """
    streak_data = load_streak()
    alte_streak = streak_data["current_streak"]

    # Prüfe ob Streak-Bedingung erfüllt (>= 80%)
    if zielbereich >= STREAK_THRESHOLD:
        # Streak fortsetzen oder starten
        streak_data["current_streak"] += 1
        streak_gebrochen = False

        # Neuer Rekord?
        if streak_data["current_streak"] > streak_data["best_streak"]:
            streak_data["best_streak"] = streak_data["current_streak"]
    else:
        # Streak gebrochen
        streak_gebrochen = alte_streak > 0
        streak_data["current_streak"] = 0

    streak_data["last_date"] = datum
    save_streak(streak_data)

    return streak_data["current_streak"], streak_gebrochen, alte_streak


def get_streak_message(current_streak, streak_gebrochen, alte_streak):
    """Erstellt die Streak-Nachricht basierend auf dem aktuellen Status."""
    if streak_gebrochen:
        # Streak wurde gebrochen
        if alte_streak >= 7:
            return f"\n\n💔 Streak beendet nach {alte_streak} Tagen. Morgen neu starten!"
        elif alte_streak > 0:
            return f"\n\n💔 Streak beendet nach {alte_streak} Tag{'en' if alte_streak > 1 else ''}. Morgen neu starten!"
        return ""

    if current_streak == 0:
        return ""

    # Meilensteine prüfen
    if current_streak == 100:
        return f"\n\n🏆 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%! Legendär!"
    elif current_streak == 60:
        return f"\n\n🔥🔥🔥🔥 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%! Zwei Monate!"
    elif current_streak == 30:
        return f"\n\n🔥🔥🔥 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%! Ein ganzer Monat!"
    elif current_streak == 14:
        return f"\n\n🔥🔥 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%! Zwei Wochen stark!"
    elif current_streak == 7:
        return f"\n\n🔥🔥 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%! Eine ganze Woche!"
    elif current_streak >= 3:
        return f"\n\n🔥 {current_streak} Tage in Folge über {STREAK_THRESHOLD}%!"
    elif current_streak >= 1:
        return ""  # Keine Nachricht für 1-2 Tage (zu früh für Streak-Anzeige)

    return ""


def format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell, bester_zielbereich=None, bester_cv=None, streak_message=""):
    """Formatiert die Telegram-Nachricht."""

    # Wenn keine Daten für gestern verfügbar
    if not ist_aktuell or not gestern_data:
        heute = datetime.now()
        gestern = heute - timedelta(days=1)
        wochentag = WOCHENTAGE[gestern.weekday()]
        datum_str = gestern.strftime("%d.%m.%Y")

        message = f"""📊 {wochentag}, {datum_str}

<b>Daten nicht verfügbar</b>"""
        return message

    # Datum parsen
    datum = datetime.strptime(gestern_data['datum'], "%Y-%m-%d")
    wochentag = WOCHENTAGE[datum.weekday()]
    datum_str = datum.strftime("%d.%m.%Y")

    # Werte extrahieren
    zielbereich = round(float(gestern_data['zielbereich_pct']))
    cv = round(float(gestern_data['cv_pct']))

    # Trends nur wenn Vorgestern-Daten verfügbar
    zielbereich_trend = ""
    cv_trend = ""

    if vorgestern_data:
        zielbereich_trend = f" ({get_trend_arrow(gestern_data['zielbereich_pct'], vorgestern_data['zielbereich_pct'])})"
        cv_trend = f" ({get_trend_arrow(gestern_data['cv_pct'], vorgestern_data['cv_pct'])})"

    # Nachricht zusammenbauen
    message = f"""📊 {wochentag}, {datum_str}

<b>{zielbereich}%{zielbereich_trend} Blutzucker im Idealbereich</b>
{cv}%{cv_trend} Glukose-Stabilität"""

    # Glückwunsch bei Bestwerten hinzufügen
    if bester_zielbereich or bester_cv:
        message += "\n"

        if bester_zielbereich and bester_cv:
            message += "\n🎉 <b>Glückwunsch!</b> Bestwerte bei Idealbereich und Stabilität!"
        elif bester_zielbereich:
            message += "\n🎉 <b>Glückwunsch!</b> Bestwert beim Blutzucker im Idealbereich!"
        elif bester_cv:
            message += "\n🎉 <b>Glückwunsch!</b> Bestwert bei der Glukose-Stabilität!"

    # Streak-Nachricht hinzufügen
    if streak_message:
        message += streak_message

    return message


def send_telegram(message):
    """Sendet die Nachricht via Telegram an alle Chat-IDs."""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("ERROR: TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID erforderlich")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    success_count = 0
    error_count = 0

    for chat_id in TELEGRAM_CHAT_IDS:
        chat_id = chat_id.strip()  # Leerzeichen entfernen
        if not chat_id:
            continue

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            print(f"✓ Nachricht an Chat-ID {chat_id} gesendet")
            success_count += 1
        else:
            print(f"✗ Fehler bei Chat-ID {chat_id}: {response.status_code} - {response.text}")
            error_count += 1

    print(f"\nErgebnis: {success_count} erfolgreich, {error_count} Fehler")
    return success_count > 0


def main():
    """Hauptfunktion."""
    print("Lese Daten aus CSV...")

    # Alle Daten laden für Bestwert-Prüfung
    all_data = read_all_data()
    print(f"Insgesamt {len(all_data)} Tage in der Datenbank")

    # Berechne erwartete Daten (gestern und vorgestern)
    heute = datetime.now()
    gestern_datum = (heute - timedelta(days=1)).strftime("%Y-%m-%d")
    vorgestern_datum = (heute - timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"Suche Daten für:")
    print(f"  Gestern: {gestern_datum}")
    print(f"  Vorgestern: {vorgestern_datum}")

    # Versuche die Daten für gestern und vorgestern zu laden
    gestern_data, vorgestern_data = read_data_for_dates(gestern_datum, vorgestern_datum)

    ist_aktuell = gestern_data is not None

    print(f"\nVerwende Daten:")
    if gestern_data:
        print(f"  Haupt-Datum: {gestern_data['datum']} ✓")
    else:
        print(f"  Haupt-Datum: {gestern_datum} ✗ (nicht verfügbar)")

    if vorgestern_data:
        print(f"  Vergleichs-Datum: {vorgestern_data['datum']} ✓")
    else:
        print(f"  Vergleichs-Datum: {vorgestern_datum} ✗ (kein Trend-Vergleich)")

    # Prüfe auf Bestwerte (nur wenn gestern_data vorhanden und >= 10 Tage Daten)
    bester_zielbereich = None
    bester_cv = None

    if gestern_data and len(all_data) >= 10:
        print(f"\nPrüfe Bestwerte (>= 10 Tage Daten vorhanden)...")
        bester_zielbereich, bester_cv = check_best_values(gestern_data, all_data)
        if bester_zielbereich:
            print("  🎉 Bestwert beim Idealbereich!")
        if bester_cv:
            print("  🎉 Bestwert bei der Stabilität!")
        if not bester_zielbereich and not bester_cv:
            print("  Keine Bestwerte heute")
    elif len(all_data) < 10:
        print(f"\nBestwert-Prüfung übersprungen (erst {len(all_data)} von 10 benötigten Tagen)")

    # Streak aktualisieren und Nachricht erstellen
    streak_message = ""
    if gestern_data:
        zielbereich = round(float(gestern_data['zielbereich_pct']))
        print(f"\nAktualisiere Streak (Schwellwert: {STREAK_THRESHOLD}%)...")
        print(f"  Zielbereich gestern: {zielbereich}%")

        current_streak, streak_gebrochen, alte_streak = update_streak(zielbereich, gestern_datum)

        if streak_gebrochen:
            print(f"  💔 Streak gebrochen! (war {alte_streak} Tage)")
        elif current_streak > 0:
            print(f"  🔥 Streak: {current_streak} Tage")
        else:
            print(f"  Keine Streak (unter {STREAK_THRESHOLD}%)")

        streak_message = get_streak_message(current_streak, streak_gebrochen, alte_streak)

    print("\nErstelle Nachricht...")
    message = format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell, bester_zielbereich, bester_cv, streak_message)

    print("\n--- Nachricht ---")
    print(message)
    print("-----------------\n")

    print("Sende via Telegram...")
    return send_telegram(message)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
