from atproto import Client, AtUri
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import threading  # Hier wird threading importiert

# Funktion zur Paginierung und zum Abrufen aller Reposts
def paginated_list_records(cli, repo, collection):
    """Ruft alle Einträge einer Sammlung (Posts/Reposts) ab, paginiert, um alle Daten zu erfassen."""
    params = {
        "repo": repo,
        "collection": collection,
        "limit": 100,
    }

    records = []
    while True:
        resp = cli.com.atproto.repo.list_records(params)
        records.extend(resp.records)

        if resp.cursor:
            params["cursor"] = resp.cursor
        else:
            break

    return records

# Funktion zur Löschung von Reposts vor einem bestimmten Datum
def delete_reposts(username, password, date_str, progress_callback):
    try:
        # Datum validieren
        keep_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Fehler", "Ungültiges Datum. Bitte im Format YYYY-MM-DD eingeben.")
        return

    # ATProto-Client initialisieren und anmelden
    cli = Client()
    try:
        cli.login(username, password)
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Einloggen: {e}")
        return

    # Alle Reposts abholen
    records = paginated_list_records(cli, username, "app.bsky.feed.repost")
    if len(records) == 0:
        messagebox.showinfo("Ergebnis", "Keine Reposts gefunden.")
        return

    deletes = []

    # Durchlaufe alle Reposts und überprüfe das Erstellungsdatum
    for repost in reversed(records):
        repost_date = datetime.fromisoformat(repost.value.created_at[:-1])
        if repost_date < keep_date:
            # URI des Eintrags abrufen und zum Löschen markieren
            uri = AtUri.from_str(repost.uri)
            deletes.append({
                "$type": "com.atproto.repo.applyWrites#delete",
                "rkey": uri.rkey,
                "collection": "app.bsky.feed.repost",
            })
        else:
            # Wenn neuere Reposts gefunden werden, abbrechen
            break

    # Lösche markierte Reposts und zeige Fortschritt an
    total_deletes = len(deletes)
    if total_deletes > 0:
        for i in range(0, total_deletes, 200):
            cli.com.atproto.repo.apply_writes({"repo": username, "writes": deletes[i:i + 200]})
            progress_callback(int((i + 200) / total_deletes * 100))

        messagebox.showinfo("Ergebnis", f"{total_deletes} Reposts wurden erfolgreich rückgängig gemacht.")
    else:
        messagebox.showinfo("Ergebnis", "Keine Reposts zum Löschen gefunden.")

# GUI-Klasse mit Tkinter und Fortschrittsbalken
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Reposts vor Datum rückgängig machen")

        # Benutzername, Passwort und Datum abfragen
        tk.Label(self.root, text="Benutzername:").pack(pady=5)
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack(pady=5)

        tk.Label(self.root, text="Passwort:").pack(pady=5)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)

        tk.Label(self.root, text="Datum (YYYY-MM-DD):\nReposts vor diesem Datum werden rückgängig gemacht.").pack(pady=5)
        self.date_entry = tk.Entry(self.root)
        self.date_entry.pack(pady=5)

        # Fortschrittsbalken
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Button zum Starten des Prozesses
        tk.Button(self.root, text="Reposts rückgängig machen", command=self.run_delete_reposts).pack(pady=10)

    def update_progress(self, value):
        """Aktualisiert den Fortschrittsbalken."""
        self.progress_bar['value'] = value
        self.root.update_idletasks()

    def run_delete_reposts(self):
        """Führt die Löschung der Reposts aus, indem Benutzereingaben verwendet werden."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        date_str = self.date_entry.get()

        if not username or not password or not date_str:
            messagebox.showerror("Fehler", "Alle Felder müssen ausgefüllt werden.")
            return

        # Setze den Fortschrittsbalken auf 0
        self.progress_bar['value'] = 0
        self.update_progress(0)

        # Starte den Repost-Löschprozess mit Fortschrittsanzeige
        threading.Thread(target=delete_reposts, args=(username, password, date_str, self.update_progress)).start()

# Hauptprogramm
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
