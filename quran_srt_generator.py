# Prerequisites:
#  Install Python: 3.8+ (3.10+ recommended).
#       python --version 
#  Install with pip:
#       python -m pip install --upgrade pip
#       python -m pip install requests mutagen
#
# How to run:
#   python quran_srt_generator.py --surah 67 --reciter 8 --download-audio
#   python quran_srt_generator.py --surah 1 --reciter 7 --download-audio --translation "T. Usmani"
#   python quran_srt_generator.py --h
#   python quran_srt_generator.py --list-reciters
#   python quran_srt_generator.py --list-translations

# Reciter IDs reference (from Quran.com API):
# | ID | Reciter Name               | Style    |
# | -: | -------------------------- | -------- |
# |  1 | AbdulBaset AbdulSamad      | Mujawwad |
# |  2 | AbdulBaset AbdulSamad      | Murattal |
# |  3 | Abdur-Rahman as-Sudais     | —        |
# |  4 | Abu Bakr al-Shatri         | —        |
# |  5 | Hani ar-Rifai              | —        |
# |  6 | Mahmoud Khalil Al-Husary   | —        |
# |  7 | Mishari Rashid al-`Afasy   | —        |
# |  8 | Mohamed Siddiq al-Minshawi | Mujawwad |
# |  9 | Mohamed Siddiq al-Minshawi | Murattal |
# | 10 | Sa`ud ash-Shuraym          | —        |
# | 11 | Mohamed al-Tablawi         | —        |
# | 12 | Mahmoud Khalil Al-Husary   | Muallim  |

import argparse
import csv
import os
import re
import time
import json
import requests
import tempfile
from io import BytesIO
from mutagen import File as MutagenFile
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======================================================
# CONFIG
# ======================================================
DEFAULT_TIMEOUT = 20

BASE_VERSES_AUDIO = "https://verses.quran.com/"

QURANCOM_API_BASE = "https://api.quran.com/api/v4"
QURANCOM_TRANSLATIONS_API = f"{QURANCOM_API_BASE}/resources/translations"
QURANCOM_VERSES_API = f"{QURANCOM_API_BASE}/verses/by_chapter"
QURANCOM_RECITERS_API = f"{QURANCOM_API_BASE}/resources/recitations"

# ✅ Solution A endpoint (full surah mp3 + timings)
QURANCOM_CHAPTER_AUDIO_API = f"{QURANCOM_API_BASE}/chapter_recitations"

# ✅ Fallback endpoint (verse MP3s)
QURANCOM_VERSE_AUDIO_API = f"{QURANCOM_API_BASE}/recitations"

OUTPUT_ROOT = "output"
DEFAULT_TRANSLATOR_QUERY = "Muhammad Sodiq Muhammad Yusuf (Latin)"

# Simple in-memory caches to avoid repeated lookups when processing many surahs
_reciter_name_cache = {}
_translation_lookup_cache = {}

# Duration Cache (Fallback mode)
CACHE_DIR = "cache"
DURATION_CACHE_FILE = os.path.join(CACHE_DIR, "audio_durations.json")

