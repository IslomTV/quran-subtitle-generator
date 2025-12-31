# Quran Subtitle Generator

Generate SRT subtitles and CSV exports for Quran recitations using Quran.com timings (preferred) or per-verse MP3 durations (fallback).

## Features

- Create SRT files for Arabic text and translations.
- Export CSV with ayah, Arabic and translation columns.
- Use Quran.com chapter timings when available for perfect sync.
- Fallback to per-verse MP3 durations with caching when true timings are unavailable.
- Optionally download full-surah or per-verse audio files.

## Prerequisites

- Python 3.8+ (3.10+ recommended)
- pip

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install requests mutagen
```

## Usage

Basic example (generate for a single surah):

```bash
python quran_srt_generator.py --surah 1 --reciter 7 --download-audio
```

With a different translation:

```bash
python quran_srt_generator.py --surah 1 --reciter 7 --download-audio --translation "T. Usmani"
```

List helpers:

```bash
python quran_srt_generator.py --list-reciters
python quran_srt_generator.py --list-translations
python quran_srt_generator.py --h
```

Process all surahs:

```bash
python quran_srt_generator.py --all --reciter 7 --translation "T. Usmani"
```

## Output

By default files are written to the `output/` folder, organized by reciter and translation:

- `output/<reciter>/<translation>/srt/arabic/<surah>_arabic.srt`
- `output/<reciter>/<translation>/srt/translation/<surah>_translation.srt`
- `output/<reciter>/<translation>/csv/<surah>.csv`
- Shared audio files (if downloaded): `output/<reciter>/audio/` (full surah and per-verse MP3s)

## Notes

- The script prefers Quran.com chapter recitation timings (Solution A). If unavailable it falls back to downloading per-verse audio to compute durations — this can be slower and may drift slightly when combining timings into a full MP3.
- A small cache is used to store per-verse durations in `cache/audio_durations.json` to avoid re-downloading audio repeatedly.

## Files

- `quran_srt_generator.py` — main script
- `requirements.txt` — minimal dependencies (`requests`, `mutagen`)
- `.gitignore` — ignores `output/`, `cache/`, and Python artifacts

## Contributing

Contributions and improvements welcome — open an issue or a PR.

## License

Add a license file if you want to set usage terms (e.g., MIT).