from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time
import json
from datetime import datetime, timedelta

# ────────────────────────────────────────────────
# KONFIGURATION
# ────────────────────────────────────────────────
EMAIL = os.getenv("GLOOKO_EMAIL")
PASSWORT = os.getenv("GLOOKO_PASSWORD")
URL_LOGIN = "https://my.glooko.com/users/sign_in"
DAYS_TO_SCRAPE = 1  # Nur aktueller Tag (wird um 23:50 gescraped)
# ────────────────────────────────────────────────

def login_to_glooko(page):
    """Führt Login durch und kehrt zum Dashboard zurück"""
    print("→ Lade Login-Seite...")
    page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)
    
    # Cookie-Banner akzeptieren
    cookie_selectors = [
        "button:has-text('Allow All')",
        "button:has-text('Accept All')",
        "button:has-text('Alle akzeptieren')"
    ]
    
    for selector in cookie_selectors:
        try:
            if page.locator(selector).is_visible(timeout=3000):
                page.locator(selector).click()
                print("✓ Cookie-Banner akzeptiert")
                time.sleep(2)
                break
        except:
            continue
    
    # Email eingeben
    email_field = page.locator("input[type='email']").first
    email_field.fill(EMAIL)
    print(f"✓ Email eingetragen: {EMAIL}")
    
    # Passwort eingeben
    password_field = page.locator("input[type='password']").first
    password_field.fill(PASSWORT)
    print("✓ Passwort eingetragen")
    
    # Login
    password_field.press("Enter")
    print("✓ Login-Button gedrückt")
    
    # Warten auf Seitenwechsel
    print("Warte auf Seiten-Redirect nach Login...")
    time.sleep(3)
    
    # Screenshot direkt nach Login
    page.screenshot(path="debug_after_login.png")
    print(f"Screenshot nach Login - URL: {page.url}")
    
    # WICHTIG: Warten bis JavaScript fertig geladen ist
    print("Warte auf dynamisches Laden der React-App...")
    
    # Warte auf wichtige Container
    try:
        page.wait_for_selector("#summary-container", timeout=20000, state="attached")
        print("✓ Summary-Container gefunden")
    except:
        print("⚠ Summary-Container nicht gefunden, fahre trotzdem fort")
    
    # Extra Wartezeit für JavaScript/React
    time.sleep(10)
    
    print("Warte auf vollständiges Laden der Daten...")
    page.screenshot(path="debug_after_js_load.png")
    
    # Warten auf Dashboard
    dashboard_loaded = False
    dashboard_selectors = [
        "text=Zusammenfassung",
        "text=Summary",
        "text=Diagramme",
        "text=Charts"
    ]
    
    for selector in dashboard_selectors:
        try:
            page.wait_for_selector(selector, timeout=10000, state="visible")
            print(f"✓ Dashboard geladen (erkannt: {selector})")
            dashboard_loaded = True
            break
        except:
            continue
    
    if not dashboard_loaded:
        print(f"⚠ Dashboard nicht erkannt, aber URL ist: {page.url}")
        if "sign_in" not in page.url and "login" not in page.url.lower():
            print("✓ URL zeigt: Login erfolgreich")
            dashboard_loaded = True
        else:
            print("!!! Login fehlgeschlagen")
            return False
    
    if not dashboard_loaded:
        return False
    
    # Cookie-Banner NACH Login nochmal prüfen - SEHR WICHTIG!
    print("→ Prüfe Cookie-Banner nach Login...")
    for attempt in range(3):
        cookie_found = False
        for selector in cookie_selectors:
            try:
                if page.locator(selector).is_visible(timeout=2000):
                    page.locator(selector).click(timeout=3000, force=True)
                    print(f"✓ Cookie-Banner akzeptiert (Versuch {attempt+1})")
                    time.sleep(2)
                    cookie_found = True
                    break
            except:
                continue
        
        if not cookie_found:
            break
        
        time.sleep(1)
    
    return True

