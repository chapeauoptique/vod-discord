"""
Poste automatiquement les nouvelles vidéos d'une chaîne YouTube
dans un salon Discord via un webhook.

Variables d'environnement (définies dans le workflow GitHub) :
  DISCORD_WEBHOOK : l'URL du webhook Discord (secret)
  YT_CHANNEL_ID   : l'ID de la chaîne YouTube (commence par "UC")
  STATE_FILE      : fichier qui mémorise les vidéos déjà postées
  MESSAGE         : texte du message, avec {titre} et {lien}
"""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
CHANNEL_ID = os.environ["YT_CHANNEL_ID"].strip()
STATE_FILE = os.environ.get("STATE_FILE", "videos_postees.txt")
MESSAGE = os.environ.get("MESSAGE", "🎮 **Nouvelle VOD !** {titre}\n{lien}")
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
        "content": MESSAGE.format(titre=video["titre"], lien=video["lien"]),
        # autorise le ping @everyone s'il est présent dans le message
        "allowed_mentions": {"parse": ["everyone"]},
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

    # Premier lancement : on mémorise les vidéos existantes sans rien poster.
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            f.write("\n".join(v["id"] for v in videos))
        print(f"[{STATE_FILE}] Premier lancement : {len(videos)} vidéos mémorisées, rien posté.")
        return

    with open(STATE_FILE) as f:
        deja_postees = set(f.read().split())

    nouvelles = [v for v in videos if v["id"] not in deja_postees]
    for video in reversed(nouvelles):
        poster_discord(video)
        print(f"[{STATE_FILE}] Postée : {video['titre']}")

    with open(STATE_FILE, "w") as f:
        f.write("\n".join(v["id"] for v in videos))

    if not nouvelles:
        print(f"[{STATE_FILE}] Aucune nouvelle vidéo.")


if __name__ == "__main__":
    main()
