import subprocess
import json
import os
import re

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLd4gIYSJqNQd8dPPnGst4hSj8_umevXNu"
OUTPUT_DIR = "descriptions_latin"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Uzbek Cyrillic → Latin map
UZ_CYR_TO_LAT = {
    "А":"A","а":"a","Б":"B","б":"b","В":"V","в":"v","Г":"G","г":"g",
    "Д":"D","д":"d","Е":"E","е":"e","Ё":"Yo","ё":"yo","Ж":"J","ж":"j",
    "З":"Z","з":"z","И":"I","и":"i","Й":"Y","й":"y","К":"K","к":"k",
    "Л":"L","л":"l","М":"M","м":"m","Н":"N","н":"n","О":"O","о":"o",
    "П":"P","п":"p","Р":"R","р":"r","С":"S","с":"s","Т":"T","т":"t",
    "У":"U","у":"u","Ф":"F","ф":"f","Х":"X","х":"x","Ц":"Ts","ц":"ts",
    "Ч":"Ch","ч":"ch","Ш":"Sh","ш":"sh","Ъ":"ʼ","ъ":"ʼ","Ь":"",
    "Э":"E","э":"e","Ю":"Yu","ю":"yu","Я":"Ya","я":"ya",
    "Ў":"Oʻ","ў":"oʻ","Қ":"Q","қ":"q","Ғ":"Gʻ","ғ":"gʻ","Ҳ":"H","ҳ":"h"
}

def cyr_to_lat(text):
    return "".join(UZ_CYR_TO_LAT.get(c, c) for c in text)

def sanitize_filename(name):
    name = cyr_to_lat(name)
    return re.sub(r'[\\/*?:"<>|]', "", name)

print("Fetching playlist metadata using yt-dlp...")

cmd = [
    "yt-dlp",
    "--dump-single-json",
    "--flat-playlist",
    PLAYLIST_URL
]

playlist_data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
entries = playlist_data.get("entries", [])

print(f"Found {len(entries)} videos")

for i, entry in enumerate(entries, start=1):
    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
    print(f"[{i}] Processing {video_url}")

    cmd = ["yt-dlp", "-j", video_url]
    video_data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

    title = cyr_to_lat(video_data.get("title", f"video_{entry['id']}"))
    description = cyr_to_lat(video_data.get("description", ""))

    filename = sanitize_filename(f"{i:02d} - {title}")
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(description)

    print(f"    Saved → {filepath}")

print("✅ Done. All descriptions converted to Uzbek Latin.")
