#!/usr/bin/env python3
"""
Telegram Sender
Sendet den Diabetes-Tagesbericht via Telegram.
"""

import os
import csv
import requests
from datetime import datetime
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


def read_last_two_days():
    """Liest die letzten zwei Einträge aus der CSV."""
    if not CSV_FILE.exists():
        print("ERROR: CSV-Datei nicht gefunden")
        return None, None

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    if len(reader) < 1:
        print("ERROR: Keine Daten in CSV")
        return None, None

    # Sortiere nach Datum absteigend
    reader.sort(key=lambda x: x['datum'], reverse=True)

    gestern = reader[0] if len(reader) >= 1 else None
    vorgestern = reader[1] if len(reader) >= 2 else None

    return gestern, vorgestern


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


def format_message(gestern, vorgestern):
    """Formatiert die Telegram-Nachricht."""

    # Datum parsen
    datum = datetime.strptime(gestern['datum'], "%Y-%m-%d")
    wochentag = WOCHENTAGE[datum.weekday()]
    datum_str = datum.strftime("%d.%m.%Y")

    # Werte extrahieren
    zielbereich = round(float(gestern['zielbereich_pct']))
    cv = round(float(gestern['cv_pct']))

    # Trends berechnen
    zielbereich_trend = ""
    cv_trend = ""

    if vorgestern:
        zielbereich_trend = f" ({get_trend_arrow(gestern['zielbereich_pct'], vorgestern['zielbereich_pct'])})"
        cv_trend = f" ({get_trend_arrow(gestern['cv_pct'], vorgestern['cv_pct'])})"

    # Nachricht zusammenbauen
    message = f"""📊 {wochentag}, {datum_str}

<b>{zielbereich}%{zielbereich_trend} Blutzucker im Idealbereich</b>
{cv}%{cv_trend} Glukose-Stabilität"""

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
    gestern, vorgestern = read_last_two_days()

    if not gestern:
        print("Keine Daten verfügbar")
        return False

    print(f"Gestern: {gestern['datum']}")
    if vorgestern:
        print(f"Vorgestern: {vorgestern['datum']}")

    print("\nErstelle Nachricht...")
    message = format_message(gestern, vorgestern)

    print("\n--- Nachricht ---")
    print(message)
    print("-----------------\n")

    print("Sende via Telegram...")
    return send_telegram(message)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
