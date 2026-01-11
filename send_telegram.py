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
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_ID", "").split(",")  # Komma-getrennte Liste
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


def format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell, bester_zielbereich=None, bester_cv=None):
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

    # Motivierende Nachricht bei guten Werten (CV < 36% oder Zielbereich >= 80%)
    if cv < 36 and zielbereich >= 80:
        # Beide Werte gut
        message += f"\n\n💪 Weiter so! Deine Glukose-Stabilität bei {cv}% und dein Blutzucker im Idealbereich bei {zielbereich}% sahen gestern richtig gut aus. Versuche es heute erneut!"
    elif cv < 36:
        # Nur CV gut
        message += f"\n\n💪 Weiter so! Deine Glukose-Stabilität bei {cv}% sah gestern richtig gut aus. Versuche es heute erneut!"
    elif zielbereich >= 80:
        # Nur Zielbereich gut
        message += f"\n\n💪 Weiter so! Dein Blutzucker im Idealbereich bei {zielbereich}% sah gestern richtig gut aus. Versuche es heute erneut!"

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

    print("\nErstelle Nachricht...")
    message = format_message(gestern_data, vorgestern_data, gestern_datum, ist_aktuell, bester_zielbereich, bester_cv)

    print("\n--- Nachricht ---")
    print(message)
    print("-----------------\n")

    print("Sende via Telegram...")
    return send_telegram(message)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
