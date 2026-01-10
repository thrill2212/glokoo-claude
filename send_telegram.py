#!/usr/bin/env python3
"""
Telegram Sender
Sendet den Diabetes-Tagesbericht via Telegram.
"""

import os
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CSV_FILE = Path(__file__).parent / "data" / "diabetes_daily.csv"

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


def read_data_for_dates(target_date, previous_date):
    """Liest die Daten für spezifische Daten aus der CSV."""
    if not CSV_FILE.exists():
        print("ERROR: CSV-Datei nicht gefunden")
        return None, None

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    if len(reader) < 1:
        print("ERROR: Keine Daten in CSV")
        return None, None

    # Erstelle Dict für schnellen Zugriff
    data_by_date = {row['datum']: row for row in reader}

    target_data = data_by_date.get(target_date)
    previous_data = data_by_date.get(previous_date)

    return target_data, previous_data


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


def format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell):
    """Formatiert die Telegram-Nachricht."""

    # Datum parsen
    datum = datetime.strptime(gestern_data['datum'], "%Y-%m-%d")
    wochentag = WOCHENTAGE[datum.weekday()]
    datum_str = datum.strftime("%d.%m.%Y")

    # Werte extrahieren
    zielbereich = round(float(gestern_data['zielbereich_pct']))
    cv = round(float(gestern_data['cv_pct']))

    # Trends berechnen
    zielbereich_trend = ""
    cv_trend = ""

    if vorgestern_data:
        zielbereich_trend = f" ({get_trend_arrow(gestern_data['zielbereich_pct'], vorgestern_data['zielbereich_pct'])})"
        cv_trend = f" ({get_trend_arrow(gestern_data['cv_pct'], vorgestern_data['cv_pct'])})"

    # Nachricht zusammenbauen
    message = f"""📊 {wochentag}, {datum_str}

<b>{zielbereich}%{zielbereich_trend} Blutzucker im Idealbereich</b>
{cv}%{cv_trend} Glukose-Stabilität"""

    # Warnung hinzufügen, wenn Daten nicht aktuell sind
    if not ist_aktuell:
        message += f"\n\n⚠️ <i>Achtung: Daten sind nicht von gestern ({gestern_datum})</i>"

    return message


def send_telegram(message):
    """Sendet die Nachricht via Telegram."""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID erforderlich")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("Nachricht erfolgreich gesendet!")
        return True
    else:
        print(f"ERROR: {response.status_code} - {response.text}")
        return False


def main():
    """Hauptfunktion."""
    print("Lese Daten aus CSV...")

    # Berechne erwartete Daten (gestern und vorgestern)
    heute = datetime.now()
    gestern_datum = (heute - timedelta(days=1)).strftime("%Y-%m-%d")
    vorgestern_datum = (heute - timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"Suche Daten für:")
    print(f"  Gestern: {gestern_datum}")
    print(f"  Vorgestern: {vorgestern_datum}")

    # Versuche erst die aktuellen Daten zu laden
    gestern_data, vorgestern_data = read_data_for_dates(gestern_datum, vorgestern_datum)

    ist_aktuell = True

    # Wenn keine Daten für gestern, nimm die neuesten verfügbaren
    if not gestern_data:
        print(f"⚠️  Keine Daten für {gestern_datum} gefunden, verwende neueste verfügbare Daten")
        ist_aktuell = False

        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))

        if len(reader) < 1:
            print("ERROR: Keine Daten in CSV")
            return False

        # Sortiere nach Datum absteigend
        reader.sort(key=lambda x: x['datum'], reverse=True)
        gestern_data = reader[0]
        vorgestern_data = reader[1] if len(reader) >= 2 else None

    print(f"\nVerwende Daten:")
    print(f"  Haupt-Datum: {gestern_data['datum']} {'✓' if ist_aktuell else '(nicht aktuell)'}")
    if vorgestern_data:
        print(f"  Vergleichs-Datum: {vorgestern_data['datum']}")

    print("\nErstelle Nachricht...")
    message = format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell)

    print("\n--- Nachricht ---")
    print(message)
    print("-----------------\n")

    print("Sende via Telegram...")
    return send_telegram(message)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
