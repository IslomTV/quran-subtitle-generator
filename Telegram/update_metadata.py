# python update_metadata.py --folder Yasser_Al-Dosari

import os
import argparse
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, TIT2, TALB, TPE1, TRCK, APIC, ID3NoHeaderError
)
from tqdm import tqdm

# -------------------- CONSTANTS --------------------
TOTAL_SURAHS = 114
COVER_IMAGE = "quran.png"

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

# -------------------- METADATA UPDATE --------------------
def update_metadata(folder):
    if not os.path.exists(COVER_IMAGE):
        raise FileNotFoundError("Cover image 'quran.png' not found.")

    if not os.path.isdir(folder):
        raise NotADirectoryError("Provided folder does not exist.")

    # Reciter name from folder
    reciter_name = os.path.basename(folder).replace("_", " ").strip()

    mp3_files = sorted(
        f for f in os.listdir(folder) if f.lower().endswith(".mp3")
    )

    print(f"\nUpdating metadata")
    print(f"Folder : {folder}")
    print(f"Reciter: {reciter_name}\n")

    for index, file_name in enumerate(tqdm(mp3_files, desc="Processing"), start=1):
        file_path = os.path.join(folder, file_name)

        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        # Remove old cover images (important for Telegram)
        audio.tags.delall("APIC")

        title = f"{index:03}. {SURAH_NAMES_UZ[index - 1]} surasi – Quroni Karim"

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=reciter_name))
        audio.tags.add(TALB(encoding=3, text="Quroni Karim"))
        audio.tags.add(TRCK(encoding=3, text=f"{index}/{TOTAL_SURAHS}"))

        with open(COVER_IMAGE, "rb") as img:
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime="image/png",
                    type=3,      # Front cover (Telegram requirement)
                    desc="Cover",
                    data=img.read()
                )
            )

        # Force ID3v2.3 for max compatibility
        audio.save(v2_version=3)

    print("\n✅ Metadata update completed (Telegram optimized).")

# -------------------- MAIN --------------------
def main():
    parser = argparse.ArgumentParser(
        description="Update MP3 metadata + embed PNG cover (reciter from folder name)"
    )
    parser.add_argument("--folder", required=True, help="Folder with MP3 files")

    args = parser.parse_args()
    update_metadata(args.folder)

if __name__ == "__main__":
    main()