def set_timeframe_to_one_day(page):
    """Ändert Zeitraum auf '1 Tag' - DEUTSCHE VERSION"""
    print("→ Ändere Zeitraum auf '1 Tag'...")

    # Cookie-Banner AGGRESSIV wegklicken (DEUTSCH!)
    print("  Prüfe Cookie-Banner...")
    cookie_selectors = [
        "button:has-text('Alle akzeptieren')",
        "button:has-text('Alle Cookies akzeptieren')",
        "button:has-text('Allow All')",
        "button:has-text('Accept All')",
        "text=Alle akzeptieren",
        "text=Alle Cookies akzeptieren"
    ]

    for _ in range(3):  # Mehrfach versuchen
        for selector in cookie_selectors:
            try:
                if page.locator(selector).is_visible(timeout=1000):
                    page.locator(selector).click(force=True)
                    print(f"  ✓ Cookie-Banner entfernt: {selector}")
                    time.sleep(2)
                    break
            except:
                continue

    page.screenshot(path="debug_before_timeframe.png")
    time.sleep(2)

    try:
        # STRATEGIE 1: Klicke auf "2 Wochen" Dropdown (DEUTSCH!)
        print("  → Versuche Dropdown zu öffnen...")
        dropdown_selectors = [
            "text=2 Wochen",
            "text=2 weeks",
            "text=Zeitraum",
            "select"
        ]

        dropdown_opened = False
        for selector in dropdown_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    print(f"  ✓ Dropdown geklickt: {selector}")
                    time.sleep(2)
                    page.screenshot(path="debug_dropdown_open.png")
                    dropdown_opened = True
                    break
            except:
                continue

        if dropdown_opened:
            # Jetzt "1 Tag" auswählen (DEUTSCH!)
            print("  → Suche '1 Tag' Option...")
            day_options = [
                "text=1 Tag",
                "text=1 day",
                "option:has-text('1 Tag')",
                "option:has-text('1 day')"
            ]

            for opt_selector in day_options:
                try:
                    opt = page.locator(opt_selector).first
                    if opt.is_visible(timeout=2000):
                        opt.click()
                        print(f"  ✓ '1 Tag' ausgewählt!")
                        time.sleep(5)
                        page.screenshot(path="debug_after_timeframe.png")
                        return True
                except:
                    continue

        # STRATEGIE 2: SELECT Element direkt
        print("  → Versuche SELECT direkt...")
        try:
            select = page.locator("select").first
            if select.is_visible(timeout=2000):
                # Versuche verschiedene Values
                for val in ["1", "1d", "day", "1 day", "1 Tag"]:
                    try:
                        select.select_option(value=val)
                        print(f"  ✓ SELECT value='{val}' gesetzt")
                        time.sleep(5)
                        return True
                    except:
                        pass
                # Versuche Labels
                for label in ["1 Tag", "1 day", "Tag", "day"]:
                    try:
                        select.select_option(label=label)
                        print(f"  ✓ SELECT label='{label}' gesetzt")
                        time.sleep(5)
                        return True
                    except:
                        pass
        except:
            pass

        print("⚠ Zeitraum konnte nicht geändert werden - versuche trotzdem mit Navigation")
        return False

    except Exception as e:
        print(f"⚠ Zeitraum-Änderung fehlgeschlagen: {e}")
        return False

def scrape_glucose_data(page):
    """Scraped Glukose-Daten vom Dashboard"""
    print("  → Scrape Glukose-Daten...")
    
    glucose_data = {}
    
    try:
        time.sleep(3)
        page_text = page.inner_text("body")
        
        import re
        
        # TIR
        tir_patterns = [
            r'(\d+)%\s+Zielbereich',
            r'(\d+)%\s+Target\s+Range'
        ]
        
        for pattern in tir_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                glucose_data['time_in_range'] = match.group(1)
                print(f"    ✓ TIR gefunden: {match.group(1)}%")
                break
        
        # CV
        cv_patterns = [
            r'CV[:\s]+(\d+[.,]\d+)%',
            r'CV[:\s]+(\d+)%'
        ]
        
        for pattern in cv_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                cv_value = match.group(1).replace(',', '.')
                glucose_data['cv'] = cv_value
                print(f"    ✓ CV gefunden: {cv_value}%")
                break
        
        if not glucose_data:
            print(f"    ⚠ Keine Glukose-Daten gefunden")
        else:
            print(f"    ✓ {len(glucose_data)} Glucose-Werte gefunden")
        
    except Exception as e:
        print(f"    ⚠ Fehler beim Scrapen: {e}")
    
    return glucose_data

def scrape_insulin_data(page):
    """Scraped Insulin-Daten vom Dashboard"""
    print("  → Scrape Insulin-Daten...")
    return {}

