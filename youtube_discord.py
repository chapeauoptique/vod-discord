"""
Poste automatiquement les nouvelles vidéos/VOD d'une chaîne YouTube
dans un salon Discord via un webhook.

Variables d'environnement (configurées dans GitHub, jamais dans le code) :
  DISCORD_WEBHOOK : l'URL du webhook Discord (secret)
  YT_CHANNEL_ID   : l'ID de la chaîne YouTube (commence par "UC")
"""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
CHANNEL_ID = os.environ["YT_CHANNEL_ID"].strip()
STATE_FILE = "videos_postees.txt"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
HEADERS = {"User-Agent": "ChapeauOptique-VOD-Bot/1.0"}


def lire_flux():
    req = urllib.request.Request(FEED_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    videos = []
    for entry in root.findall("atom:entry", NS):
        videos.append({
            "id": entry.find("yt:videoId", NS).text,
            "titre": entry.find("atom:title", NS).text,
            "lien": entry.find("atom:link", NS).attrib["href"],
        })
    return videos  # du plus récent au plus ancien


def poster_discord(video):
    message = {
        "content": f"🎮 **Nouvelle VOD !** {video['titre']}\n{video['lien']}",
    }
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps(message).encode("utf-8"),
        headers={**HEADERS, "Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    videos = lire_flux()

    # Premier lancement : on mémorise les vidéos existantes sans rien poster,
    # pour ne pas spammer le salon avec tout l'historique.
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            f.write("\n".join(v["id"] for v in videos))
        print(f"Premier lancement : {len(videos)} vidéos mémorisées, rien posté.")
        return

    with open(STATE_FILE) as f:
        deja_postees = set(f.read().split())

    nouvelles = [v for v in videos if v["id"] not in deja_postees]
    for video in reversed(nouvelles):  # de la plus ancienne à la plus récente
        poster_discord(video)
        print(f"Postée : {video['titre']}")
        deja_postees.add(video["id"])

    # On garde seulement les IDs encore présents dans le flux (15 dernières vidéos)
    with open(STATE_FILE, "w") as f:
        f.write("\n".join(v["id"] for v in videos))

    if not nouvelles:
        print("Aucune nouvelle vidéo.")


if __name__ == "__main__":
    main()
