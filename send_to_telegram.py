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

def create_simple_report(all_data):
    """Erstellt Bericht mit Daten fuer Heute und Gestern"""

    if not all_data or len(all_data) == 0:
        return "⚠️ Keine Daten verfuegbar!"

    # Heute (neueste Daten = Index 0)
    today = all_data[0]
    today_date = today.get('date', 'Heute')
    today_glucose = today.get('glucose', {})
    today_tir = today_glucose.get('time_in_range')
    today_cv = today_glucose.get('cv')

    # Gestern (falls vorhanden = Index 1)
    yesterday = None
    yesterday_date = None
    yesterday_tir = None
    yesterday_cv = None

    if len(all_data) > 1:
        yesterday = all_data[1]
        yesterday_date = yesterday.get('date', 'Gestern')
        yesterday_glucose = yesterday.get('glucose', {})
        yesterday_tir = yesterday_glucose.get('time_in_range')
        yesterday_cv = yesterday_glucose.get('cv')

    # Bericht erstellen
    report = "📊 <b>Glooko Tagesbericht</b>\n"
    report += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    # === HEUTE ===
    report += f"📅 <b>HEUTE</b> ({today_date})\n"
    report += "┌─────────────────────\n"
    report += f"│ 🎯 TIR:  <b>{format_value(today_tir)}%</b>"

    # TIR Bewertung inline
    try:
        tir_val = float(today_tir) if today_tir else 0
        if tir_val >= 70:
            report += " ✅\n"
        elif tir_val >= 50:
            report += " ⚠️\n"
        else:
            report += " ❌\n"
    except:
        report += "\n"

    report += f"│ 📈 CV:   <b>{format_value(today_cv)}%</b>"

    # CV Bewertung inline
    try:
        cv_val = float(today_cv) if today_cv else 0
        if cv_val <= 36:
            report += " ✅\n"
        else:
            report += " ⚠️\n"
    except:
        report += "\n"

    report += "└─────────────────────\n\n"

    # === GESTERN ===
    if yesterday:
        report += f"📅 <b>GESTERN</b> ({yesterday_date})\n"
        report += "┌─────────────────────\n"
        report += f"│ 🎯 TIR:  <b>{format_value(yesterday_tir)}%</b>"

        try:
            tir_val = float(yesterday_tir) if yesterday_tir else 0
            if tir_val >= 70:
                report += " ✅\n"
            elif tir_val >= 50:
                report += " ⚠️\n"
            else:
                report += " ❌\n"
        except:
            report += "\n"

        report += f"│ 📈 CV:   <b>{format_value(yesterday_cv)}%</b>"

        try:
            cv_val = float(yesterday_cv) if yesterday_cv else 0
            if cv_val <= 36:
                report += " ✅\n"
            else:
                report += " ⚠️\n"
        except:
            report += "\n"

        report += "└─────────────────────\n\n"

    # === VERGLEICH ===
    if yesterday_tir and today_tir:
        report += "📊 <b>VERGLEICH</b>\n"
        report += "┌─────────────────────\n"

        tir_emoji, tir_change = calculate_change(today_tir, yesterday_tir)
        cv_emoji, cv_change = calculate_change(today_cv, yesterday_cv)

        report += f"│ TIR: {tir_emoji} {tir_change}\n"
        report += f"│ CV:  {cv_emoji} {cv_change}\n"
        report += "└─────────────────────\n\n"

    # === BEWERTUNG ===
    report += "💡 <b>Zielwerte:</b>\n"
    report += "• TIR ≥70% = ✅ | CV ≤36% = ✅\n"

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
