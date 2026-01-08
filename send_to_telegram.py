import os
import json
import requests
from datetime import datetime

# Aus GitHub Secrets
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_to_telegram(text):
    """Sendet Nachricht an Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })
    return response.json()

def calculate_change(current, previous):
    """Berechnet Veraenderung und gibt Emoji zurueck"""
    if current is None or previous is None:
        return "", ""
    
    try:
        current_val = float(current)
        previous_val = float(previous)
        
        diff = current_val - previous_val
        
        if abs(diff) < 0.1:
            return "➡️", "±0%"
        elif diff > 0:
            return "📈", f"+{diff:.1f}%"
        else:
            return "📉", f"{diff:.1f}%"
    except:
        return "", ""

def format_value(value):
    """Formatiert Wert (ersetzt . mit , fuer deutsche Schreibweise)"""
    if value is None:
        return "N/A"
    try:
        # Konvertiere zu float und zurueck fuer einheitliches Format
        num = float(str(value).replace(',', '.'))
        return f"{num:.1f}".replace('.', ',')
    except:
        return str(value)

def get_motivational_message(tir_today, tir_yesterday, cv_today):
    """Generiert eine motivierende Nachricht basierend auf den Werten"""
    try:
        tir = float(tir_today) if tir_today else 0
        tir_prev = float(tir_yesterday) if tir_yesterday else tir
        cv = float(cv_today) if cv_today else 50
        diff = tir - tir_prev

        # Sehr guter Tag
        if tir >= 80 and cv <= 33:
            return "🌟 Fantastischer Tag! Weiter so, du machst das großartig!"
        # Guter Tag
        elif tir >= 70:
            if diff > 5:
                return "💪 Super Verbesserung! Dein Einsatz zahlt sich aus!"
            else:
                return "👍 Solider Tag im Zielbereich. Gut gemacht!"
        # Okay Tag mit Verbesserung
        elif tir >= 50 and diff > 0:
            return "📈 Es geht aufwärts! Jeder Schritt zählt."
        # Schwieriger Tag
        elif tir < 50:
            return "🤗 Nicht jeder Tag ist perfekt - morgen wird besser!"
        # Rückgang
        elif diff < -10:
            return "💡 Kleiner Rückschritt, aber du schaffst das! Fokus auf heute."
        else:
            return "☀️ Neuer Tag, neue Chance! Du hast es in der Hand."
    except:
        return "☀️ Guten Morgen! Mach das Beste aus dem Tag!"


def get_tip_of_the_day(tir, cv):
    """Gibt einen passenden Tipp basierend auf den Werten"""
    try:
        tir_val = float(tir) if tir else 0
        cv_val = float(cv) if cv else 50

        if cv_val > 40:
            tips = [
                "💡 Tipp: Regelmäßige Mahlzeiten helfen, Schwankungen zu reduzieren.",
                "💡 Tipp: Achte auf versteckte Kohlenhydrate in Getränken.",
                "💡 Tipp: Bewegung nach dem Essen kann Spitzen abflachen."
            ]
        elif tir_val < 60:
            tips = [
                "💡 Tipp: Überprüfe deine Basalrate mit deinem Arzt.",
                "💡 Tipp: Führe ein Ernährungstagebuch für 3 Tage.",
                "💡 Tipp: Stress kann den Blutzucker beeinflussen - gönn dir Pausen."
            ]
        else:
            tips = [
                "💡 Tipp: Bleib dran - Konstanz ist der Schlüssel!",
                "💡 Tipp: Genug Schlaf hilft bei der Blutzuckerkontrolle.",
                "💡 Tipp: Feiere deine Erfolge, auch die kleinen!"
            ]

        import random
        return random.choice(tips)
    except:
        return ""


def create_simple_report(all_data):
    """Erstellt kompakten, motivierenden Morgenbericht"""

    if not all_data or len(all_data) == 0:
        return "⚠️ Keine Daten verfügbar!"

    # Heute (Index 0)
    today = all_data[0]
    today_glucose = today.get('glucose', {})
    today_tir = today_glucose.get('time_in_range')
    today_cv = today_glucose.get('cv')

    # Gestern (Index 1)
    yesterday_tir = None
    yesterday_cv = None
    if len(all_data) > 1:
        yesterday = all_data[1]
        yesterday_glucose = yesterday.get('glucose', {})
        yesterday_tir = yesterday_glucose.get('time_in_range')
        yesterday_cv = yesterday_glucose.get('cv')

    # Berechne Veränderung
    tir_emoji, tir_change = calculate_change(today_tir, yesterday_tir)
    cv_emoji, cv_change = calculate_change(today_cv, yesterday_cv)

    # === NACHRICHT AUFBAUEN ===
    report = "☀️ <b>Guten Morgen, Heiko!</b>\n\n"

    # Motivierende Nachricht
    motivation = get_motivational_message(today_tir, yesterday_tir, today_cv)
    report += f"{motivation}\n\n"

    # TIR - Klare Aussage
    tir_status = "✅" if float(today_tir or 0) >= 70 else "⚠️" if float(today_tir or 0) >= 50 else "❌"
    report += f"🎯 Du warst gestern <b>{format_value(today_tir)}%</b> im Zielbereich {tir_status}\n"

    if yesterday_tir:
        try:
            diff = float(today_tir) - float(yesterday_tir)
            if diff > 0:
                report += f"   ↗️ Das sind <b>+{abs(diff):.0f}%</b> mehr als vorgestern ({format_value(yesterday_tir)}%)\n"
            elif diff < 0:
                report += f"   ↘️ Das sind <b>{abs(diff):.0f}%</b> weniger als vorgestern ({format_value(yesterday_tir)}%)\n"
            else:
                report += f"   ➡️ Gleich wie vorgestern ({format_value(yesterday_tir)}%)\n"
        except:
            pass

    report += "\n"

    # CV - Klare Aussage
    cv_status = "✅" if float(today_cv or 50) <= 36 else "⚠️"
    report += f"📈 Deine Blutzucker-Stabilität lag bei <b>{format_value(today_cv)}%</b> {cv_status}\n"

    if yesterday_cv:
        try:
            cv_diff = float(today_cv) - float(yesterday_cv)
            if abs(cv_diff) < 1:
                report += f"   ➡️ Ähnlich stabil wie vorgestern\n"
            elif cv_diff < 0:
                report += f"   ✨ Stabiler als vorgestern!\n"
            else:
                report += f"   📊 Etwas mehr Schwankungen als vorgestern\n"
        except:
            pass

    report += "\n"

    # Tages-Tipp
    tip = get_tip_of_the_day(today_tir, today_cv)
    if tip:
        report += f"{tip}\n\n"

    # Abschluss
    report += "🎯 <i>Dein Ziel: TIR ≥70% · CV ≤36%</i>"

    return report

def create_weekly_summary(all_data):
    """Erstellt Wochen-Zusammenfassung (nur TIR und CV)"""
    
    if not all_data or len(all_data) < 2:
        return None
    
    tir_values = []
    cv_values = []
    
    for day in all_data:
        glucose = day.get('glucose', {})
        
        tir = glucose.get('time_in_range')
        cv = glucose.get('cv')
        
        if tir:
            try:
                tir_values.append(float(tir))
            except:
                pass
        
        if cv:
            try:
                cv_values.append(float(cv))
            except:
                pass
    
    if not tir_values and not cv_values:
        return None
    
    report = f"📈 <b>Wochenzusammenfassung ({len(all_data)} Tage):</b>\n\n"
    
    if tir_values:
        avg_tir = sum(tir_values) / len(tir_values)
        min_tir = min(tir_values)
        max_tir = max(tir_values)
        
        report += f"🎯 <b>Zeit im Zielbereich:</b>\n"
        report += f"   • Durchschnitt: <b>{avg_tir:.1f}%</b>\n"
        report += f"   • Bester Tag: {max_tir:.1f}%\n"
        report += f"   • Schwaechster Tag: {min_tir:.1f}%\n\n"
    
    if cv_values:
        avg_cv = sum(cv_values) / len(cv_values)
        min_cv = min(cv_values)
        max_cv = max(cv_values)
        
        report += f"📊 <b>Variationskoeffizient:</b>\n"
        report += f"   • Durchschnitt: <b>{avg_cv:.1f}%</b>\n"
        report += f"   • Stabilster Tag: {min_cv:.1f}%\n"
        report += f"   • Variabelster Tag: {max_cv:.1f}%\n\n"
    
    # Trend
    if len(tir_values) >= 3:
        recent_avg = sum(tir_values[:3]) / 3
        older_avg = sum(tir_values[3:]) / len(tir_values[3:]) if len(tir_values) > 3 else recent_avg
        
        if recent_avg > older_avg + 2:
            report += "📈 <b>Trend:</b> Verbesserung in den letzten Tagen! 👍\n"
        elif recent_avg < older_avg - 2:
            report += "📉 <b>Trend:</b> Leichter Rueckgang in den letzten Tagen\n"
        else:
            report += "➡️ <b>Trend:</b> Stabil\n"
    
    return report

def main():
    print("Starte Telegram-Versand...")
    
    # JSON-Datei laden
    json_file = "glooko_data.json"
    
    if not os.path.exists(json_file):
        send_to_telegram("⚠️ <b>Fehler:</b> Keine Daten gefunden!")
        print("!!! JSON-Datei nicht gefunden !!!")
        return False
    
    with open(json_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    print(f"✓ {len(all_data)} Tage geladen")
    
    if not all_data:
        send_to_telegram("⚠️ Keine Daten zum Senden!")
        return False
    
    # Tages-Bericht (Heute vs. Gestern)
    daily_report = create_simple_report(all_data)
    send_to_telegram(daily_report)
    print("✓ Tagesbericht gesendet")
    
    # Wochen-Zusammenfassung (falls genug Daten vorhanden)
    if len(all_data) >= 3:
        weekly_report = create_weekly_summary(all_data)
        if weekly_report:
            # Trennlinie
            send_to_telegram("─" * 30)
            send_to_telegram(weekly_report)
            print("✓ Wochenzusammenfassung gesendet")
    
    print("✓ Alle Daten erfolgreich gesendet!")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n!!! Versand fehlgeschlagen !!!")
        exit(1)
    print("\n✓✓✓ Telegram-Versand erfolgreich! ✓✓✓")