# ======================================================
# UTILITIES
# ======================================================

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def create_session_with_retries(total_retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retries = Retry(total=total_retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist, allowed_methods=frozenset(['GET', 'POST']))
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def ms_to_srt(ms: int) -> str:
    s = ms // 1000
    ms = ms % 1000
    m = s // 60
    s = s % 60
    h = m // 60
    m = m % 60
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def request_json(url: str, params=None, timeout=DEFAULT_TIMEOUT, session=None):
    sess = session or requests
    r = sess.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def safe_folder_name(name: str) -> str:
    if not name:
        return "Unknown"
    name = name.replace("`", "").replace("’", "").replace("'", "")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "Unknown"

def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return "https:" + url
    return urljoin("https://quran.com", url)

def normalize_verse_audio_url(url_path: str) -> str:
    """
    For verse audio returned as relative paths for verses.quran.com
    """
    if not url_path:
        return ""
    url_path = url_path.strip()
    if url_path.startswith("http"):
        return url_path
    if url_path.startswith("//"):
        return "https:" + url_path
    if url_path.startswith("/"):
        return BASE_VERSES_AUDIO.rstrip("/") + url_path
    return BASE_VERSES_AUDIO + url_path

# ======================================================
# CACHE (Fallback durations)
# ======================================================

def load_duration_cache():
    ensure_dir(CACHE_DIR)
    if not os.path.exists(DURATION_CACHE_FILE):
        return {}
    try:
        with open(DURATION_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_duration_cache(cache: dict):
    ensure_dir(CACHE_DIR)
    tmp_file = DURATION_CACHE_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DURATION_CACHE_FILE)

# ======================================================
# CLEAN TRANSLATION TEXT
# ======================================================

def clean_translation_text(text: str) -> str:
    if not text:
        return ""
    text = strip_html(text)
    # Remove square-bracket footnotes but preserve parenthetical text
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", text)
    text = re.sub(r"\s*\d+\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ======================================================
# RECITERS
# ======================================================

def list_reciters(session=None):
    data = request_json(QURANCOM_RECITERS_API, session=session)
    reciters = data.get("recitations") or []
    print("\n---- RECITERS (QURAN.COM) ----")
    for r in reciters:
        rid = r.get("id")
        name = r.get("reciter_name")
        style = r.get("style") or ""
        print(f"{rid:>3} | {name} {('('+style+')' if style else '')}")

def get_reciter_name(reciter_id: int, session=None) -> str:
    if reciter_id in _reciter_name_cache:
        return _reciter_name_cache[reciter_id]

    data = request_json(QURANCOM_RECITERS_API, session=session)
    reciters = data.get("recitations") or []
    name = f"reciter_{reciter_id}"
    for r in reciters:
        if r.get("id") == reciter_id:
            name = r.get("reciter_name") or name
            break

    _reciter_name_cache[reciter_id] = name
    return name

# ======================================================
# TRANSLATIONS
# ======================================================

def list_translations(session=None):
    data = request_json(QURANCOM_TRANSLATIONS_API, session=session)
    translations = data.get("translations") or []
    print("\n---- TRANSLATIONS (ALL LANGUAGES) ----")
    for t in translations:
        print(f"{t.get('id'):>5} | {t.get('language_name','')} | {t.get('name')}")

def find_translation_id(translator_query: str, session=None):
    key = (translator_query or "").strip().lower()
    if key in _translation_lookup_cache:
        return _translation_lookup_cache[key]

    data = request_json(QURANCOM_TRANSLATIONS_API, session=session)
    translations = data.get("translations") or []
    if not translations:
        raise RuntimeError("No translations returned from Quran.com.")

    q = key

    for t in translations:
        name = (t.get("name") or "").strip().lower()
        if name == q:
            result = (t["id"], t["name"], t.get("language_name", ""))
            _translation_lookup_cache[key] = result
            return result

    for t in translations:
        name = (t.get("name") or "").strip().lower()
        if q in name:
            result = (t["id"], t["name"], t.get("language_name", ""))
            _translation_lookup_cache[key] = result
            return result

    print(f"\n❌ Translation not found for query: {translator_query}")
    print("Try listing translations:")
    print("   python quran_srt_generator.py --list-translations")
    raise RuntimeError("Translation not found.")

# ======================================================
# FETCH TEXTS
# ======================================================

def fetch_arabic_uthmani(surah: int, add_numbers=True, session=None):
    ar_url = f"https://api.alquran.cloud/v1/surah/{surah}/quran-uthmani"
    ar_data = request_json(ar_url, session=session)

    result = []
    for i, a in enumerate(ar_data["data"]["ayahs"], start=1):
        text = a["text"]
        if add_numbers:
            # Arabic-style ayah number (١،٢،٣…)
            arabic_num = "".join(
                chr(0x0660 + int(d)) for d in str(i)
            )
            text = f"{text} ﴿{arabic_num}﴾"
        result.append(text)

    return result


def fetch_translation_qurancom(surah: int, translation_id: int, clean=True, add_numbers=True, session=None):
    params = {"translations": translation_id, "per_page": 300}
    data = request_json(f"{QURANCOM_VERSES_API}/{surah}", params=params, session=session)

    verses = data.get("verses") or []
    if not verses:
        raise RuntimeError(f"No verses returned from Quran.com for surah {surah}")

    result = []
    for i, v in enumerate(verses, start=1):
        tr_list = v.get("translations") or []
        tr_text = tr_list[0].get("text") if tr_list else ""
        text = clean_translation_text(tr_text) if clean else strip_html(tr_text)
        if add_numbers:
            text = f"{i}. {text}"
        result.append(text)
    return result

# ======================================================
# SOLUTION A (Preferred): TRUE TIMINGS FROM CHAPTER AUDIO
# ======================================================

def fetch_chapter_audio_timings(reciter_id: int, surah: int, session=None):
    params = {"segments": True}
    url = f"{QURANCOM_CHAPTER_AUDIO_API}/{reciter_id}/{surah}"
    data = request_json(url, params=params, session=session)

    chapter = data.get("audio_file") or data.get("chapter_recitation") or data
    if not isinstance(chapter, dict):
        raise RuntimeError("Unexpected chapter_recitations response format")

    audio_url = chapter.get("audio_url") or chapter.get("url")
    timestamps = chapter.get("timestamps") or chapter.get("verse_timestamps")

    if not audio_url or not timestamps:
        raise RuntimeError("No chapter audio timestamps available for this reciter")

    audio_url = normalize_url(audio_url)

    timings = []
    for t in timestamps:
        verse_key = t.get("verse_key") or t.get("verse") or ""
        start_ms = t.get("timestamp_from") or t.get("start_ms") or t.get("start") or 0
        end_ms = t.get("timestamp_to") or t.get("end_ms") or t.get("end") or 0
        timings.append({"verse_key": verse_key, "from": int(start_ms), "to": int(end_ms)})

    timings.sort(key=lambda x: x["from"])
    return audio_url, timings

# ======================================================
# FALLBACK MODE: PER-VERSE MP3 DURATIONS + CACHING
# ======================================================

def fetch_audio_files(reciter_id: int, surah: int, session=None):
    url = f"{QURANCOM_VERSE_AUDIO_API}/{reciter_id}/by_chapter/{surah}"
    data = request_json(url, params={"per_page": 500}, session=session)

    audio_files = data.get("audio_files") or []
    if not audio_files:
        raise RuntimeError(f"No audio_files returned for surah {surah}, reciter {reciter_id}")
    return audio_files

def compute_timings_from_audio(audio_files, session=None, duration_cache=None):
    timings = []
    cumulative_ms = 0
    sess = session or requests
    duration_cache = duration_cache or {}

    for idx, af in enumerate(audio_files, start=1):
        url_path = af.get("url")
        if not url_path:
            raise RuntimeError(f"Missing audio URL for verse {idx}")

        full_url = normalize_verse_audio_url(url_path)

        if full_url in duration_cache:
            duration_ms = duration_cache[full_url]
        else:
            # Stream to temporary file to avoid keeping entire file in memory
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                r = sess.get(full_url, timeout=DEFAULT_TIMEOUT, stream=True)
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        tmp.write(chunk)

            audio = MutagenFile(tmp_path)
            if not audio or not hasattr(audio.info, "length"):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                raise RuntimeError(f"Cannot determine duration for verse {idx} ({full_url})")
            duration_ms = int(audio.info.length * 1000)
            duration_cache[full_url] = duration_ms
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        start_ms = cumulative_ms
        end_ms = cumulative_ms + duration_ms
        timings.append({"verse_key": af.get("verse_key", ""), "from": start_ms, "to": end_ms})
        cumulative_ms = end_ms

    return timings

# ======================================================
# OUTPUT
# ======================================================

def build_output_paths(reciter_name: str, translation_name: str):
    rec_folder = safe_folder_name(reciter_name)
    tr_folder = safe_folder_name(translation_name)

    base = os.path.join(OUTPUT_ROOT, rec_folder, tr_folder)
    csv_dir = os.path.join(base, "csv")
    arabic_srt_dir = os.path.join(base, "srt", "arabic")
    tr_srt_dir = os.path.join(base, "srt", "translation")
    # Place audio folder at the reciter level so it's shared across translations
    audio_dir = os.path.join(OUTPUT_ROOT, rec_folder, "audio")

    return base, csv_dir, arabic_srt_dir, tr_srt_dir, audio_dir

def write_csv(csv_dir: str, surah: int, arabic_texts, translated_texts):
    ensure_dir(csv_dir)
    out_path = os.path.join(csv_dir, f"{surah}.csv")

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Ayah", "Arabic", "Translation"])
        for i in range(min(len(arabic_texts), len(translated_texts))):
            writer.writerow([f"{surah}:{i+1}", arabic_texts[i], translated_texts[i]])

    return out_path

def write_srt(output_dir: str, file_name: str, timings, texts, bom: bool = False):
    """Write an SRT file. If `bom` is True the file will be written with a UTF-8 BOM (`utf-8-sig`).

    By default (bom=False) files are written as UTF-8 without BOM.
    """
    ensure_dir(output_dir)
    out_path = os.path.join(output_dir, file_name)

    encoding = "utf-8-sig" if bom else "utf-8"
    with open(out_path, "w", encoding=encoding) as f:
        for i, t in enumerate(timings):
            start = ms_to_srt(t["from"])
            end = ms_to_srt(t["to"])
            line = texts[i] if i < len(texts) else ""
            f.write(f"{i+1}\n{start} --> {end}\n{line}\n\n")

    return out_path

def download_file(url: str, out_path: str, session=None):
    ensure_dir(os.path.dirname(out_path))
    sess = session or requests
    r = sess.get(url, timeout=DEFAULT_TIMEOUT, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 128):
            if chunk:
                f.write(chunk)

# ======================================================
# MAIN PROCESSING
# ======================================================

def process_surah(surah: int, reciter_id: int, translator_query: str,
                 clean_translation=True, add_numbers=True, download_audio=False, session=None):
    session = session or requests.Session()

    reciter_name = get_reciter_name(reciter_id, session=session)
    translation_id, translation_name, translation_lang = find_translation_id(translator_query, session=session)

    base_dir, csv_dir, arabic_srt_dir, tr_srt_dir, audio_dir = build_output_paths(reciter_name, translation_name)

    print(f"\n📥 Processing Surah {surah}")
    print(f"🎧 Reciter: {reciter_name} (id={reciter_id})")
    print(f"🌍 Translation: {translation_name} (id={translation_id}) [{translation_lang}]")
    print(f"📂 Output folder: {base_dir}")

    arabic_texts = fetch_arabic_uthmani(
    surah,
    add_numbers=add_numbers,
    session=session
    )
    tr_texts = fetch_translation_qurancom(
        surah,
        translation_id,
        clean=clean_translation,
        add_numbers=add_numbers,
        session=session
    )

    # ✅ Try Solution A first
    audio_url = None
    timings = None

    try:
        audio_url, timings = fetch_chapter_audio_timings(reciter_id, surah, session=session)
        print("✅ Using Solution A: true timestamps from chapter_recitations (perfect sync).")
    except Exception as e:
        print(f"⚠️ Solution A not available for this reciter/surah → Falling back. Reason: {e}")
        # Fallback mode with caching
        duration_cache = load_duration_cache()
        audio_files = fetch_audio_files(reciter_id, surah, session=session)
        timings = compute_timings_from_audio(audio_files, session=session, duration_cache=duration_cache)
        save_duration_cache(duration_cache)
        print("✅ Using fallback: per-verse MP3 durations (may drift on full MP3).")

    min_len = min(len(timings), len(arabic_texts), len(tr_texts))
    timings = timings[:min_len]
    arabic_texts = arabic_texts[:min_len]
    tr_texts = tr_texts[:min_len]

    csv_path = write_csv(csv_dir, surah, arabic_texts, tr_texts)
    ar_srt_path = write_srt(arabic_srt_dir, f"{surah}_arabic.srt", timings, arabic_texts, bom=False)
    # Ensure translation SRT is saved explicitly without BOM
    tr_srt_path = write_srt(tr_srt_dir, f"{surah}_translation.srt", timings, tr_texts, bom=False)

    # Ensure audio directory exists for any audio downloads
    ensure_dir(audio_dir)

    print(f"✅ CSV: {csv_path}")
    print(f"✅ Arabic SRT: {ar_srt_path}")
    print(f"✅ Translation SRT: {tr_srt_path}")
    print(f"✅ Total ayahs: {min_len}")

    if audio_url:
        print(f"🎵 Full Surah Audio: {audio_url}")
        if download_audio:
            audio_path = os.path.join(audio_dir, f"{surah:03}.mp3")
            if os.path.exists(audio_path):
                print(f"ℹ️ Full surah MP3 already exists: {audio_path}")
            else:
                print(f"⬇️ Downloading full surah MP3 to: {audio_path}")
                download_file(audio_url, audio_path, session=session)
                print("✅ Audio downloaded.")
    else:
        # Fallback: optionally save per-verse MP3s into the audio folder
        if download_audio:
            print(f"⬇️ Downloading per-verse MP3s to: {audio_dir}")
            # audio_files may be available from fallback; fetch if not
            if 'audio_files' not in locals():
                try:
                    audio_files = fetch_audio_files(reciter_id, surah, session=session)
                except Exception as e:
                    print(f"⚠️ Could not fetch per-verse audio files: {e}")
                    audio_files = []

            for idx, af in enumerate(audio_files, start=1):
                url_path = af.get('url')
                if not url_path:
                    print(f"⚠️ Missing URL for verse {idx}, skipping")
                    continue
                full_url = normalize_verse_audio_url(url_path)
                out_path = os.path.join(audio_dir, f"{surah:03}_{idx:03}.mp3")
                if os.path.exists(out_path):
                    print(f"ℹ️ Verse {idx} already exists, skipping: {out_path}")
                    continue
                try:
                    download_file(full_url, out_path, session=session)
                except Exception as e:
                    print(f"⚠️ Failed to download verse {idx}: {e}")
            print("✅ Per-verse audio download finished.")

# ======================================================
# CLI
# ======================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate Quran SRT + CSV using Solution A (true timestamps) with fallback to per-verse durations."
    )
    parser.add_argument("--surah", type=int, help="Surah number (1-114)")
    parser.add_argument("--reciter", type=int, default=7, help="Reciter ID (default: 7)")
    parser.add_argument("--translation", type=str, default=DEFAULT_TRANSLATOR_QUERY,
                        help=f"Translator name query (default: {DEFAULT_TRANSLATOR_QUERY})")
    parser.add_argument("--all", action="store_true", help="Process all surahs")
    parser.add_argument("--no-clean", action="store_true", help="Do NOT clean translation text")
    parser.add_argument("--no-numbers", action="store_true", help="Do NOT add numbering to translation lines")
    parser.add_argument("--list-reciters", action="store_true", help="List all reciters and exit")
    parser.add_argument("--list-translations", action="store_true", help="List all translations and exit")
    parser.add_argument("--download-audio", action="store_true", help="Download full surah MP3 when Solution A is used")

    args = parser.parse_args()
    session = create_session_with_retries()

    if args.list_reciters:
        list_reciters(session=session)
        return

    if args.list_translations:
        list_translations(session=session)
        return

    clean_translation = not args.no_clean
    add_numbers = not args.no_numbers

    if args.all:
        for s in range(1, 115):
            try:
                process_surah(
                    s,
                    args.reciter,
                    args.translation,
                    clean_translation=clean_translation,
                    add_numbers=add_numbers,
                    download_audio=args.download_audio,
                    session=session
                )
            except Exception as e:
                print(f"❌ Surah {s} failed: {e}")
            time.sleep(0.1)
    else:
        if not args.surah:
            parser.error("You must provide --surah unless using --all")
        process_surah(
            args.surah,
            args.reciter,
            args.translation,
            clean_translation=clean_translation,
            add_numbers=add_numbers,
            download_audio=args.download_audio,
            session=session
        )

if __name__ == "__main__":
    main()
