# Quick and dirty aus Vorhandenem zusammengeschustert. Man hätte es sicher beides über atproto und damit effizienter machen können, aber mir egal
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse
from atproto import Client, AtUri
import threading


def get_auth_token(username, password):
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": username, "password": password}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()["accessJwt"], response.json()["did"]
    else:
        raise Exception("Authentifizierung fehlgeschlagen: " + response.text)


def get_all_skeets(auth_token, did):
    url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
    headers = {"Authorization": f"Bearer {auth_token}"}
    all_skeets = []
    cursor = None

    while True:
        params = {"actor": did}
        if cursor:
            params["cursor"] = cursor  

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            all_skeets.extend(data["feed"])  

            if "cursor" in data:
                cursor = data["cursor"]
            else:
                break 
        else:
            raise Exception(f"Fehler beim Abrufen der Skeets: {response.text}")

    return all_skeets


def delete_skeets(auth_token, skeet_uris):
    url = "https://bsky.social/xrpc/com.atproto.repo.deleteRecord"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    for uri in skeet_uris:
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


def delete_old_skeets(username, password):
    try:
        auth_token, did = get_auth_token(username, password)
        all_skeets = get_all_skeets(auth_token, did)


        skeets_to_delete = [
            skeet['post']['uri'] for skeet in all_skeets 
            if 'indexedAt' in skeet['post'] and datetime.strptime(skeet['post']['indexedAt'][:10], "%Y-%m-%d") < tagedelta
        ]

        if skeets_to_delete:
            print(f"{len(skeets_to_delete)} Skeets werden gelöscht.")
            delete_skeets(auth_token, skeets_to_delete)
        else:
            print("Keine Skeets zum Löschen gefunden.")
    except Exception as e:
        print(f"Fehler: {e}")




def paginated_list_records(cli, repo, collection):
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


def delete_reposts(username, password):
    cli = Client()
    try:
        cli.login(username, password)
    except Exception as e:
        print(f"Fehler beim Einloggen: {e}")
        return


    records = paginated_list_records(cli, username, "app.bsky.feed.repost")
    if len(records) == 0:
        print("Keine Reposts gefunden.")
        return

    deletes = []


    for repost in reversed(records):
        repost_date = datetime.fromisoformat(repost.value.created_at[:-1])
        if repost_date < tagedelta:
            uri = AtUri.from_str(repost.uri)
            deletes.append({
                "$type": "com.atproto.repo.applyWrites#delete",
                "rkey": uri.rkey,
                "collection": "app.bsky.feed.repost",
            })
        else:
            break

    total_deletes = len(deletes)
    if total_deletes > 0:
        for i in range(0, total_deletes, 200):
            cli.com.atproto.repo.apply_writes({"repo": username, "writes": deletes[i:i + 200]})
            

        print(f"{total_deletes} Reposts wurden erfolgreich gelöscht.")
    else:
        print("Keine Reposts zum Löschen gefunden.")

if __name__ == "__main__":
    # ÜBER DIESER ZEILE NICHTS ÄNDERN
    username = "XXX"  # Setze deinen Bluesky-Benutzernamen inkl dem nach dem "." also bspw "testuser.bsky.social"
    password = "XXX"  # Setze dein Bluesky-Passwort oder ein erstelltes App-Passwort: https://bsky.app/settings/app-passwords (letzteres wird empfohlen)
    Tage_behalten = 3 # Tage setzen, vor denen gelöscht werden soll => 3 = alles, was älter ist als 3 Tage wird gelöscht
    # UNTER DIESER ZEILE NICHTS ÄNDERN
    tagedelta = datetime.utcnow() - timedelta(days=Tage_behalten)
    delete_old_skeets(username, password)
    delete_reposts(username, password)