def navigate_to_previous_day(page):
    """Navigiert zum vorherigen Tag"""
    print("  → Navigiere zum vorherigen Tag...")
    
    # Cookie-Banner prüfen
    print("    Prüfe Cookie-Banner vor Navigation...")
    cookie_selectors = [
        "button:has-text('Allow All')",
        "button:has-text('Reject All')",
        "button:has-text('Alle akzeptieren')"
    ]
    
    for selector in cookie_selectors:
        try:
            if page.locator(selector).is_visible(timeout=1000):
                page.locator(selector).click(force=True)
                print(f"    ✓ Cookie-Banner entfernt")
                time.sleep(1)
                break
        except:
            continue
    
    try:
        # WICHTIG: ALLE Dialoge/Modals/Overlays schließen!
        print("    Schließe alle Dialoge und Overlays...")

        # ESC drücken um Dialoge zu schließen
        try:
            page.keyboard.press("Escape")
            time.sleep(1)
            page.keyboard.press("Escape")
            time.sleep(1)
        except:
            pass

        # Alle möglichen Schließen-Buttons klicken
        close_selectors = [
            "button:has-text('Cancel')",
            "button:has-text('Abbrechen')",
            "button:has-text('×')",
            "button:has-text('Close')",
            "button:has-text('Schließen')",
            "[aria-label*='close' i]",
            "[aria-label*='Close' i]",
            "button:has-text('Reject All')",
            "button:has-text('Alle ablehnen')"
        ]

        for close_sel in close_selectors:
            try:
                if page.locator(close_sel).is_visible(timeout=500):
                    page.locator(close_sel).click(force=True)
                    print(f"    ✓ Dialog geschlossen: {close_sel}")
                    time.sleep(1)
            except:
                continue

        # Klicke IRGENDWO außerhalb um Modals zu schließen
        try:
            page.mouse.click(10, 10)
            time.sleep(1)
        except:
            pass

        time.sleep(2)
        
        # Datum VOR Navigation
        date_before = get_current_date_from_page(page)
        print(f"    Datum vor Navigation: {date_before}")

        # NEUE STRATEGIE: Finde die Pfeil-Buttons im Navigationsbereich
        print("    → Suche Pfeil-Buttons...")
        clicked = False

        try:
            # METHODE 1: Finde clickbare Buttons im Navigationsbereich (y ~ 400-550)
            nav_buttons = page.evaluate("""() => {
                const allElements = Array.from(document.querySelectorAll('button, div[role="button"], [onclick]'));
                const navButtons = allElements.filter(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    // Im mittleren Bereich, kleine Buttons
                    return rect.y > 350 && rect.y < 550 &&
                           rect.width < 60 && rect.width > 20 &&
                           rect.height < 60 && rect.height > 20;
                }).map(el => {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: rect.x + rect.width/2,
                        y: rect.y + rect.height/2,
                        width: rect.width,
                        tag: el.tagName,
                        text: el.textContent.trim().substring(0, 10)
                    };
                });
                // Sortiere nach x-Position (links zuerst)
                return navButtons.sort((a, b) => a.x - b.x);
            }""")

            print(f"    Gefundene Nav-Buttons: {len(nav_buttons)}")
            for btn in nav_buttons[:5]:
                print(f"      {btn['tag']} x={int(btn['x'])} y={int(btn['y'])} text='{btn['text']}'")

            # Klicke den ERSTEN (linksten) Button - das ist der "<" Button
            if nav_buttons:
                first_btn = nav_buttons[0]
                print(f"    → Klicke LINKEN Pfeil bei x={int(first_btn['x'])}, y={int(first_btn['y'])}")

                # EIN Klick reicht!
                page.mouse.click(first_btn['x'], first_btn['y'])
                print(f"    ✓ Pfeil-Button geklickt!")
                clicked = True

        except Exception as e:
            print(f"    Methode 1 fehlgeschlagen: {e}")

        # METHODE 2: Klicke direkt auf bekannte Koordinaten (vom Debug-Screenshot)
        if not clicked:
            print("    → Fallback: Klicke auf bekannte Koordinaten...")
            try:
                # Aus dem Debug-Script: Buttons bei x=480 und x=534, y=487
                page.mouse.click(480, 487)
                print(f"    ✓ Geklickt bei (480, 487)")
                clicked = True
            except Exception as e:
                print(f"    Koordinaten-Klick fehlgeschlagen: {e}")

        # METHODE 3: Keyboard-Navigation
        if not clicked:
            print("    → Versuche Keyboard-Navigation...")
            try:
                page.keyboard.press("ArrowLeft")
                print(f"    ✓ ArrowLeft gedrückt")
                clicked = True
            except:
                pass

        if not clicked:
            print(f"    ⚠ Kein Navigation-Button gefunden!")
            return False
        
        # Warten
        print("    Warte 10 Sekunden...")
        time.sleep(10)
        
        # Datum NACH Navigation
        date_after = get_current_date_from_page(page)
        print(f"    Datum nach Navigation: {date_after}")
        
        if date_before == date_after:
            print(f"    ⚠⚠⚠ WARNUNG: Datum NICHT geändert!")
            page.screenshot(path=f"debug_navigation_failed.png")
            return False
        else:
            print(f"    ✓ Datum geändert: {date_before} → {date_after}")
        
        page.screenshot(path=f"debug_after_navigation.png")
        return True
        
    except Exception as e:
        print(f"    ⚠ Navigation fehlgeschlagen: {e}")
        return False

