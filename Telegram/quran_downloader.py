# This script is an automated Python tool that downloads all 114 Surahs of the Quran from QuranicAudio
# and updates their metadata with multilingual support and cover art.
# Install required packages:
#       pip install requests tqdm mutagen
# Usage examples:
#       python quran_downloader.py --reciters
# Download AND update metadata automatically (default behavior)
#       python quran_downloader.py --reciter_name "Mishari Rashid al-`Afasy"
#       python quran_downloader.py --update_metadata --folder "Maher_al-Muaiqly"


import os
import argparse
import requests
from urllib.parse import quote
from tqdm import tqdm
import unicodedata
import difflib
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TPE2, TRCK, APIC, ID3NoHeaderError

# -------------------- CONSTANTS --------------------
QA_API = "https://quranicaudio.com/api"
QA_DOWNLOAD = "https://download.quranicaudio.com/quran/"
TOTAL_SURAHS = 114
COVER_IMAGE = "quran.png"  # Place your image in script folder

# -------------------- SURAH NAMES --------------------
SURAH_NAMES_UZ = [
    "Fotiha","Baqara","Oli Imron","Niso","Moida","An'om","A'rof","Anfol","Tavba",
    "Yunus","Hud","Yusuf","Ra'd","Ibrohim","Hijr","Nahl","Isro","Kahf","Maryam",
    "Toho","Anbiyo","Haj","Mo'minun","Nur","Furqon","Shuaro","Naml","Qasos",
    "Ankabut","Rum","Luqmon","Sajda","Ahzob","Saba'","Fotir","Yosin","Soffat",
    "Sod","Zumar","G'ofir","Fussilat","Shuro","Zuxruf","Duxon","Josiya","Ahqof",
    "Muhammad","Fath","Hujurot","Qof","Zoriyot","Tur","Najm","Qamar","Rahmon",
    "Voqi'a","Hadid","Mujodala","Hashr","Mumtahana","Soff","Juma","Munofiqun",
    "Tag'obun","Taloq","Tahrim","Mulk","Qalam","Haaqqa","Ma'orij","Nuh","Jin",
    "Muzzammil","Muddassir","Qiyomat","Inson","Mursalot","Naba'","Nozi'ot",
    "Abasa","Takvir","Infitor","Mutoffifun","Inshiqoq","Buruj","Toriq","A'lo",
    "G'oshiya","Fajr","Balad","Shams","Layl","Zuho","Sharh","Tiyn","Alaq","Qadr",
    "Bayyina","Zalzala","Odiyot","Qori'a","Takosur","Asr","Humaza","Fil","Quraysh",
    "Mo'un","Kavsar","Kofirun","Nasr","Masad","Ixlos","Falaq","Nos"
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
    'TOFN', 'TORY', 'TOPE', 'TOWN', 'TPUB', 'WXXX', 'WOAR', 'WOAS', 'WORS',
    'WPAY', 'WPUB', 'TENC', 'TSSE', 'TPRO', 'TSRC', 'PRIV',
]

# -------------------- LIST RECITERS --------------------
def list_reciters():
    """Display all available reciters from QuranicAudio API."""
    response = requests.get(f"{QA_API}/qaris", timeout=15)
    response.raise_for_status()
    print("\nAvailable QuranicAudio Reciters:\n")
    for r in response.json():
        print(f"- {r['name']}")
    print()

# -------------------- GET RECITER BY NAME --------------------
def get_reciter_by_name(reciter_name):
    """
    Find reciter information by name.
    
    Args:
        reciter_name: Name of the reciter to search for
        
    Returns:
        Tuple of (reciter_name, relative_path)
    """
    response = requests.get(f"{QA_API}/qaris", timeout=15)
    response.raise_for_status()

    def _normalize(s):
        if not s:
            return ""
        s = s.strip().lower()
        # Normalize common quote/apostrophe variants to a simple apostrophe
        for ch in ("`", "´", "’", "‘", "ʻ", "ʼ", "ʿ"):
            s = s.replace(ch, "'")
        # Remove diacritics
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        # Remove remaining punctuation except spaces and alphanumerics
        s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())
        s = " ".join(s.split())
        return s

    items = []
    norm_map = {}
    for r in response.json():
        name = r.get("name", "")
        rel = r.get("relative_path")
        n = _normalize(name)
        items.append((name, rel, n))
        norm_map[n] = (name, rel)

    target = _normalize(reciter_name)

    # Exact normalized match
    if target in norm_map:
        name, rel = norm_map[target]
        if not rel:
            raise ValueError(f"Reciter '{name}' has no downloadable audio.")
        return name, rel

    # Fuzzy match: try to suggest/auto-select closest reciter
    normalized_keys = [n for (_, _, n) in items]
    close = difflib.get_close_matches(target, normalized_keys, n=1, cutoff=0.6)
    if close:
        matched_norm = close[0]
        matched_name, matched_rel = norm_map[matched_norm]
        if not matched_rel:
            raise ValueError(f"Reciter '{matched_name}' has no downloadable audio.")
        print(f"Using closest match for reciter: '{matched_name}' (requested: '{reciter_name}')")
        return matched_name, matched_rel

    # If nothing found, prepare helpful error with suggestions
    suggestions = difflib.get_close_matches(target, normalized_keys, n=5, cutoff=0.4)
    suggestion_names = [norm_map[s][0] for s in suggestions]
    suggestion_text = "\n".join(f"- {n}" for n in suggestion_names) if suggestion_names else ""

    raise ValueError(
        f"Reciter '{reciter_name}' not found.\n"
        f"Run: python quran_downloader.py --reciters\n"
        + (f"\nDid you mean:\n{suggestion_text}\n" if suggestion_text else "")
    )

