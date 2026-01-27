# python update_metadata.py --folder idrees-abkar

import os
import argparse
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, TIT2, TALB, TPE1, TPE2, TRCK, APIC, ID3NoHeaderError,
    COMM, TYER, TCON  # Added for removing comments, year, genre if needed
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

SURAH_NAMES_EN = [
    "Al-Fatihah","Al-Baqarah","Aal-E-Imran","An-Nisa","Al-Ma'idah","Al-An'am",
    "Al-A'raf","Al-Anfal","At-Tawbah","Yunus","Hud","Yusuf","Ar-Ra'd","Ibrahim",
    "Al-Hijr","An-Nahl","Al-Isra","Al-Kahf","Maryam","Ta-Ha","Al-Anbiya","Al-Hajj",
    "Al-Mu'minun","An-Nur","Al-Furqan","Ash-Shu'ara","An-Naml","Al-Qasas",
    "Al-Ankabut","Ar-Rum","Luqman","As-Sajdah","Al-Ahzab","Saba","Fatir","Ya-Sin",
    "As-Saffat","Sad","Az-Zumar","Ghafir","Fussilat","Ash-Shura","Az-Zukhruf",
    "Ad-Dukhan","Al-Jathiyah","Al-Ahqaf","Muhammad","Al-Fath","Al-Hujurat",
    "Qaf","Adh-Dhariyat","At-Tur","An-Najm","Al-Qamar","Ar-Rahman","Al-Waqi'ah",
    "Al-Hadid","Al-Mujadila","Al-Hashr","Al-Mumtahanah","As-Saff","Al-Jumu'ah",
    "Al-Munafiqun","At-Taghabun","At-Talaq","At-Tahrim","Al-Mulk","Al-Qalam",
    "Al-Haqqah","Al-Ma'arij","Nuh","Al-Jinn","Al-Muzzammil","Al-Muddaththir",
    "Al-Qiyamah","Al-Insan","Al-Mursalat","An-Naba","An-Nazi'at","Abasa",
    "At-Takwir","Al-Infitar","Al-Mutaffifin","Al-Inshiqaq","Al-Buruj","At-Tariq",
    "Al-A'la","Al-Ghashiyah","Al-Fajr","Al-Balad","Ash-Shams","Al-Layl",
    "Ad-Duha","Ash-Sharh","At-Tin","Al-Alaq","Al-Qadr","Al-Bayyinah",
    "Az-Zalzalah","Al-Adiyat","Al-Qari'ah","At-Takathur","Al-Asr","Al-Humazah",
    "Al-Fil","Quraysh","Al-Ma'un","Al-Kawthar","Al-Kafirun","An-Nasr",
    "Al-Masad","Al-Ikhlas","Al-Falaq","An-Nas"
]

SURAH_NAMES_AR = [
    "الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف",
    "الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل",
    "الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون","النور","الفرقان",
    "الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب",
    "سبإ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف",
    "الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات",
    "الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر",
    "الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحريم","الملك",
    "القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القيامة","الإنسان",
    "المرسلات","النبأ","النازعات","عبس","التكوير","الإنفطار","المطففين",
    "الإنشقاق","البروج","الطارق","الأعلى","الغاشية","الفجر","البلد","الشمس",
    "الليل","الضحى","الشرح","التين","العلق","القدر","البينة","الزلزلة",
    "العاديات","القارعة","التكاثر","العصر","الهمزة","الفيل","قريش","الماعون",
    "الكوثر","الكافرون","النصر","المسد","الإخلاص","الفلق","الناس"
]

# Tags that may contain personal information
PERSONAL_INFO_TAGS = [
    'TOFN',  # Original filename
    'TORY',  # Original release year
    'TOPE',  # Original artist/performer
    'TOWN',  # File owner/licensee
    'TPUB',  # Publisher
    'WXXX',  # User defined URL link
    'WOAR',  # Official artist/performer webpage
    'WOAS',  # Official audio source webpage
    'WORS',  # Official internet radio station homepage
    'WPAY',  # Payment
    'WPUB',  # Publishers official webpage
    'TENC',  # Encoded by
    'TSSE',  # Software/Hardware and settings used for encoding
    'TPRO',  # Produced notice
    'TSRC',  # ISRC (International Standard Recording Code)
    'PRIV',  # Private frame (may contain owner info)
]

