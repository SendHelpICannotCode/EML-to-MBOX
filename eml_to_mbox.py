import os
import sys
import json
import mailbox
import email
import time
import csv
import tkinter as tk
from tkinter import filedialog
from email.utils import getaddresses

def read_config(config_path: str) -> dict:
    """
    Liest die JSON-Konfigurationsdatei ein und gibt sie als Dict zurück.
    Erwartet z.B.:
    {
      "excluded_recipients": [...],
      "csv_basename": "my_email_analysis",
      "mbox_basename": "my_mbox_export"
    }
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def print_progress_bar(iteration: int, total: int, bar_length: int = 30):
    """
    Zeigt einen Ladebalken in der Konsole an.
    
    Parameter:
    -----------
    iteration: int
        Wie viele Elemente wurden bereits verarbeitet
    total: int
        Gesamtanzahl der zu verarbeitenden Elemente
    bar_length: int
        Länge des Balkens in der Konsole
    """
    fraction = iteration / total  # Anteil des Fortschritts (0..1)
    filled = int(bar_length * fraction)  # Anzahl gefüllter "█"
    bar = "█" * filled + "-" * (bar_length - filled)
    percent = fraction * 100

    # \r -> Zurück an den Zeilenanfang (Überschreiben)
    sys.stdout.write(f"\r[{bar}] {percent:5.1f}%  ({iteration}/{total})")
    sys.stdout.flush()

    if iteration == total:
        print()

def analyze_recipients(eml_folder: str, csv_file: str, excluded_list: list[str]) -> None:
    """
    Durchsucht alle EML-Dateien im Ordner 'eml_folder' und sammelt jede distincte
    "Raw-Address" (z.B. "Kai Beckmann" <amarysium@gmail.com>).
    Für jede Adresse ermitteln wir:
      - wie oft sie vorkommt (count)
      - den extrahierten Mailbox-Part (z.B. "amarysium@gmail.com")
      - ob die Mailbox in 'excluded_list' steht (ja/nein)

    Das Ergebnis wird in 'csv_file' gespeichert.
    Zeigt währenddessen einen Ladebalken.
    """
    # Dict-Aufbau:
    #   key   = raw_address (z.B. "\"Kai Beckmann\" <amarysium@gmail.com>")
    #   value = {
    #       "mailbox": str,    # "amarysium@gmail.com"
    #       "count": int,      # wie oft sie gefunden wurde
    #       "excluded": bool   # ob mailbox in excluded_list
    #   }
    analysis_dict = {}

    eml_files = [f for f in os.listdir(eml_folder) if f.lower().endswith(".eml")]
    total_files = len(eml_files)

    if total_files == 0:
        print("Keine EML-Dateien gefunden!")
        # CSV wenigstens als leere Struktur anlegen:
        with open(csv_file, 'w', newline='', encoding='utf-8') as empty_csv:
            writer = csv.writer(empty_csv)
            writer.writerow(["Raw Address", "Count", "Mailbox", "Excluded"])
        return

    print("Starte Empfänger-Analyse...")
    for i, file_name in enumerate(eml_files, start=1):
        file_path = os.path.join(eml_folder, file_name)

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            eml_content = f.read()

        msg = email.message_from_string(eml_content)

        # "To"-Feld parsen
        to_field = msg.get('To', "")
        parsed_list = getaddresses([to_field])
        # z.B. [('Kai Beckmann', 'amarysium@gmail.com'), ('AYm', 'amarysium@gmail.com'), ...]

        for (name, addr) in parsed_list:
            display_name = name.strip()
            mailbox_part = addr.strip().lower()

            # Raw-Address zusammenbauen
            # Falls kein display_name -> z.B. "<amarysium@gmail.com>"
            if display_name:
                raw_address = f"\"{display_name}\" <{addr}>"
            else:
                raw_address = f"<{addr}>"

            # Im Dict anlegen oder aktualisieren
            if raw_address not in analysis_dict:
                is_excluded = (mailbox_part in excluded_list)
                analysis_dict[raw_address] = {
                    "mailbox": mailbox_part,
                    "count": 0,
                    "excluded": is_excluded
                }
            analysis_dict[raw_address]["count"] += 1

        # Fortschrittsbalken updaten
        print_progress_bar(i, total_files)

    # CSV schreiben
    with open(csv_file, 'w', newline='', encoding='utf-8') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Raw Address", "Count", "Mailbox", "Excluded?"])
        for raw_address, info in analysis_dict.items():
            writer.writerow([
                raw_address,
                info["count"],
                info["mailbox"],
                "Yes" if info["excluded"] else "No"
            ])

    print(f"Analyse abgeschlossen. CSV-Datei erstellt unter: {csv_file}")

def eml_to_mbox(eml_folder: str, mbox_file: str, excluded_list: list[str]) -> None:
    """
    Konvertiert alle EML-Dateien in 'eml_folder' in eine Mbox-Datei 'mbox_file'
    und zeigt einen Ladebalken.
    Mails werden übersprungen, wenn mindestens eine ihrer "To"-Adressen
    in der excluded_list steht.
    """
    eml_files = [f for f in os.listdir(eml_folder) if f.lower().endswith(".eml")]
    total_files = len(eml_files)

    if total_files == 0:
        print("Keine EML-Dateien gefunden!")
        return

    print("Starte Konvertierung zu Mbox...")
    mbox = mailbox.mbox(mbox_file)

    included_count = 0
    skipped_count = 0

    from email.utils import getaddresses

    for i, filename in enumerate(eml_files, start=1):
        file_path = os.path.join(eml_folder, filename)

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            eml_content = f.read()

        msg = email.message_from_string(eml_content)

        # Prüfen, ob eine der To-Adressen in excluded_list ist
        to_field = msg.get('To', "")
        parsed_list = getaddresses([to_field])

        skip_mail = False
        for (name, addr) in parsed_list:
            mailbox_part = addr.strip().lower()
            if mailbox_part in excluded_list:
                skip_mail = True
                break
        
        if skip_mail:
            skipped_count += 1
        else:
            mbox.add(msg)
            included_count += 1

        print_progress_bar(i, total_files)

    mbox.flush()
    print(f"\nKonvertierung abgeschlossen.")
    print(f"Insgesamt: {total_files} EML-Dateien gefunden.")
    print(f"Eingefügt in Mbox: {included_count}, Übersprungen: {skipped_count}")
    print(f"Mbox-Datei erstellt unter: {mbox_file}")

def main():
    """
    Hauptfunktion:
    1) config.json laden
    2) Tkinter-Dialog -> Ordner mit EML-Dateien
    3) CSV-Analyse -> Schreibt CSV-Datei "basename_timestamp.csv"
    4) Nutzer fragen, ob wir eine Mbox erzeugen wollen
    5) Wenn ja -> Mbox "basename_timestamp.mbox"
       -> EML-Dateien, deren To-Adressen ausgeschlossen sind, überspringen
    """
    # 1) Konfiguration laden
    config_path = "config.json"
    try:
        config = read_config(config_path)
    except FileNotFoundError as e:
        print(f"Fehler: {e}")
        sys.exit(1)

    # Empfänger-Ausschlussliste normalisieren
    excluded_list = [addr.strip().lower() for addr in config.get("excluded_recipients", [])]

    # CSV- und Mbox-Basenamen aus der Config holen
    # Fallback, falls sie nicht definiert sind
    csv_basename = config.get("csv_basename", "csv_output")
    mbox_basename = config.get("mbox_basename", "mbox_output")

    # 2) EML-Ordner wählen
    root = tk.Tk()
    root.withdraw()
    eml_folder = filedialog.askdirectory(title="Wähle den Ordner mit deinen EML-Dateien aus")
    if not eml_folder:
        print("Kein Ordner ausgewählt. Skript wird beendet.")
        sys.exit(0)

    # 3) Timestamp und Pfade
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    csv_file = os.path.join(script_dir, f"{csv_basename}_{timestamp}.csv")
    mbox_file = os.path.join(script_dir, f"{mbox_basename}_{timestamp}.mbox")

    # Analyse
    analyze_recipients(eml_folder, csv_file, excluded_list)

    # Nutzer fragen
    user_input = input("\nMöchtest du jetzt die Mbox-Erzeugung starten? (J/n) ").strip().lower()
    if user_input not in ["j", "ja", ""]:
        print("Abbruch. Skript beendet.")
        sys.exit(0)

    # Konvertierung
    eml_to_mbox(eml_folder, mbox_file, excluded_list)
    print(f"\nFertig! CSV: {csv_file}\n       Mbox: {mbox_file}")

if __name__ == "__main__":
    main()
