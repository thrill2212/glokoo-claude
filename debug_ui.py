"""
Debug-Skript: Analysiert die Glooko UI um Navigation-Elemente zu finden
"""
from playwright.sync_api import sync_playwright
import os
import time
import json

EMAIL = os.getenv("GLOOKO_EMAIL")
PASSWORD = os.getenv("GLOOKO_PASSWORD")
URL_LOGIN = "https://my.glooko.com/users/sign_in"

def main():
    with sync_playwright() as p:
        # Browser SICHTBAR starten für besseres Debugging
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        # Login
        print("→ Login...")
        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Cookie-Banner
        try:
            page.click("button:has-text('Allow All')", timeout=5000)
            print("✓ Cookie akzeptiert")
            time.sleep(2)
        except:
            pass

        # Login-Formular
        page.fill("input[type='email']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        page.press("input[type='password']", "Enter")
        print("✓ Login abgeschickt")

        # Warten auf Dashboard
        time.sleep(15)
        print(f"URL nach Login: {page.url}")

        # Screenshot
        page.screenshot(path="debug_full_page.png", full_page=True)

        # Cookie-Banner nochmal wegklicken
        try:
            page.click("button:has-text('Allow All')", timeout=3000)
            time.sleep(2)
        except:
            pass

        print("\n" + "="*60)
        print("ANALYSE: Suche nach Navigations-Elementen")
        print("="*60)

        # 1. Finde das Time-Dropdown
        print("\n1. DROPDOWN-ANALYSE:")
        dropdown_info = page.evaluate("""() => {
            // Suche nach "2 weeks" oder "Time" Text
            const allElements = Array.from(document.querySelectorAll('*'));
            const timeElements = allElements.filter(el => {
                const text = el.textContent;
                return text && (text.includes('2 weeks') || text.includes('1 day') || text.includes('Time:'));
            }).slice(0, 10);

            return timeElements.map(el => ({
                tag: el.tagName,
                text: el.textContent.substring(0, 50),
                className: el.className,
                clickable: window.getComputedStyle(el).cursor === 'pointer'
            }));
        }""")

        for info in dropdown_info[:5]:
            print(f"  {info['tag']}: '{info['text'][:30]}' class='{info['className'][:40]}' clickable={info['clickable']}")

        # 2. Finde Elemente NEBEN dem Datum
        print("\n2. DATUM-BEREICH ANALYSE:")
        date_area = page.evaluate("""() => {
            // Finde Element mit Datum (Dec, Jan, 2025, 2026)
            const allElements = Array.from(document.querySelectorAll('*'));
            const dateElement = allElements.find(el => {
                const text = el.textContent;
                return text && text.includes('Dec') && text.includes('2025');
            });

            if (!dateElement) return {found: false};

            // Finde Parent und Siblings
            const parent = dateElement.parentElement;
            const siblings = parent ? Array.from(parent.children) : [];

            return {
                found: true,
                dateTag: dateElement.tagName,
                dateClass: dateElement.className,
                parentTag: parent?.tagName,
                parentClass: parent?.className,
                siblingsCount: siblings.length,
                siblings: siblings.map(s => ({
                    tag: s.tagName,
                    text: s.textContent.substring(0, 20),
                    className: s.className
                }))
            };
        }""")

        print(f"  Datum gefunden: {date_area.get('found')}")
        if date_area.get('found'):
            print(f"  Parent: {date_area.get('parentTag')} class='{date_area.get('parentClass', '')[:40]}'")
            print(f"  {date_area.get('siblingsCount')} Siblings:")
            for sib in date_area.get('siblings', [])[:5]:
                print(f"    {sib['tag']}: '{sib['text']}' class='{sib['className'][:30]}'")

        # 3. Finde ALLE clickbaren Elemente im Hauptbereich
        print("\n3. CLICKBARE ELEMENTE:")
        clickables = page.evaluate("""() => {
            const allElements = Array.from(document.querySelectorAll('*'));
            const clickableElements = allElements.filter(el => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return (style.cursor === 'pointer' || el.onclick) &&
                       rect.top > 200 && rect.top < 500 &&  // Im mittleren Bereich
                       rect.width < 100;  // Kleine Elemente (wie Buttons)
            });

            return clickableElements.slice(0, 20).map(el => ({
                tag: el.tagName,
                text: el.textContent.substring(0, 30),
                className: el.className,
                rect: el.getBoundingClientRect()
            }));
        }""")

        for info in clickables:
            print(f"  {info['tag']}: '{info['text'][:20]}' x={int(info['rect']['x'])} y={int(info['rect']['y'])}")

        # 4. Versuche das Dropdown zu öffnen
        print("\n4. VERSUCHE DROPDOWN ZU ÖFFNEN:")
        try:
            # Klicke auf "2 weeks" Text
            page.click("text=2 weeks", timeout=5000)
            print("  ✓ Auf '2 weeks' geklickt")
            time.sleep(2)
            page.screenshot(path="debug_dropdown_open.png")

            # Suche nach Optionen
            options = page.evaluate("""() => {
                const allElements = Array.from(document.querySelectorAll('*'));
                return allElements.filter(el => {
                    const text = el.textContent.trim();
                    return text === '1 day' || text === '1 week' || text === '2 weeks' || text === '3 months';
                }).map(el => ({
                    tag: el.tagName,
                    text: el.textContent.trim(),
                    className: el.className,
                    visible: el.offsetParent !== null
                }));
            }""")

            print(f"  Gefundene Optionen nach Klick:")
            for opt in options[:10]:
                print(f"    {opt['tag']}: '{opt['text']}' visible={opt['visible']}")

            # Versuche "1 day" zu klicken
            try:
                page.click("text=1 day", timeout=3000)
                print("  ✓ '1 day' geklickt!")
                time.sleep(5)
                page.screenshot(path="debug_after_1day.png")
            except Exception as e:
                print(f"  ⚠ Konnte '1 day' nicht klicken: {e}")

        except Exception as e:
            print(f"  ⚠ Dropdown-Klick fehlgeschlagen: {e}")

        # 5. Suche nach SVG-Pfeilen
        print("\n5. SVG-ANALYSE:")
        svgs = page.evaluate("""() => {
            const svgs = Array.from(document.querySelectorAll('svg'));
            return svgs.map((svg, i) => {
                const parent = svg.parentElement;
                const rect = svg.getBoundingClientRect();
                return {
                    index: i,
                    parentTag: parent?.tagName,
                    parentClass: parent?.className?.substring?.(0, 40) || '',
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };
            });
        }""")

        # Zeige SVGs im relevanten Bereich (y zwischen 300-500)
        relevant_svgs = [s for s in svgs if 300 < s['y'] < 500]
        print(f"  {len(svgs)} SVGs gesamt, {len(relevant_svgs)} im Navigationsbereich:")
        for svg in relevant_svgs[:10]:
            print(f"    #{svg['index']}: parent={svg['parentTag']} x={svg['x']} y={svg['y']} size={svg['width']}x{svg['height']}")

        # 6. Versuche links vom Datum zu klicken
        print("\n6. KLICK-VERSUCH LINKS VOM DATUM:")
        try:
            # Finde Datum-Position
            date_pos = page.evaluate("""() => {
                const allElements = Array.from(document.querySelectorAll('*'));
                const dateEl = allElements.find(el => {
                    const text = el.textContent;
                    return text && text.includes('Dec') && text.includes('Jan') && el.children.length === 0;
                });
                if (dateEl) {
                    const rect = dateEl.getBoundingClientRect();
                    return {x: rect.x, y: rect.y + rect.height/2, found: true};
                }
                return {found: false};
            }""")

            if date_pos.get('found'):
                # Klicke 50px links vom Datum
                click_x = date_pos['x'] - 50
                click_y = date_pos['y']
                print(f"  Datum bei x={date_pos['x']}, klicke bei x={click_x}, y={click_y}")
                page.mouse.click(click_x, click_y)
                time.sleep(3)
                page.screenshot(path="debug_after_left_click.png")
                print("  ✓ Geklickt! Screenshot gespeichert")
        except Exception as e:
            print(f"  ⚠ Fehler: {e}")

        print("\n" + "="*60)
        print("Analyse abgeschlossen. Screenshots gespeichert.")
        print("="*60)

        # Warte damit User den Browser sehen kann
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    main()