# -------------------- MP3 TAGGING (SIMPLE) --------------------
def tag_mp3_simple(file_path, surah_no, reciter):
    """
    Add simple metadata tags during download.
    
    Args:
        file_path: Path to the MP3 file
        surah_no: Surah number (1-114)
        reciter: Name of the reciter
    """
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
    
    # Add cover image if available
    if os.path.exists(COVER_IMAGE):
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

    audio.save()

# -------------------- DOWNLOAD --------------------
def download_quran(reciter_name, relative_path, auto_update_metadata=True):
    """
    Download all 114 Surahs for a given reciter.
    
    Args:
        reciter_name: Name of the reciter
        relative_path: Relative path for downloads from QuranicAudio
        auto_update_metadata: Automatically update metadata after download
    """
    folder = reciter_name.replace(" ", "_")
    os.makedirs(folder, exist_ok=True)
    base_url = QA_DOWNLOAD + quote(relative_path)

    print(f"\nDownloading Quroni Karim")
    print(f"Reciter: {reciter_name}")
    print(f"Folder : {folder}\n")

    for i in tqdm(range(1, TOTAL_SURAHS + 1), desc="Downloading"):
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
            tag_mp3_simple(file_path, i, reciter_name)
        else:
            print(f"Failed: {file_name}")

    print(f"\n✅ Download completed! Files saved in: {folder}")
    
    # Automatically update metadata if enabled
    if auto_update_metadata:
        print("\n" + "="*60)
        print("Starting automatic metadata update...")
        print("="*60)
        try:
            update_metadata(folder, remove_comments=True, remove_personal_tags=True)
        except Exception as e:
            print(f"\n⚠️  Metadata update failed: {e}")
            print(f"💡 You can manually update metadata later with:")
            print(f"   python quran_downloader.py --update_metadata --folder \"{folder}\"")
    else:
        print(f"💡 To update metadata with multilingual support, run:")
        print(f"   python quran_downloader.py --update_metadata --folder \"{folder}\"")

# -------------------- METADATA UPDATE --------------------
def update_metadata(folder, remove_comments=True, remove_personal_tags=True):
    """
    Update metadata with multilingual support and remove personal information.
    
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
            audio.tags.delall("COMM")

        # Remove tags that may contain personal information
        if remove_personal_tags:
            for tag in PERSONAL_INFO_TAGS:
                try:
                    audio.tags.delall(tag)
                except KeyError:
                    pass

        # Add clean multilingual metadata
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
        description="Quran Manager: Download and manage Quran MP3 files with metadata"
    )
    
    # Download options
    parser.add_argument("--reciters", action="store_true", 
                       help="List all available reciters")
    parser.add_argument("--reciter_name", 
                       help="Download Quran by reciter name (e.g. 'Maher al-Muaiqly')")
    parser.add_argument("--skip-metadata-update", action="store_true",
                       help="Skip automatic metadata update after download")
    
    # Metadata update options
    parser.add_argument("--update_metadata", action="store_true",
                       help="Update metadata for existing MP3 files")
    parser.add_argument("--folder", 
                       help="Folder containing MP3 files to update")
    parser.add_argument("--keep_comments", action="store_true",
                       help="Keep comment tags (by default they are removed)")
    parser.add_argument("--keep_personal_tags", action="store_true",
                       help="Keep personal information tags (by default they are removed)")

    args = parser.parse_args()

    # List reciters
    if args.reciters:
        list_reciters()
        return

    # Download Quran
    if args.reciter_name:
        name, path = get_reciter_by_name(args.reciter_name)
        download_quran(name, path, auto_update_metadata=not args.skip_metadata_update)
        return

    # Update metadata
    if args.update_metadata:
        if not args.folder:
            parser.error("--update_metadata requires --folder")
        update_metadata(
            args.folder,
            remove_comments=not args.keep_comments,
            remove_personal_tags=not args.keep_personal_tags
        )
        return

    parser.print_help()

if __name__ == "__main__":
    main()
