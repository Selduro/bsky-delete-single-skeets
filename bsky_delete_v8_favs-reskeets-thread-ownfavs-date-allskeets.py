import requests
from urllib.parse import urlparse
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from datetime import datetime
import threading

def get_auth_token(username, password):
    """Authentifiziert den Benutzer und gibt das Token sowie die DID zurück."""
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": username, "password": password}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()["accessJwt"], response.json()["did"]
    else:
        raise Exception("Authentifizierung fehlgeschlagen: " + response.text)

def get_all_skeets(auth_token, did, progress_callback):
    """Ruft alle Skeets des Benutzers ab, inklusive Paginierung und Fortschrittsmeldung."""
    url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
    headers = {"Authorization": f"Bearer {auth_token}"}
    all_skeets = []
    cursor = None
    total_skeets = 0  # Zähler für die gesamte Anzahl der Skeets

    while True:
        params = {"actor": did}
        if cursor:
            params["cursor"] = cursor  # Füge den Cursor hinzu, falls vorhanden

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            all_skeets.extend(data["feed"])  # Füge die neuen Skeets zur Liste hinzu
            total_skeets = len(all_skeets)
            progress_callback(total_skeets)  # Aktualisiere den Fortschritt

            # Überprüfe, ob ein Cursor für die nächste Seite vorhanden ist
            if "cursor" in data:
                cursor = data["cursor"]
            else:
                break  # Wenn kein Cursor vorhanden ist, gibt es keine weiteren Skeets
        else:
            raise Exception(f"Fehler beim Abrufen der Skeets: {response.text}")

    return all_skeets

def get_user_likes(auth_token, did):
    """Ruft alle Skeets ab, die vom Benutzer geliket wurden."""
    url = f"https://bsky.social/xrpc/app.bsky.feed.getActorLikes?actor={did}"
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "feed" in data:
            return set(skeet['post']['uri'] for skeet in data["feed"])
        else:
            raise Exception("Unerwartete Antwortstruktur: 'feed' nicht gefunden")
    else:
        raise Exception("Fehler beim Abrufen der Likes: " + response.text)

def analyze_skeets(skeets, min_likes, min_reskeets, filter_threads, filter_self_liked, user_liked_uris, filter_date, filter_by_date):
    """Analysiert die Skeets nach den angegebenen Filterkriterien."""
    max_value = 999999999999999999999999999999
    min_likes = min_likes if min_likes is not None else max_value
    min_reskeets = min_reskeets if min_reskeets is not None else max_value

    # Initialisiere Zähler
    skeets_to_delete = set()
    thread_uris = set()

    # Wenn der Datumsfilter deaktiviert ist, setzen wir ein Datum weit in der Zukunft
    if not filter_by_date:
        filter_date = datetime(2500, 1, 1)

    # Identifizieren der Threads, wenn der Filter für Threads aktiviert ist
    if filter_threads:
        for skeet in skeets:
            if skeet['post']['uri'] in thread_uris:
                continue

            if 'reply' in skeet:
                parent_uri = skeet['reply']['parent']['uri']
                if parent_uri in thread_uris:
                    thread_uris.add(skeet['post']['uri'])
                    continue

            for reply in skeets:
                if 'reply' in reply and reply['reply']['parent']['uri'] == skeet['post']['uri']:
                    thread_uris.add(skeet['post']['uri'])
                    thread_uris.add(reply['post']['uri'])

    # Analysiere die Skeets basierend auf den Filtern
    for skeet in skeets:
        is_thread = skeet['post']['uri'] in thread_uris
        has_min_likes = skeet['post']['likeCount'] >= min_likes
        has_min_reskeets = skeet['post']['repostCount'] >= min_reskeets
        is_self_liked = skeet['post']['uri'] in user_liked_uris if filter_self_liked else False

        # Überprüfe das Erstellungsdatum des Skeets
        skeet_date = datetime.strptime(skeet['post']['indexedAt'][:10], "%Y-%m-%d") if 'indexedAt' in skeet['post'] else None
        is_before_date = skeet_date < filter_date if skeet_date else False

        # Skeet wird gelöscht, wenn KEINER der aktiven Filter zutrifft
        if not (is_thread or has_min_likes or has_min_reskeets or is_self_liked or not is_before_date):
            skeets_to_delete.add(skeet['post']['uri'])

    return skeets_to_delete  # Rückgabe der Liste der Skeet-URIs, die gelöscht werden sollen

