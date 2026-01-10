#!/usr/bin/env python3
"""
Glooko Scraper
Scrapes diabetes data from Glooko dashboard and saves to CSV.
"""

import os
import sys
import csv
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
GLOOKO_URL = "https://de-fr.my.glooko.com/"
GLOOKO_EMAIL = os.environ.get("GLOOKO_EMAIL")
GLOOKO_PASSWORD = os.environ.get("GLOOKO_PASSWORD")
CSV_FILE = Path(__file__).parent / "data" / "diabetes_daily.csv"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

# CSV Spalten
CSV_COLUMNS = [
    "datum",
    "aktive_cgm_zeit_pct",
    "sehr_hoch_pct",
    "hoch_pct",
    "zielbereich_pct",
    "niedrig_pct",
    "sehr_niedrig_pct",
    "durchschnitt_mgdl",
    "sd_mgdl",
    "cv_pct",
    "gmi",
    "basal_pct",
    "basal_einheiten",
    "bolus_pct",
    "bolus_einheiten",
    "created_at"
]


def extract_values(page):
    """Extrahiert alle Werte aus dem Glooko Dashboard via JavaScript."""

    values = page.evaluate('''() => {
        const result = {
            datum: null,
            aktive_cgm_zeit_pct: null,
            sehr_hoch_pct: null,
            hoch_pct: null,
            zielbereich_pct: null,
            niedrig_pct: null,
            sehr_niedrig_pct: null,
            durchschnitt_mgdl: null,
            sd_mgdl: null,
            cv_pct: null,
            gmi: null,
            basal_pct: null,
            basal_einheiten: null,
            bolus_pct: null,
            bolus_einheiten: null
        };

        const allText = document.body.innerText;

        // Datum extrahieren (Format: "Fr., 09. Jan. 2026")
        const datumMatch = allText.match(/(Mo|Di|Mi|Do|Fr|Sa|So)\\.?,?\\s*(\\d{1,2})\\.\\s*(Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\\.?\\s*(\\d{4})/);
        if (datumMatch) {
            const monate = {
                'Jan': '01', 'Feb': '02', 'Mär': '03', 'Apr': '04',
                'Mai': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Okt': '10', 'Nov': '11', 'Dez': '12'
            };
            const tag = datumMatch[2].padStart(2, '0');
            const monat = monate[datumMatch[3]];
            const jahr = datumMatch[4];
            result.datum = `${jahr}-${monat}-${tag}`;
        }

        // Aktive CGM-Zeit (Format: "Aktive CGM-Zeit in % 100% (1 Tage)")
        const cgmZeitMatch = allText.match(/Aktive\\s*CGM-?Zeit\\s*(?:in\\s*%)?\\s*(\\d+[,.]?\\d*)\\s*%/i);
        if (cgmZeitMatch) {
            result.aktive_cgm_zeit_pct = parseFloat(cgmZeitMatch[1].replace(',', '.'));
        }

        // Sehr hoch (Format: "12% Sehr hoch" oder "Sehr hoch > 250 mg/dl")
        const sehrHochMatch = allText.match(/(\\d+)%\\s*Sehr\\s*hoch/i);
        if (sehrHochMatch) {
            result.sehr_hoch_pct = parseFloat(sehrHochMatch[1]);
        }

        // Hoch (Format: "14% Hoch")
        const hochMatch = allText.match(/(\\d+)%\\s*Hoch\\s*(?:181|\\d)/i);
        if (hochMatch) {
            result.hoch_pct = parseFloat(hochMatch[1]);
        }

        // Zielbereich (Format: "69% Zielbereich")
        const zielbereichMatch = allText.match(/(\\d+)%\\s*Zielbereich/i);
        if (zielbereichMatch) {
            result.zielbereich_pct = parseFloat(zielbereichMatch[1]);
        }

        // Niedrig (Format: "5% Niedrig")
        const niedrigMatch = allText.match(/(\\d+)%\\s*Niedrig\\s*(?:54|\\d)/i);
        if (niedrigMatch) {
            result.niedrig_pct = parseFloat(niedrigMatch[1]);
        }

        // Sehr niedrig (Format: "0% Sehr niedrig")
        const sehrNiedrigMatch = allText.match(/(\\d+)%\\s*Sehr\\s*niedrig/i);
        if (sehrNiedrigMatch) {
            result.sehr_niedrig_pct = parseFloat(sehrNiedrigMatch[1]);
        }

        // Durchschnitt (Format: "Durchschnitt 157 mg/dl")
        const durchschnittMatch = allText.match(/Durchschnitt\\s*(\\d+)\\s*mg\\/dl/i);
        if (durchschnittMatch) {
            result.durchschnitt_mgdl = parseInt(durchschnittMatch[1]);
        }

        // SD (Format: "SD 61 mg/dl")
        const sdMatch = allText.match(/SD\\s*(\\d+)\\s*mg\\/dl/i);
        if (sdMatch) {
            result.sd_mgdl = parseInt(sdMatch[1]);
        }

        // CV (Format: "CV 38.9%")
        const cvMatch = allText.match(/CV\\s*(\\d+[,.]?\\d*)\\s*%/i);
        if (cvMatch) {
            result.cv_pct = parseFloat(cvMatch[1].replace(',', '.'));
        }

        // GMI (Format: "GMI 7.2%" oder "GMI k.A.")
        const gmiMatch = allText.match(/GMI\\s*(\\d+[,.]?\\d*)\\s*%/i);
        if (gmiMatch) {
            result.gmi = parseFloat(gmiMatch[1].replace(',', '.'));
        }

        // Basal (Format: "44% 16,1 Einheit Basal/Tag")
        const basalMatch = allText.match(/(\\d+)%\\s*(\\d+[,.]?\\d*)\\s*Einheit[en]*\\s*(?:Basal|Basal\\/Tag)/i);
        if (basalMatch) {
            result.basal_pct = parseFloat(basalMatch[1]);
            result.basal_einheiten = parseFloat(basalMatch[2].replace(',', '.'));
        }

        // Bolus (Format: "56% 20,4 Einheit Bolus")
        const bolusMatch = allText.match(/(\\d+)%\\s*(\\d+[,.]?\\d*)\\s*Einheit[en]*\\s*(?:Bolus)/i);
        if (bolusMatch) {
            result.bolus_pct = parseFloat(bolusMatch[1]);
            result.bolus_einheiten = parseFloat(bolusMatch[2].replace(',', '.'));
        }

        return result;
    }''')

    return values


