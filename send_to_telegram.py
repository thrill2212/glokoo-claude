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
    """Erstellt vereinfachten Bericht mit nur TIR und CV"""
    
    if not all_data or len(all_data) == 0:
        return "⚠️ Keine Daten verfuegbar!"
    
    # Heute (neueste Daten = Index 0)
    today = all_data[0]
    today_date = today.get('date', 'Heute')
    today_glucose = today.get('glucose', {})
    
    today_tir = today_glucose.get('time_in_range')
    today_cv = today_glucose.get('cv')
    
    # Gestern (falls vorhanden = Index 1)
    yesterday_tir = None
    yesterday_cv = None
    
    if len(all_data) > 1:
        yesterday = all_data[1]
        yesterday_glucose = yesterday.get('glucose', {})
        yesterday_tir = yesterday_glucose.get('time_in_range')
        yesterday_cv = yesterday_glucose.get('cv')
    
    # Bericht erstellen
    report = f"📊 <b>Diabetes Update - {today_date}</b>\n\n"
    
    # Time in Range (Zielbereich)
    tir_emoji, tir_change = calculate_change(today_tir, yesterday_tir)
    report += f"🎯 <b>Zeit im Zielbereich (TIR):</b>\n"
    report += f"   • Heute: <b>{format_value(today_tir)}%</b>\n"
    
    if yesterday_tir:
        report += f"   • Gestern: {format_value(yesterday_tir)}%\n"
        report += f"   • Veraenderung: {tir_emoji} <i>{tir_change}</i>\n"
    
    report += "\n"
    
    # CV (Variationskoeffizient)
    cv_emoji, cv_change = calculate_change(today_cv, yesterday_cv)
    report += f"📊 <b>Variationskoeffizient (CV):</b>\n"
    report += f"   • Heute: <b>{format_value(today_cv)}%</b>\n"
    
    if yesterday_cv:
        report += f"   • Gestern: {format_value(yesterday_cv)}%\n"
        report += f"   • Veraenderung: {cv_emoji} <i>{cv_change}</i>\n"
    
    report += "\n"
    
    # Interpretation
    report += "💡 <b>Bewertung:</b>\n"
    
    # TIR Bewertung
    try:
        tir_val = float(today_tir) if today_tir else 0
        if tir_val >= 70:
            report += "   • TIR: ✅ Sehr gut (≥70%)\n"
        elif tir_val >= 50:
            report += "   • TIR: ⚠️ Ausbaufaehig (50-70%)\n"
        else:
            report += "   • TIR: ⚠️ Verbesserungsbedarf (<50%)\n"
    except:
        pass
    
    # CV Bewertung
    try:
        cv_val = float(today_cv) if today_cv else 0
        if cv_val <= 36:
            report += "   • CV: ✅ Stabil (≤36%)\n"
        else:
            report += "   • CV: ⚠️ Hoehere Variabilitaet (>36%)\n"
    except:
        pass
    
    report += "\n💬 <i>Du kannst Fragen zu deinen Daten stellen!</i>"
    
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