# -------------------- METADATA UPDATE --------------------
def update_metadata(folder, remove_comments=True, remove_personal_tags=True):
    """
    Update metadata and remove personal information from MP3 files.
    
    Args:
        folder: Path to folder containing MP3 files
        remove_comments: Remove comment tags that may contain website/personal info
        remove_personal_tags: Remove tags that may contain owner/computer info
    """
    if not os.path.exists(COVER_IMAGE):
        raise FileNotFoundError("Cover image 'quran.png' not found.")

    if not os.path.isdir(folder):
        raise NotADirectoryError("Provided folder does not exist.")

    reciter_name = os.path.basename(folder).replace("_", " ").strip()

    mp3_files = sorted(
        (f for f in os.listdir(folder) if f.lower().endswith(".mp3")),
        key=lambda x: int(os.path.splitext(x)[0])
    )

    if len(mp3_files) != TOTAL_SURAHS:
        raise ValueError(f"Expected {TOTAL_SURAHS} MP3 files, found {len(mp3_files)}.")

    print(f"\nUpdating metadata and removing personal information")
    print(f"Folder : {folder}")
    print(f"Reciter: {reciter_name}")
    print(f"Remove comments: {remove_comments}")
    print(f"Remove personal tags: {remove_personal_tags}\n")

    for index, file_name in enumerate(tqdm(mp3_files, desc="Processing"), start=1):
        file_path = os.path.join(folder, file_name)

        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        # Clear old standard tags
        for tag in ["TIT2", "TPE1", "TPE2", "TALB", "TRCK", "APIC"]:
            audio.tags.delall(tag)

        # Remove comment tags that may contain personal/source info
        if remove_comments:
            audio.tags.delall("COMM")  # Remove all comment frames

        # Remove tags that may contain personal information
        if remove_personal_tags:
            for tag in PERSONAL_INFO_TAGS:
                try:
                    audio.tags.delall(tag)
                except KeyError:
                    pass  # Tag doesn't exist, skip

        # Add clean metadata
        title = (
            f"{index:03}. {SURAH_NAMES_EN[index-1]} | "
            f"{SURAH_NAMES_UZ[index-1]} surasi | "
            f"{SURAH_NAMES_AR[index-1]}"
        )

        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=reciter_name))
        audio.tags.add(TPE2(encoding=3, text=reciter_name))
        audio.tags.add(TALB(encoding=3, text="The Holy Qur'an | Quroni Karim | القرآن الكريم"))
        audio.tags.add(TRCK(encoding=3, text=f"{index}/{TOTAL_SURAHS}"))

        # Add cover art
        with open(COVER_IMAGE, "rb") as img:
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime="image/png",
                    type=3,
                    desc="Cover",
                    data=img.read()
                )
            )

        # Save with v2.3 tags (most compatible)
        audio.save(v2_version=3)

    print("\n✅ Metadata update completed:")
    print("   - Updated: Title, Artist, Album, Track, Cover Art")
    if remove_comments:
        print("   - Removed: Comment tags (website/source info)")
    if remove_personal_tags:
        print("   - Removed: Personal information tags (owner, encoder, etc.)")

# -------------------- MAIN --------------------
def main():
    parser = argparse.ArgumentParser(
        description="Update MP3 Quran metadata and remove personal information"
    )
    parser.add_argument("--folder", required=True, help="Folder with MP3 files")
    parser.add_argument(
        "--keep-comments", 
        action="store_true", 
        help="Keep comment tags (by default they are removed)"
    )
    parser.add_argument(
        "--keep-personal-tags", 
        action="store_true", 
        help="Keep personal information tags (by default they are removed)"
    )

    args = parser.parse_args()
    
    update_metadata(
        args.folder, 
        remove_comments=not args.keep_comments,
        remove_personal_tags=not args.keep_personal_tags
    )

if __name__ == "__main__":
    main()