def save_to_csv(data):
    """Speichert die Daten in der CSV-Datei."""

    # Erstelle data-Verzeichnis falls nötig
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Füge Timestamp hinzu
    data['created_at'] = datetime.now().isoformat()

    # Prüfe ob Datei existiert
    file_exists = CSV_FILE.exists()

    # Prüfe ob Datum bereits existiert
    if file_exists:
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['datum'] == data['datum']:
                    print(f"Daten für {data['datum']} existieren bereits - überspringe")
                    return False

    # Schreibe Daten
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)

        # Schreibe Header falls neue Datei
        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    print(f"Daten für {data['datum']} gespeichert in {CSV_FILE}")
    return True


def scrape_glooko():
    """Hauptfunktion: Login, Navigation, Scraping, Speichern."""

    if not GLOOKO_EMAIL or not GLOOKO_PASSWORD:
        print("ERROR: GLOOKO_EMAIL und GLOOKO_PASSWORD Umgebungsvariablen erforderlich")
        sys.exit(1)

    print(f"Starte Glooko Scraper für: {GLOOKO_EMAIL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="de-DE"
        )
        page = context.new_page()

        try:
            # Login
            print(f"Navigiere zu {GLOOKO_URL}")
            page.goto(GLOOKO_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Cookie-Banner auf Login-Seite schließen
            try:
                cookie_btn = page.locator('button:has-text("Alle ablehnen"), button:has-text("Reject All"), button#onetrust-reject-all-handler').first
                if cookie_btn.is_visible(timeout=5000):
                    cookie_btn.click()
                    page.wait_for_timeout(1000)
                    print("Cookie-Banner auf Login-Seite geschlossen")
            except:
                pass

            print("Gebe Anmeldedaten ein...")
            email_field = page.locator('input[type="email"], input[name="user[email]"], input[placeholder*="mail" i]').first
            email_field.fill(GLOOKO_EMAIL)
            password_field = page.locator('input[type="password"]').first
            password_field.fill(GLOOKO_PASSWORD)
            login_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("Log In"), button:has-text("Anmelden")').first
            login_button.click()

            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            print("LOGIN ERFOLGREICH!")

            # Cookie-Banner schließen
            try:
                cookie_btn = page.locator('button:has-text("Alle ablehnen")').first
                if cookie_btn.is_visible(timeout=2000):
                    cookie_btn.click()
                    page.wait_for_timeout(1000)
            except:
                pass

            # Zeitraum auf "1 Tag" wechseln
            print("Wechsle Zeitraum auf '1 Tag'...")
            zeitraum_dropdown = page.locator('select, [class*="dropdown"], [class*="select"]').filter(has_text="Wochen").first
            zeitraum_dropdown.click()
            page.wait_for_timeout(500)
            tag_option = page.locator('option:has-text("1 Tag"), li:has-text("1 Tag"), [role="option"]:has-text("1 Tag")').first
            tag_option.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # Zum gestrigen Tag navigieren
            print("Navigiere zum gestrigen Tag...")
            all_buttons = page.locator('button').all()
            nav_buttons = []
            for btn in all_buttons:
                try:
                    box = btn.bounding_box()
                    if box and 480 < box['y'] < 540 and 30 < box['width'] < 60:
                        nav_buttons.append((box['x'], btn))
                except:
                    pass

            if nav_buttons:
                nav_buttons.sort(key=lambda x: x[0])
                nav_buttons[0][1].click()

            # Warte auf Daten-Aktualisierung
            print("Warte 10 Sekunden auf Daten-Aktualisierung...")
            page.wait_for_timeout(10000)
            page.wait_for_load_state("networkidle")

            # Full-page Screenshot
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SCREENSHOTS_DIR / "debug_scrape_fullpage.png"), full_page=True)

            # Werte extrahieren
            print("Extrahiere Werte...")
            data = extract_values(page)

            # Ausgabe
            print("\n=== EXTRAHIERTE DATEN ===")
            for key, value in data.items():
                print(f"  {key}: {value}")

            # In CSV speichern
            print("\nSpeichere in CSV...")
            save_to_csv(data)

            return True

        except PlaywrightTimeout as e:
            print(f"TIMEOUT ERROR: {e}")
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SCREENSHOTS_DIR / "debug_error_timeout.png"))
            return False
        except Exception as e:
            print(f"ERROR: {e}")
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SCREENSHOTS_DIR / "debug_error_exception.png"))
            return False
        finally:
            browser.close()


if __name__ == "__main__":
    success = scrape_glooko()
    sys.exit(0 if success else 1)
