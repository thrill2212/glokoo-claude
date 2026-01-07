from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import time

# ────────────────────────────────────────────────
# KONFIGURATION - Wird aus GitHub Secrets geladen
# ────────────────────────────────────────────────
DOWNLOAD_DIR = "Downloads"
EMAIL = os.getenv("GLOOKO_EMAIL")
PASSWORT = os.getenv("GLOOKO_PASSWORD")
URL_LOGIN = "https://my.glooko.com/users/sign_in"
EXPORT_FORMAT = "csv"
# ────────────────────────────────────────────────

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        # Browser starten - headless für GitHub Actions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        print("→ Lade Login-Seite...")
        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)  # Extra Wartezeit für JavaScript
        
        page.screenshot(path="debug_01_login_page.png")
        print("Screenshot 1: Login-Seite geladen")

        # WICHTIG: Cookie-Banner ZUERST akzeptieren (blockiert oft Buttons!)
        print("→ Suche Cookie-Banner...")
        cookie_selectors = [
            "button:has-text('Allow All')",
            "button:has-text('Accept All')",
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Alle Cookies akzeptieren')",
            "#onetrust-accept-btn-handler",
            ".accept-cookies",
            "button[id*='accept']",
            "button[class*='accept']"
        ]
        
        for selector in cookie_selectors:
            try:
                if page.locator(selector).is_visible(timeout=3000):
                    page.locator(selector).click(timeout=5000)
                    print(f"✓ Cookie-Banner akzeptiert: {selector}")
                    time.sleep(2)
                    page.screenshot(path="debug_02_cookies_accepted.png")
                    break
            except:
                continue

        # Email-Feld finden und LANGSAM ausfüllen
        print("→ Fülle Email-Feld aus...")
        
        email_selectors = [
            "input[type='email']",
            "#user_email",
            "input[name='user[email]']",
            "input[placeholder*='mail' i]"
        ]
        
        email_filled = False
        for selector in email_selectors:
            try:
                email_field = page.locator(selector).first
                email_field.wait_for(timeout=10000, state="visible")
                
                # Feld leeren (falls vorausgefüllt)
                email_field.click()
                email_field.fill("")
                time.sleep(0.5)
                
                # WICHTIG: Zeichen für Zeichen eintippen (simuliert echtes Tippen)
                print(f"  Tippe Email: {EMAIL}")
                for char in EMAIL:
                    email_field.type(char, delay=50)  # 50ms zwischen Zeichen
                
                time.sleep(0.5)
                
                # Validierung: Prüfen ob Email korrekt eingetragen wurde
                entered_value = email_field.input_value()
                print(f"  Eingetragener Wert: {entered_value}")
                
                if entered_value == EMAIL:
                    print(f"✓ Email korrekt eingetragen mit: {selector}")
                    email_filled = True
                    break
                else:
                    print(f"⚠ Email-Wert falsch! Erwartet: {EMAIL}, Bekommen: {entered_value}")
                    # Nochmal versuchen mit fill() statt type()
                    email_field.fill(EMAIL)
                    time.sleep(0.5)
                    entered_value = email_field.input_value()
                    if entered_value == EMAIL:
                        print(f"✓ Email mit fill() korrigiert")
                        email_filled = True
                        break
                    
            except Exception as e:
                print(f"  Email-Selector {selector} fehlgeschlagen: {str(e)[:100]}")
                continue
        
        if not email_filled:
            print("!!! FEHLER: Email konnte nicht eingetragen werden !!!")
            page.screenshot(path="debug_03_email_failed.png")
            browser.close()
            return False

        page.screenshot(path="debug_03_email_entered.png")

        # Passwort-Feld - gleiche Methode
        print("→ Fülle Passwort-Feld aus...")
        
        password_selectors = [
            "input[type='password']",
            "#user_password",
            "input[name='user[password]']"
        ]
        
        password_filled = False
        for selector in password_selectors:
            try:
                password_field = page.locator(selector).first
                password_field.wait_for(timeout=10000, state="visible")
                
                password_field.click()
                password_field.fill("")
                time.sleep(0.5)
                
                # Passwort eintippen
                for char in PASSWORT:
                    password_field.type(char, delay=50)
                
                time.sleep(0.5)
                print(f"✓ Passwort eingetragen mit: {selector}")
                password_filled = True
                break
                
            except Exception as e:
                print(f"  Passwort-Selector {selector} fehlgeschlagen: {str(e)[:100]}")
                continue
        
        if not password_filled:
            print("!!! FEHLER: Passwort konnte nicht eingetragen werden !!!")
            page.screenshot(path="debug_04_password_failed.png")
            browser.close()
            return False

        time.sleep(1)
        page.screenshot(path="debug_04_before_login.png")
        print("Screenshot: Vor Login-Klick")

        # Login-Button klicken
        print("→ Suche Login-Button...")
        
        submit_selectors = [
            # Spezifische Buttons
            "button:has-text('Log In')",
            "button:has-text('Log in')",
            "button:has-text('Sign in')",
            "button:has-text('Anmelden')",
            
            # Input-Buttons
            "input[type='submit'][value*='Log' i]",
            "input[type='submit'][value*='Sign' i]",
            "input[type='submit'][value*='Anmeld' i]",
            
            # Allgemeine Submit-Elemente
            "button[type='submit']",
            "input[type='submit']",
            
            # CSS-Klassen
            "button.btn-primary",
            "button.submit",
            ".login-button"
        ]

        clicked = False
        for selector in submit_selectors:
            try:
                print(f"  Versuche: {selector}")
                button = page.locator(selector).first
                
                # Warten bis sichtbar
                if not button.is_visible(timeout=5000):
                    continue
                
                # Prüfen ob disabled
                if button.is_disabled():
                    print(f"  → Button disabled")
                    continue
                
                # Klicken
                button.click(timeout=10000)
                print(f"✓ Login-Button geklickt: {selector}")
                clicked = True
                break
                
            except Exception as e:
                print(f"  → Fehlgeschlagen: {str(e)[:80]}")
                continue

        # Fallback: Enter-Taste
        if not clicked:
            print("→ Fallback: Enter-Taste im Passwort-Feld")
            try:
                page.locator("input[type='password']").first.press("Enter")
                print("✓ Enter gedrückt")
                clicked = True
            except Exception as e:
                print(f"!!! Enter-Taste fehlgeschlagen: {e}")

        if not clicked:
            print("!!! Login-Button nicht gefunden !!!")
            page.screenshot(path="debug_05_button_not_found.png")
            browser.close()
            return False

        # Warten auf Seitenwechsel
        print("→ Warte auf Login-Erfolg...")
        time.sleep(6)
        
        page.screenshot(path="debug_06_after_login.png")
        print("Screenshot: Nach Login-Versuch")
        print(f"Aktuelle URL: {page.url}")

        # Cookie-Banner NACH Login nochmal prüfen
        print("→ Prüfe Cookie-Banner nach Login...")
        for selector in cookie_selectors:
            try:
                if page.locator(selector).is_visible(timeout=2000):
                    page.locator(selector).click(timeout=3000)
                    print(f"✓ Cookie-Banner (nach Login) akzeptiert")
                    time.sleep(2)
                    break
            except:
                continue

        # Dashboard-Indikatoren prüfen
        dashboard_indicators = [
            "text=Profile",
            "text=Profil", 
            "text=Summary",
            "text=Zusammenfassung",
            "text=Export as CSV",
            "text=Als CSV exportieren",
            "text=Charts",
            "text=Diagramme"
        ]

        logged_in = False
        for ind in dashboard_indicators:
            try:
                page.wait_for_selector(ind, timeout=20000, state="visible")
                print(f"✓ Dashboard erkannt: {ind}")
                logged_in = True
                break
            except:
                continue

        if not logged_in:
            print("!!! Dashboard nicht erkannt !!!")
            print(f"URL: {page.url}")
            
            # Prüfen ob auf Login-Seite geblieben
            if "sign_in" in page.url or "login" in page.url.lower():
                print("⚠ Noch auf Login-Seite - Login fehlgeschlagen!")
            
            page.screenshot(path="debug_07_login_failed.png")
            browser.close()
            return False

        print("\n✓✓✓ Login erfolgreich!\n")
        page.screenshot(path="debug_08_dashboard.png")

        # CSV-EXPORT
        downloaded = False

        try:
            print("→ Starte CSV-Export...")
            
            # Warte auf Export-Button
            export_selectors = [
                "text=Export as CSV",
                "text=Als CSV exportieren",
                "button:has-text('Export')",
                "a:has-text('Export')"
            ]
            
            export_clicked = False
            for selector in export_selectors:
                try:
                    if page.locator(selector).is_visible(timeout=5000):
                        page.locator(selector).click()
                        print(f"✓ Export-Button geklickt: {selector}")
                        export_clicked = True
                        break
                except:
                    continue
            
            if not export_clicked:
                print("!!! Export-Button nicht gefunden !!!")
                page.screenshot(path="debug_09_export_button_missing.png")
                browser.close()
                return False

            # Warte auf Modal
            page.wait_for_selector('[data-testid="dialog-container-export-to-csv"]', timeout=15000)
            print("✓ Export-Modal geöffnet")
            
            page.screenshot(path="debug_10_export_modal.png")

            modal = page.locator('[data-testid="dialog-container-export-to-csv"]')
            confirm_button = modal.locator('button:has-text("Export"), button:has-text("Exportieren")').first

            try:
                with page.expect_download(timeout=90000) as download_info:
                    confirm_button.click(force=True, timeout=30000)
                print("✓ Exportieren-Button geklickt")

                download = download_info.value
                filename = download.suggested_filename or f"glooko_export_{time.strftime('%Y-%m-%d')}.zip"
                save_path = os.path.join(DOWNLOAD_DIR, filename)
                download.save_as(save_path)
                print(f"\n✓✓✓ Download erfolgreich: {save_path}\n")
                downloaded = True

            except Exception as e:
                print(f"Download fehlgeschlagen: {str(e)}")
                page.screenshot(path="debug_11_download_failed.png")

        except Exception as outer_e:
            print(f"CSV-Export-Prozess fehlgeschlagen: {str(outer_e)}")
            page.screenshot(path="debug_12_export_failed.png")

        browser.close()
        return downloaded

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n!!! Export fehlgeschlagen !!!")
        exit(1)
    print("\n✓✓✓ Export erfolgreich abgeschlossen! ✓✓✓")
