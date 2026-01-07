import os
import glob
import zipfile
import pandas as pd
import requests
from datetime import datetime
import json

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


def send_file_to_telegram(file_path, caption=""):
    """Sendet Datei an Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        response = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": f}
        )
    return response.json()


def analyze_glucose_data(csv_file):
    """Analysiert CGM/Glucose-Daten"""
    try:
        df = pd.read_csv(csv_file)
        
        # Verschiedene mögliche Spaltennamen für Glucose-Werte
        value_cols = ['Value', 'value', 'Glucose', 'glucose', 'BG', 'bg']
        value_col = None
        
        for col in value_cols:
            if col in df.columns:
                value_col = col
                break
        
        if value_col:
            # Nur numerische Werte
            values = pd.to_numeric(df[value_col], errors='coerce').dropna()
            
            if len(values) > 0:
                return {
                    'avg': values.mean(),
                    'min': values.min(),
                    'max': values.max(),
                    'std': values.std(),
                    'count': len(values),
                    'in_range': len(values[(values >= 70) & (values <= 180)]) / len(values) * 100
                }
    except Exception as e:
        print(f"Fehler bei Glucose-Analyse: {e}")
    
    return None


def analyze_insulin_data(csv_file):
    """Analysiert Insulin-Daten"""
    try:
        df = pd.read_csv(csv_file)
        
        # Mögliche Spaltennamen
        insulin_cols = ['Insulin', 'insulin', 'Units', 'units', 'Dose', 'dose']
        insulin_col = None
        
        for col in insulin_cols:
            if col in df.columns:
                insulin_col = col
                break
        
        if insulin_col:
            values = pd.to_numeric(df[insulin_col], errors='coerce').dropna()
            
            if len(values) > 0:
                return {
                    'total': values.sum(),
                    'avg': values.mean(),
                    'count': len(values)
                }
    except Exception as e:
        print(f"Fehler bei Insulin-Analyse: {e}")
    
    return None


def main():
    print("Starte Verarbeitung...")
    
    # Debug: Aktuelles Verzeichnis und Inhalt anzeigen
    print("Aktuelles Arbeitsverzeichnis:", os.getcwd())
    
    download_dir = "Downloads"
    if not os.path.exists(download_dir):
        print(f"Ordner '{download_dir}' existiert nicht!")
        send_to_telegram("⚠️ <b>Fehler:</b> Downloads-Ordner nicht gefunden!")
        return
    
    print(f"Inhalt von {download_dir}/:")
    print(os.listdir(download_dir))
    
    # Alle .zip Dateien im Downloads-Ordner sammeln
    zip_candidates = [
        os.path.join(download_dir, f)
        for f in os.listdir(download_dir)
        if f.lower().endswith('.zip')
    ]
    
    if not zip_candidates:
        print("Keine ZIP-Dateien im Downloads-Ordner gefunden!")
        send_to_telegram("⚠️ <b>Fehler:</b> Keine ZIP-Datei im Downloads-Ordner gefunden!")
        return
    
    # Neueste Datei nach Erstellungszeit auswählen
    latest_zip = max(zip_candidates, key=os.path.getctime)
    print(f"→ Neueste ZIP-Datei ausgewählt: {latest_zip}")
    print(f"  Größe: {os.path.getsize(latest_zip) / 1024 / 1024:.1f} MB")
    print(f"  Erstellt: {datetime.fromtimestamp(os.path.getctime(latest_zip)).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Entpacken
    extract_dir = "extracted"
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(latest_zip, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"ZIP erfolgreich entpackt nach: {extract_dir}")
    except Exception as e:
        print(f"Fehler beim Entpacken: {e}")
        send_to_telegram(f"⚠️ <b>Fehler:</b> ZIP konnte nicht entpackt werden!\n{e}")
        return
    
    # Alle CSVs finden
    csv_files = glob.glob(f"{extract_dir}/**/*.csv", recursive=True)
    print(f"{len(csv_files)} CSV-Dateien gefunden")
    
    if not csv_files:
        send_to_telegram("⚠️ Keine CSV-Dateien in der ZIP gefunden!")
        return
    
    # Daten analysieren
    glucose_stats = None
    insulin_stats = None
    
    for csv in csv_files:
        filename = os.path.basename(csv).lower()
        
        # Glucose-Daten
        if any(keyword in filename for keyword in ['glucose', 'cgm', 'bg', 'glukose']):
            glucose_stats = analyze_glucose_data(csv)
        
        # Insulin-Daten
        if any(keyword in filename for keyword in ['insulin', 'bolus']):
            insulin_stats = analyze_insulin_data(csv)
    
    # Bericht erstellen
    date_str = datetime.now().strftime('%d.%m.%Y')
    report = f"📊 <b>Glooko Update vom {date_str}</b>\n\n"
    report += f"✅ {len(csv_files)} Dateien verarbeitet\n\n"
    
    if glucose_stats:
        report += "🩸 <b>Glukose-Statistik:</b>\n"
        report += f"  • Durchschnitt: {glucose_stats['avg']:.1f} mg/dL\n"
        report += f"  • Min/Max: {glucose_stats['min']:.0f} / {glucose_stats['max']:.0f} mg/dL\n"
        report += f"  • Im Zielbereich (70-180): {glucose_stats['in_range']:.1f}%\n"
        report += f"  • Messungen: {glucose_stats['count']}\n\n"
    
    if insulin_stats:
        report += "💉 <b>Insulin-Statistik:</b>\n"
        report += f"  • Gesamt: {insulin_stats['total']:.1f} Einheiten\n"
        report += f"  • Durchschnitt: {insulin_stats['avg']:.2f} Einheiten\n"
        report += f"  • Anzahl Gaben: {insulin_stats['count']}\n\n"
    
    report += "💬 Du kannst jetzt Fragen zu deinen Daten stellen!"
    
    # An Telegram senden
    print("Sende Bericht an Telegram...")
    send_to_telegram(report)
    
    # ZIP auch hochladen (als Backup)
    print("Lade ZIP-Datei hoch...")
    send_file_to_telegram(latest_zip, caption=f"Vollständiger Export vom {date_str}")
    
    # Metadaten speichern für späteren Bot-Zugriff
    metadata = {
        'date': date_str,
        'files': [os.path.basename(f) for f in csv_files],
        'glucose': glucose_stats,
        'insulin': insulin_stats
    }
    
    with open('metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("✓ Erfolgreich abgeschlossen!")


if __name__ == "__main__":
    main()
