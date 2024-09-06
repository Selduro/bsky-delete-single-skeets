import requests
from urllib.parse import urlparse
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk

# Funktion zum Abrufen des Authentifizierungstokens
def get_auth_token(username, password):
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {
        "identifier": username,
        "password": password
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()["accessJwt"], response.json()["did"]
    else:
        raise Exception("Authentifizierung fehlgeschlagen: " + response.text)

# Funktion zum Abrufen aller Skeets
def get_all_skeets(auth_token, did):
    url = f"https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor={did}"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["feed"]
    else:
        raise Exception("Fehler beim Abrufen der Skeets: " + response.text)

# Funktion zum Analysieren der Skeets mit den drei Filtern
def analyze_skeets(skeets, min_likes, min_reskeets, filter_threads):
    threads_count = 0
    like_condition_count = 0
    reskeet_condition_count = 0
    no_criteria_count = 0
    single_skeets = []

    skeet_dict = {skeet['post']['uri']: skeet for skeet in skeets}

    # Set zum Markieren aller Skeets, die zu einem Thread gehören
    thread_uris = set()

    # Identifizieren der Threads, wenn der Filter für Threads aktiviert ist
    if filter_threads:
        for skeet in skeets:
            if skeet['post']['uri'] in thread_uris:
                continue

            # Überprüfen, ob der Skeet eine Antwort ist und ob es eine eigene Antwort darauf gibt
            if 'reply' in skeet:
                parent_uri = skeet['reply']['parent']['uri']
                if parent_uri in skeet_dict and skeet_dict[parent_uri]['post']['author']['did'] == skeet['post']['author']['did']:
                    thread_uris.add(skeet['post']['uri'])
                    thread_uris.add(parent_uri)

            # Überprüfen, ob es Antworten auf diesen Skeet gibt
            for reply in skeets:
                if 'reply' in reply and reply['reply']['parent']['uri'] == skeet['post']['uri']:
                    thread_uris.add(skeet['post']['uri'])
                    thread_uris.add(reply['post']['uri'])

    # Einteilen in Threads und Single Skeets
    for skeet in skeets:
        if skeet['post']['uri'] in thread_uris:
            threads_count += 1
        elif skeet['post']['likeCount'] >= min_likes:
            like_condition_count += 1
        elif skeet['post']['repostCount'] >= min_reskeets:
            reskeet_condition_count += 1
        else:
            no_criteria_count += 1
            single_skeets.append(skeet)

    return threads_count, like_condition_count, reskeet_condition_count, no_criteria_count, single_skeets

# Funktion zum Löschen der Einzel-Skeets
def delete_single_skeets(auth_token, single_skeets, progress_callback, status_callback):
    url = "https://bsky.social/xrpc/com.atproto.repo.deleteRecord"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    total = len(single_skeets)
    for idx, skeet in enumerate(single_skeets):
        # Extrahiere rkey aus dem URI
        uri_parts = urlparse(skeet['post']['uri'])
        rkey = uri_parts.path.split('/')[-1]

        payload = {
            "collection": "app.bsky.feed.post",
            "repo": skeet['post']['author']['did'],
            "rkey": rkey
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Deleted Skeet: {skeet['post']['uri']}")
        else:
            print(f"Failed to delete Skeet: {skeet['post']['uri']} - {response.text}")

        progress_callback((idx + 1) / total * 100)
        status_callback(idx + 1, total)

# GUI-Anwendung
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluesky Skeets Manager")

        self.username = None
        self.password = None
        self.min_likes = None
        self.min_reskeets = None
        self.filter_threads = None
        self.auth_token = None
        self.did = None
        self.skeets = []

        self.init_gui()

    def init_gui(self):
        tk.Button(self.root, text="Login", command=self.get_credentials).pack(pady=10)
        tk.Button(self.root, text="Filtereinstellungen setzen", command=self.get_filters).pack(pady=10)
        tk.Button(self.root, text="Analysieren & Löschen", command=self.analyze_and_delete).pack(pady=10)

    def get_credentials(self):
        self.username = simpledialog.askstring("Benutzername", "Bitte geben Sie Ihren Bluesky-Benutzernamen ein:")
        self.password = simpledialog.askstring("Passwort", "Bitte geben Sie Ihr Bluesky-Passwort ein:", show='*')

        if not self.username or not self.password:
            messagebox.showerror("Fehler", "Benutzername oder Passwort nicht eingegeben!")
            return
        
        try:
            self.auth_token, self.did = get_auth_token(self.username, self.password)
            messagebox.showinfo("Erfolg", "Authentifizierung erfolgreich.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Authentifizierung: {e}")

    def get_filters(self):
        if not self.auth_token:
            messagebox.showerror("Fehler", "Bitte loggen Sie sich zuerst ein.")
            return

        try:
            self.min_likes = simpledialog.askinteger("Minimale Likes", "Mindestanzahl von Likes zum Behalten des Skeets:", initialvalue=0)
            self.min_reskeets = simpledialog.askinteger("Minimale Reskeets", "Mindestanzahl von Reskeets zum Behalten des Skeets:", initialvalue=0)
            self.ask_thread_filter()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Setzen der Filter: {e}")

    def ask_thread_filter(self):
        def set_thread_filter(answer):
            self.filter_threads = (answer == 'ja')
            filter_window.destroy()
            messagebox.showinfo("Erfolg", "Filtereinstellungen aktualisiert.")

        filter_window = tk.Toplevel(self.root)
        filter_window.title("Thread-Filter")

        label = tk.Label(filter_window, text="Soll der Thread-Filter aktiviert werden?")
        label.pack(pady=10)

        btn_ja = tk.Button(filter_window, text="Ja", command=lambda: set_thread_filter('ja'))
        btn_ja.pack(side=tk.LEFT, padx=10, pady=10)

        btn_nein = tk.Button(filter_window, text="Nein", command=lambda: set_thread_filter('nein'))
        btn_nein.pack(side=tk.LEFT, padx=10, pady=10)

    def analyze_and_delete(self):
        if not self.min_likes or not self.min_reskeets:
            messagebox.showerror("Fehler", "Bitte setzen Sie zuerst die Filter.")
            return

        try:
            self.skeets = get_all_skeets(self.auth_token, self.did)
            print(f"Fetched {len(self.skeets)} Skeets.")

            threads_count, like_condition_count, reskeet_condition_count, no_criteria_count, single_skeets = analyze_skeets(
                self.skeets, 
                self.min_likes, 
                self.min_reskeets, 
                self.filter_threads
            )

            result_parts = []
            if self.filter_threads is not None:
                if self.filter_threads:
                    result_parts.append(f"Anzahl der Skeets, die Teil eines Threads sind: {threads_count}")
                else:
                    result_parts.append("Thread-Filter wurde nicht gesetzt.")
            if self.min_likes > 0:
                result_parts.append(f"Skeets, die die Like-Bedingung erfüllen: {like_condition_count}")
            if self.min_reskeets > 0:
                result_parts.append(f"Skeets, die die Reskeet-Bedingung erfüllen: {reskeet_condition_count}")
            result_parts.append(f"Skeets, die keine der Bedingungen erfüllen (zum Löschen): {no_criteria_count}")

            result = "\n".join(result_parts)
            
            if single_skeets:
                confirmation = messagebox.askyesno("Bestätigung", f"{result}\n\nMöchten Sie die Skeets, die keine der Bedingungen erfüllen, löschen?")
                
                if confirmation:
                    self.show_progress_bar(single_skeets)
                else:
                    messagebox.showinfo("Abgebrochen", "Löschung abgebrochen.")
            else:
                messagebox.showinfo("Info", "Keine Skeets zum Löschen.")

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Analysieren und Löschen der Skeets: {e}")

    def show_progress_bar(self, single_skeets):
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Löschvorgang")

        label = tk.Label(progress_window, text="Lösche Skeets, bitte warten...")
        label.pack(pady=10)

        progress = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate")
        progress.pack(pady=10)

        status_label = tk.Label(progress_window, text="0 von 0 Skeets gelöscht")
        status_label.pack(pady=10)

        def update_progress(value):
            progress['value'] = value
            progress_window.update_idletasks()

        def update_status(deleted, total):
            status_label.config(text=f"{deleted} von {total} Skeets gelöscht")

        def delete_skeets():
            delete_single_skeets(self.auth_token, single_skeets, update_progress, update_status)
            progress_window.destroy()

        # Starten des Löschvorgangs im Hintergrund
        self.root.after(100, delete_skeets)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
