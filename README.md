# Glooko Diabetes Scraper

Automatischer Scraper, der täglich Diabetes-Daten aus dem [Glooko](https://www.glooko.com/) Dashboard ausliest und per Telegram-Bot als Tagesbericht versendet.

## Was macht das Projekt?

1. **Scraping** (`glooko_scraper.py`) — Loggt sich per Playwright (headless Chromium) in das Glooko-Dashboard ein, navigiert zum gestrigen Tag und extrahiert CGM- und Insulindaten
2. **Telegram-Report** (`send_telegram.py`) — Erstellt eine kompakte Tagesübersicht mit Zielbereich (TIR), CV, Streak-Tracking und Bestwert-Erkennung und sendet sie via Telegram
3. **GitHub Action** (`.github/workflows/daily.yml`) — Läuft täglich um 08:00 MEZ, führt beides aus und committet die CSV-Daten zurück ins Repository

## Beispiel-Nachrichten

**Normaler Tag:**
```
📊 Mittwoch, 19.02.2026

69% Blutzucker im Idealbereich (TIR)
39% Blutzucker-Stabilität (CV)
```

**Guter Tag (TIR >= 80%, CV < 36%):**
```
📊 Samstag, 15.02.2026

88% Blutzucker im Idealbereich (TIR) ⭐
31% Blutzucker-Stabilität (CV) ⭐

🔥 5 Tage in Folge über 70%!
```

**Bestwert erreicht:**
```
📊 Sonntag, 12.01.2026

92% Blutzucker im Idealbereich (TIR) ⭐
22% Blutzucker-Stabilität (CV) ⭐

🎉 Glückwunsch! Bestwerte bei Idealbereich und Stabilität!

🔥🔥 7 Tage in Folge über 70%! Eine ganze Woche!
```

## Erfasste Werte

| Wert | Beschreibung |
|------|-------------|
| Aktive CGM-Zeit | Sensortragedauer in % |
| Sehr hoch / Hoch / Zielbereich / Niedrig / Sehr niedrig | Blutzucker-Verteilung in % |
| Durchschnitt | Mittlerer Blutzucker in mg/dl |
| SD | Standardabweichung in mg/dl |
| CV | Variationskoeffizient in % |
| GMI | Glucose Management Indicator |
| Basal / Bolus | Insulinverteilung in % und Einheiten |

## Telegram-Features

- Tagesreport mit Zielbereich und CV
- Sterne bei guten Werten (TIR >= 80%, CV < 36%)
- Streak-Tracking: Tage in Folge mit TIR >= 70%
- Meilensteine bei 7, 14, 30, 60 und 100 Tagen Streak
- Bestwert-Erkennung ab 10 Tagen Datenhistorie

## Setup

### 1. Telegram-Bot erstellen

1. In Telegram den [@BotFather](https://t.me/BotFather) öffnen und `/newbot` senden
2. Einen Namen und Benutzernamen für den Bot vergeben
3. Den **Bot-Token** kopieren und als `TELEGRAM_BOT_TOKEN` Secret speichern
4. Den Bot in Telegram öffnen und `/start` senden
5. Die eigene **Chat-ID** herausfinden, z.B. über [@userinfobot](https://t.me/userinfobot), und als `TELEGRAM_CHAT_ID` Secret speichern

### 2. GitHub Secrets konfigurieren

Im Repository unter **Settings > Secrets and variables > Actions** folgende Secrets anlegen:

| Secret | Beschreibung |
|--------|-------------|
| `GLOOKO_EMAIL` | E-Mail-Adresse für den Glooko-Login |
| `GLOOKO_PASSWORD` | Passwort für den Glooko-Login |
| `TELEGRAM_BOT_TOKEN` | Token des Telegram-Bots (via [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | Chat-ID(s) für den Empfang, kommagetrennt für mehrere Empfänger |

### 3. Manuell testen

Die Action kann unter **Actions > Täglicher Diabetes-Report > Run workflow** manuell ausgelöst werden.

### 4. Lokal ausführen

```bash
pip install playwright requests
playwright install chromium

export GLOOKO_EMAIL="..."
export GLOOKO_PASSWORD="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."

python glooko_scraper.py
python send_telegram.py
```

## Datenstruktur

```
data/
├── diabetes_daily.csv   # Tägliche Werte (eine Zeile pro Tag)
└── streak.json          # Aktueller Streak-Stand
```

## Fehlerbehandlung

- Bei fehlgeschlagenem Login wird eine klare Fehlermeldung ausgegeben und ein Screenshot gespeichert
- Bei Scraping-Fehlern werden Debug-Screenshots als GitHub Action Artifact hochgeladen
- Bei jedem Fehler wird eine Telegram-Benachrichtigung gesendet
