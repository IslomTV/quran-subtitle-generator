# This script is an automated Python tool that downloads all 114 Surahs of the Quran from QuranicAudio.
# Install required packages:
#       pip install requests tqdm mutagen
# Usage examples:
#       python quran_downloader.py --reciters
#       python quran_downloader.py --reciter_name "Maher al-Muaiqly"
# Abdullah Matroud, 

import os
import argparse
import requests
from urllib.parse import quote
from tqdm import tqdm
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TRCK, APIC

# -------------------- CONSTANTS --------------------
QA_API = "https://quranicaudio.com/api"
QA_DOWNLOAD = "https://download.quranicaudio.com/quran/"
TOTAL_SURAHS = 114
COVER_IMAGE = "quran.png"  # Place your image in script folder

# -------------------- SURAH NAMES (UZBEK LATIN) --------------------
SURAH_NAMES_UZ = [
    "Fotiha","Baqara","Oli Imron","Niso","Moida","Anʼom","Aʼrof","Anfol","Tavba",
    "Yunus","Hud","Yusuf","Raʼd","Ibrohim","Hijr","Nahl","Isro","Kahf","Maryam",
    "Toho","Anbiyo","Haj","Moʼminun","Nur","Furqon","Shuaro","Naml","Qasos",
    "Ankabut","Rum","Luqmon","Sajda","Ahzob","Sabaʼ","Fotir","Yosin","Soffat",
    "Sod","Zumar","Gʼofir","Fussilat","Shuro","Zuxruf","Duxon","Josiya","Ahqof",
    "Muhammad","Fath","Hujurot","Qof","Zoriyot","Tur","Najm","Qamar","Rahmon",
    "Voqiʼa","Hadid","Mujodala","Hashr","Mumtahana","Soff","Juma","Munofiqun",
    "Tagʼobun","Taloq","Tahrim","Mulk","Qalam","Haaqqa","Maʼorij","Nuh","Jin",
    "Muzzammil","Muddassir","Qiyomat","Inson","Mursalot","Nabaʼ","Noziʼot",
    "Abasa","Takvir","Infitor","Mutoffifun","Inshiqoq","Buruj","Toriq","Aʼlo",
    "Gʼoshiya","Fajr","Balad","Shams","Layl","Zuho","Sharh","Tiyn","Alaq","Qadr",
    "Bayyina","Zalzala","Odiyot","Qoriʼa","Takosur","Asr","Humaza","Fil","Quraysh",
    "Moʼun","Kavsar","Kofirun","Nasr","Masad","Ixlos","Falaq","Nos"
]

# -------------------- LIST RECITERS --------------------
def list_reciters():
    response = requests.get(f"{QA_API}/qaris", timeout=15)
    response.raise_for_status()
    print("\nAvailable QuranicAudio Reciters:\n")
    for r in response.json():
        print(f"- {r['name']}")
    print()

# -------------------- GET RECITER BY NAME --------------------
def get_reciter_by_name(reciter_name):
    response = requests.get(f"{QA_API}/qaris", timeout=15)
    response.raise_for_status()

    for r in response.json():
        if r["name"].strip().lower() == reciter_name.strip().lower():
            if not r.get("relative_path"):
                raise ValueError(f"Reciter '{r['name']}' has no downloadable audio.")
            return r["name"], r["relative_path"]

    raise ValueError(
        f"Reciter '{reciter_name}' not found.\n"
        f"Run: python quran_downloader.py --reciters"
    )

# -------------------- MP3 TAGGING --------------------
def tag_mp3(file_path, surah_no, reciter):
    audio = MP3(file_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    # Title / Artist / Album / Track
    title = f"{surah_no:03}. {SURAH_NAMES_UZ[surah_no - 1]} surasi – Quroni Karim"
    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=reciter))
    audio.tags.add(TALB(encoding=3, text="Quroni Karim"))
    audio.tags.add(TRCK(encoding=3, text=f"{surah_no}/114"))

    # Remove all existing cover images first
    audio.tags.delall("APIC")
    
    # Add cover image
    if os.path.exists(COVER_IMAGE):
        with open(COVER_IMAGE, "rb") as img:
            audio.tags.add(
                APIC(
                    encoding=3,         # UTF-8
                    mime="image/png",   # image type
                    type=3,             # Cover (front)
                    desc="Cover",
                    data=img.read()
                )
            )

    audio.save()

# -------------------- DOWNLOAD --------------------
def download_quran(reciter_name, relative_path):
    folder = reciter_name.replace(" ", "_")
    os.makedirs(folder, exist_ok=True)
    base_url = QA_DOWNLOAD + quote(relative_path)

    print(f"\nDownloading Quroni Karim")
    print(f"Reciter: {reciter_name}")
    print(f"Folder : {folder}\n")

    for i in tqdm(range(1, TOTAL_SURAHS + 1), desc="Surahlar"):
        file_name = f"{i:03}.mp3"
        file_path = os.path.join(folder, file_name)
        url = base_url + file_name

        if os.path.exists(file_path):
            continue

        r = requests.get(url, stream=True, timeout=20)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            tag_mp3(file_path, i, reciter_name)
        else:
            print(f"Failed: {file_name}")

# -------------------- MAIN --------------------
def main():
    parser = argparse.ArgumentParser(description="Quroni Karim MP3 yuklab olish (QuranicAudio) with cover image")
    parser.add_argument("--reciters", action="store_true", help="List reciters")
    parser.add_argument("--reciter_name", help="Reciter name (e.g. Idrees Abkar)")

    args = parser.parse_args()

    if args.reciters:
        list_reciters()
        return

    if args.reciter_name:
        name, path = get_reciter_by_name(args.reciter_name)
        download_quran(name, path)
        return

    parser.print_help()

if __name__ == "__main__":
    main()