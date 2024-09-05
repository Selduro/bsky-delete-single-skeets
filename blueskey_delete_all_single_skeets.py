import requests
import json
from getpass import getpass
from urllib.parse import urlparse

# token holen
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
        raise Exception("Authentication failed: " + response.text)

# alle skeets holen
def get_all_skeets(auth_token, did):
    url = f"https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor={did}"
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["feed"]
    else:
        raise Exception("Failed to fetch skeets: " + response.text)

# threads filtern
def analyze_skeets(skeets):
    threads = []
    single_skeets = []
    skeet_dict = {skeet['post']['uri']: skeet for skeet in skeets}

    
    thread_uris = set()

    for skeet in skeets:
        if skeet['post']['uri'] in thread_uris:
            continue


        if 'reply' in skeet:
            parent_uri = skeet['reply']['parent']['uri']
            if parent_uri in skeet_dict and skeet_dict[parent_uri]['post']['author']['did'] == skeet['post']['author']['did']:
                thread_uris.add(skeet['post']['uri'])
                thread_uris.add(parent_uri)


        for reply in skeets:
            if 'reply' in reply and reply['reply']['parent']['uri'] == skeet['post']['uri']:
                thread_uris.add(skeet['post']['uri'])
                thread_uris.add(reply['post']['uri'])


    for skeet in skeets:
        if skeet['post']['uri'] in thread_uris:
            threads.append(skeet)
        else:
            single_skeets.append(skeet)

    return threads, single_skeets

# einzelskeets löschen
def delete_single_skeets(auth_token, single_skeets):
    url = "https://bsky.social/xrpc/com.atproto.repo.deleteRecord"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    for skeet in single_skeets:

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


def main():
    username = input("Enter your Bluesky username: ")
    password = getpass("Enter your Bluesky password: ")

    try:
        auth_token, did = get_auth_token(username, password)
        print("Authentication successful.")

        skeets = get_all_skeets(auth_token, did)
        print(f"Fetched {len(skeets)} skeets.")

        threads, single_skeets = analyze_skeets(skeets)
        print(f"Threads found: {len(threads)}")
        print(f"Single Skeets to delete: {len(single_skeets)}")

        if single_skeets:
            delete_single_skeets(auth_token, single_skeets)
            print("Cleanup completed.")
        else:
            print("No single skeets to delete.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