def delete_single_skeets(auth_token, skeet_uris, progress_callback, status_callback):
    """Löscht die Skeets, die keine der Filterbedingungen erfüllen."""
    url = "https://bsky.social/xrpc/com.atproto.repo.deleteRecord"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    total = len(skeet_uris)
    for idx, uri in enumerate(skeet_uris):
        uri_parts = urlparse(uri)
        rkey = uri_parts.path.split('/')[-1]

        payload = {
            "collection": "app.bsky.feed.post",
            "repo": uri_parts.netloc,
            "rkey": rkey
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print(f"Deleted Skeet: {uri}")
        else:
            print(f"Failed to delete Skeet: {uri} - {response.text}")

        progress_callback((idx + 1) / total * 100)
        status_callback(idx + 1, total)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluesky Skeets Manager")

        self.username = None
        self.password = None
        self.min_likes = None
        self.min_reskeets = None
        self.filter_threads = False
        self.filter_self_liked = False
        self.filter_by_date = False
        self.filter_date = None
        self.auth_token = None
        self.did = None
        self.skeets = []
        self.user_liked_uris = set()

        self.init_gui()

    def init_gui(self):
        tk.Button(self.root, text="Login", command=self.get_credentials).pack(pady=10)
        tk.Button(self.root, text="Filtereinstellungen setzen", command=self.show_filter_window).pack(pady=10)
        tk.Button(self.root, text="Analysieren und Löschen", command=self.analyze_and_delete).pack(pady=10)

    def get_credentials(self):
        """Zeigt ein Dialogfeld zum Eingeben der Anmeldeinformationen an und speichert das Token."""
        self.username = simpledialog.askstring("Benutzername", "Bitte geben Sie Ihren Bluesky-Benutzernamen ein:")
        self.password = simpledialog.askstring("Passwort", "Bitte geben Sie Ihr Passwort ein:")

        if self.username and self.password:
            try:
                self.auth_token, self.did = get_auth_token(self.username, self.password)
                messagebox.showinfo("Erfolg", "Erfolgreich eingeloggt.")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Einloggen: {e}")

    def show_filter_window(self):
        """Zeigt das Filtereinstellungsfenster an."""
        self.filter_window = tk.Toplevel(self.root)
        self.filter_window.title("Filtereinstellungen")

        tk.Label(self.filter_window, text="Mindestanzahl Likes:").pack(pady=5)
        self.min_likes_var = tk.BooleanVar()
        self.min_likes_checkbox = tk.Checkbutton(self.filter_window, text="Aktivieren", variable=self.min_likes_var, command=self.update_likes_entry_state)
        self.min_likes_checkbox.pack(pady=5)
        self.min_likes_entry = tk.Entry(self.filter_window)
        self.min_likes_entry.pack(pady=5)
        self.min_likes_entry.config(state='disabled')

        tk.Label(self.filter_window, text="Mindestanzahl Reskeets:").pack(pady=5)
        self.min_reskeets_var = tk.BooleanVar()
        self.min_reskeets_checkbox = tk.Checkbutton(self.filter_window, text="Aktivieren", variable=self.min_reskeets_var, command=self.update_reskeets_entry_state)
        self.min_reskeets_checkbox.pack(pady=5)
        self.min_reskeets_entry = tk.Entry(self.filter_window)
        self.min_reskeets_entry.pack(pady=5)
        self.min_reskeets_entry.config(state='disabled')

        tk.Label(self.filter_window, text="Teil eines Threads (aktivieren, um diesen Filter zu setzen):").pack(pady=5)
        self.filter_threads_var = tk.BooleanVar()
        self.filter_threads_checkbox = tk.Checkbutton(self.filter_window, text="Aktivieren", variable=self.filter_threads_var)
        self.filter_threads_checkbox.pack(pady=5)

        tk.Label(self.filter_window, text="Von mir geliket:").pack(pady=5)
        self.filter_self_liked_var = tk.BooleanVar()
        self.filter_self_liked_checkbox = tk.Checkbutton(self.filter_window, text="Aktivieren", variable=self.filter_self_liked_var)
        self.filter_self_liked_checkbox.pack(pady=5)

        tk.Label(self.filter_window, text="Vor diesem Datum (YYYY-MM-DD):").pack(pady=5)
        self.filter_date_var = tk.BooleanVar()
        self.filter_date_checkbox = tk.Checkbutton(self.filter_window, text="Aktivieren", variable=self.filter_date_var, command=self.update_date_entry_state)
        self.filter_date_checkbox.pack(pady=5)
        self.filter_date_entry = tk.Entry(self.filter_window)
        self.filter_date_entry.pack(pady=5)
        self.filter_date_entry.config(state='disabled')

        tk.Button(self.filter_window, text="Filter anwenden", command=self.apply_filters).pack(pady=10)

    def update_likes_entry_state(self):
        """Aktualisiert den Zustand des Eingabefelds für Mindestanzahl Likes basierend auf der Aktivierungsstatus."""
        if self.min_likes_var.get():
            self.min_likes_entry.config(state='normal')
        else:
            self.min_likes_entry.config(state='disabled')

    def update_reskeets_entry_state(self):
        """Aktualisiert den Zustand des Eingabefelds für Mindestanzahl Reskeets basierend auf der Aktivierungsstatus."""
        if self.min_reskeets_var.get():
            self.min_reskeets_entry.config(state='normal')
        else:
            self.min_reskeets_entry.config(state='disabled')

    def update_date_entry_state(self):
        """Aktualisiert den Zustand des Eingabefelds für das Datum basierend auf der Aktivierungsstatus."""
        if self.filter_date_var.get():
            self.filter_date_entry.config(state='normal')
        else:
            self.filter_date_entry.config(state='disabled')

    def apply_filters(self):
        """Wendet die Filtereinstellungen an und schließt das Fenster."""
        try:
            min_likes = self.min_likes_entry.get()
            min_reskeets = self.min_reskeets_entry.get()

            if self.min_likes_var.get() and not min_likes:
                messagebox.showerror("Fehler", "Bitte geben Sie eine Zahl für die Mindestanzahl Likes ein.")
                return
            
            if self.min_reskeets_var.get() and not min_reskeets:
                messagebox.showerror("Fehler", "Bitte geben Sie eine Zahl für die Mindestanzahl Reskeets ein.")
                return

            self.min_likes = int(min_likes) if min_likes else None
            self.min_reskeets = int(min_reskeets) if min_reskeets else None
            self.filter_threads = self.filter_threads_var.get()
            self.filter_self_liked = self.filter_self_liked_var.get()

            # Datumseingabe verarbeiten
            if self.filter_date_var.get():
                filter_date_str = self.filter_date_entry.get()
                if filter_date_str:
                    try:
                        self.filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d")
                    except ValueError:
                        messagebox.showerror("Fehler", "Ungültiges Datum. Bitte geben Sie das Datum im Format YYYY-MM-DD ein.")
                        return
                else:
                    messagebox.showerror("Fehler", "Bitte geben Sie ein Datum ein.")
                    return
                self.filter_by_date = True
            else:
                self.filter_by_date = False
                self.filter_date = None

            # Visuelle Bestätigung für gesetzte Filter
            messagebox.showinfo("Filter angewendet", "Die Filter wurden erfolgreich angewendet.")
            self.filter_window.destroy()
        except ValueError as e:
            messagebox.showerror("Fehler", str(e))

    def analyze_and_delete(self):
        """Analysiert die Skeets basierend auf den Filtereinstellungen und löscht die entsprechenden Skeets."""
        if not self.auth_token:
            messagebox.showerror("Fehler", "Bitte loggen Sie sich zuerst ein.")
            return

        # Fortschrittsfenster erstellen
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Fortschritt beim Abrufen der Skeets")
        self.progress_label = tk.Label(self.progress_window, text="Abrufen der Skeets: 0")
        self.progress_label.pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_window, orient="horizontal", length=300, mode="indeterminate")
        self.progress_bar.pack(pady=10)
        self.progress_bar.start(10)  # Starte die Fortschrittsanimation

        # Blockiere das Hauptfenster während des Abrufs
        self.progress_window.grab_set()

        # Funktion, um den Fortschritt zu aktualisieren
        def update_progress(total_skeets):
            self.progress_label['text'] = f"Abrufen der Skeets: {total_skeets}"
            self.progress_window.update_idletasks()

        # Thread zum Abrufen und Analysieren der Skeets
        def run_analysis():
            try:
                self.skeets = get_all_skeets(self.auth_token, self.did, update_progress)

                # Überprüfe, ob das Progressbar-Fenster noch existiert, bevor es gestoppt und freigegeben wird
                if self.progress_bar.winfo_exists():
                    self.progress_bar.stop()

                if self.progress_window.winfo_exists():
                    self.progress_window.grab_release()  # Gib das Hauptfenster frei
                    self.progress_window.destroy()

                if self.filter_self_liked:
                    self.user_liked_uris = get_user_likes(self.auth_token, self.did)
                
                skeets_to_delete = analyze_skeets(
                    self.skeets, self.min_likes, self.min_reskeets, self.filter_threads, self.filter_self_liked, self.user_liked_uris, self.filter_date, self.filter_by_date
                )

                result_message = (
                    f"Analyse abgeschlossen.\n\n"
                    f"Anzahl der überprüften Skeets: {len(self.skeets)}\n\n"
                    f"Skeets, die keine der Bedingungen erfüllen und gelöscht werden: {len(skeets_to_delete)}"
                )

                if skeets_to_delete:
                    confirm = messagebox.askyesno("Bestätigung", result_message + "\n\nMöchten Sie diese Skeets löschen?")
                    if confirm:
                        self.delete_skeets(list(skeets_to_delete))
                    else:
                        messagebox.showinfo("Abgebrochen", "Löschvorgang abgebrochen.")
                else:
                    messagebox.showinfo("Information", result_message + "\n\nKeine Skeets entsprechen den Löschkriterien.")
            except Exception as e:
                if self.progress_bar.winfo_exists():
                    self.progress_bar.stop()

                if self.progress_window.winfo_exists():
                    self.progress_window.grab_release()  # Gib das Hauptfenster frei
                    self.progress_window.destroy()

                messagebox.showerror("Fehler", f"Fehler bei der Analyse oder Löschung der Skeets: {e}")

        # Starte den Thread
        threading.Thread(target=run_analysis).start()

    def delete_skeets(self, skeet_uris):
        """Löscht die markierten Skeets."""
        # Fortschrittsfenster erstellen
        self.delete_progress_window = tk.Toplevel(self.root)
        self.delete_progress_window.title("Fortschritt beim Löschen der Skeets")
        self.delete_progress_label = tk.Label(self.delete_progress_window, text="Löschen der Skeets: 0 von {}".format(len(skeet_uris)))
        self.delete_progress_label.pack(pady=10)
        self.delete_progress_bar = ttk.Progressbar(self.delete_progress_window, orient="horizontal", length=300, mode="determinate")
        self.delete_progress_bar.pack(pady=10)
        self.delete_progress_bar["maximum"] = len(skeet_uris)
        self.delete_progress_bar["value"] = 0

        # Blockiere das Hauptfenster während des Löschens
        self.delete_progress_window.grab_set()

        def update_progress_bar(progress):
            """Aktualisiert die Fortschrittsanzeige."""
            self.delete_progress_bar["value"] = progress
            self.delete_progress_label['text'] = f"Löschen der Skeets: {progress} von {len(skeet_uris)}"
            self.delete_progress_window.update_idletasks()

        def update_status_callback(current, total):
            """Aktualisiert den Fortschritt nach jedem gelöschten Skeet."""
            update_progress_bar(current)

        # Thread zum Löschen der Skeets
        def run_deletion():
            try:
                delete_single_skeets(self.auth_token, skeet_uris, update_progress_bar, update_status_callback)

                # Löschvorgang abgeschlossen
                messagebox.showinfo("Fertig", "Alle markierten Skeets wurden gelöscht.")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Löschen der Skeets: {e}")
            finally:
                # Fortschrittsfenster freigeben und schließen
                self.delete_progress_window.grab_release()
                self.delete_progress_window.destroy()

        # Starte den Thread für das Löschen
        threading.Thread(target=run_deletion).start()

# Hauptprogramm
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