def get_current_date_from_page(page):
    """Extrahiert das aktuell angezeigte Datum aus der Seite"""
    try:
        import re

        # NEUE METHODE: Suche direkt im Navigationsbereich nach dem Datum
        # Format: "Wed, Jan 7th, 2026" oder "Sat, Jan 3rd, 2026"
        date_text = page.evaluate("""() => {
            // Suche nach Element mit Datum-Format
            const allElements = Array.from(document.querySelectorAll('*'));
            for (const el of allElements) {
                const text = el.textContent.trim();
                // Englisches Format: "Wed, Jan 7th, 2026"
                if (/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{1,2}(st|nd|rd|th), \\d{4}$/.test(text)) {
                    return text;
                }
                // Deutsches Format: "Mi., 07. Jan. 2026"
                if (/^(Mo|Di|Mi|Do|Fr|Sa|So)\\., \\d{2}\\. (Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\\. \\d{4}$/.test(text)) {
                    return text;
                }
            }
            return null;
        }""")

        if date_text:
            print(f"      [Datum aus UI: {date_text}]")
            return date_text

        # Fallback: Regex auf body text
        page_text = page.inner_text("body")

        patterns = [
            # Englisch: "Wed, Jan 7th, 2026"
            r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}(st|nd|rd|th), \d{4}',
            # Deutsch: "Mi., 07. Jan. 2026"
            r'(Mo|Di|Mi|Do|Fr|Sa|So)\., \d{2}\. (Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\. \d{4}',
            # ISO: "07.01.2026"
            r'\d{2}\.\d{2}\.\d{4}'
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text)
            if match:
                return match.group(0)

        return "DATUM_NICHT_GEFUNDEN"

    except Exception as e:
        print(f"      [Datum-Fehler: {e}]")
        return "DATUM_FEHLER"

def main():
    all_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        if not login_to_glooko(page):
            print("!!! Login fehlgeschlagen !!!")
            browser.close()
            return False
        
        set_timeframe_to_one_day(page)

        page.screenshot(path="debug_dashboard_main.png")
        print(f"✓ Dashboard-Screenshot")

        # Um 23:50 scrapen wir den AKTUELLEN Tag (keine Navigation nötig)
        print(f"\n→ Scrape aktuellen Tag...\n")

        current_date = get_current_date_from_page(page)
        glucose = scrape_glucose_data(page)

        day_data = {
            'date': current_date,
            'label': 'today',
            'tir': glucose.get('time_in_range', ''),
            'cv': glucose.get('cv', ''),
            'scraped_at': datetime.now().isoformat()
        }

        all_data.append(day_data)
        page.screenshot(path="debug_today.png")

        print()
        browser.close()
    
    # JSON speichern (aktueller Tag)
    output_file = "glooko_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # CSV-Tabelle: Neue Zeile ANHÄNGEN (History aufbauen)
    csv_file = "glooko_history.csv"
    file_exists = os.path.exists(csv_file)

    with open(csv_file, 'a', encoding='utf-8') as f:
        # Header nur wenn Datei neu ist
        if not file_exists:
            f.write("Datum,TIR (%),CV (%),Gescraped am\n")
        # Neue Zeile anhängen
        for entry in all_data:
            f.write(f"{entry['date']},{entry['tir']},{entry['cv']},{entry['scraped_at']}\n")

    print(f"\n✓✓✓ Daten gescraped!")
    print(f"✓ JSON: {output_file}")
    print(f"✓ CSV:  {csv_file} (Zeile angehängt)")

    # Aktuelle Daten anzeigen
    print("\n┌─────────────────────────┬───────────┬───────────┐")
    print("│ Datum                   │ TIR (%)   │ CV (%)    │")
    print("├─────────────────────────┼───────────┼───────────┤")
    for entry in all_data:
        print(f"│ {entry['date']:<23} │ {entry['tir']:>9} │ {entry['cv']:>9} │")
    print("└─────────────────────────┴───────────┴───────────┘")

    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n!!! Scraping fehlgeschlagen !!!")
        exit(1)
    print("\n✓✓✓ Scraping erfolgreich! ✓✓✓")
