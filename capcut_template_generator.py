# py capcut_template_generator.py   


import os
import shutil
import re
import json
import uuid
import copy
import argparse

# === CONFIG ===
TEMPLATE_DIR = r"C:\Users\davro\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
NAMES_FILE = r"quran_sura_names_uzbek.txt"

# SRT source directories (Arabic and translation)
ARAB_SRT_DIR = r"C:\Quron\Mishari_Rashid_al_Afasy\Muhammad_Sodiq_Muhammad_Yusuf_Latin\srt\arabic"
TRANSL_SRT_DIR = r"C:\Quron\Mishari_Rashid_al_Afasy\Muhammad_Sodiq_Muhammad_Yusuf_Latin\srt\translation"

# Name of ONE existing template folder to duplicate. If this folder does not exist
# the script will try to auto-detect a suitable folder inside `TEMPLATE_DIR`.
BASE_TEMPLATE_FOLDER = "BASE_TEMPLATE"  # change this to your real folder name
# If True, keep leading numbering from the names file (e.g. "1. Fatiha").
# If False, numbers will be removed (default legacy behaviour).
PRESERVE_NUMBERS = True

# =================

def clean_name(name):
    """Normalize name: optionally remove leading numbering and strip illegal chars."""
    name = name.strip()
    if not PRESERVE_NUMBERS:
        name = re.sub(r'^\d+\.\s*', '', name)  # remove "1. "
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def main():
    # Normalize the template directory path
    template_dir = os.path.normpath(os.path.expanduser(TEMPLATE_DIR))

    def find_base_template(template_dir, base_folder):
        # If user provided a base folder name, prefer that when it exists
        if base_folder:
            candidate = os.path.join(template_dir, base_folder)
            if os.path.isdir(candidate):
                return candidate

        # Otherwise try to auto-detect a single/first directory inside template_dir
        if not os.path.isdir(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        entries = [d for d in os.listdir(template_dir) if os.path.isdir(os.path.join(template_dir, d))]
        if not entries:
            raise FileNotFoundError(f"No template folders found in: {template_dir}")

        # Prefer a non-placeholder folder; pick the first non-hidden entry
        non_hidden = [d for d in entries if not d.startswith('.') and d.upper() != 'BASE_TEMPLATE']
        chosen = non_hidden[0] if non_hidden else entries[0]
        return os.path.join(template_dir, chosen)

    base_template_path = find_base_template(template_dir, BASE_TEMPLATE_FOLDER)
    print(f"Using base template folder: {os.path.basename(base_template_path)}")

    # Try to detect the original mp3 filename from the base template's draft_content.json
    def find_original_mp3(template_root):
        for root, _, files in os.walk(template_root):
            for fname in files:
                if fname == 'draft_content.json':
                    try:
                        with open(os.path.join(root, fname), 'r', encoding='utf-8') as jf:
                            data = json.load(jf)
                    except Exception:
                        continue

                    # recursive search for first mp3 filename string
                    def search_obj(o):
                        if isinstance(o, str):
                            m = re.search(r'(\d+\.mp3)$', o)
                            if m:
                                return os.path.basename(o)
                            if o.lower().endswith('.mp3'):
                                return os.path.basename(o)
                            return None
                        if isinstance(o, dict):
                            for v in o.values():
                                res = search_obj(v)
                                if res:
                                    return res
                        if isinstance(o, list):
                            for v in o:
                                res = search_obj(v)
                                if res:
                                    return res
                        return None

                    found = search_obj(data)
                    if found:
                        return found
        return None

    original_mp3 = find_original_mp3(base_template_path)
    if original_mp3:
        orig_digits = re.search(r'(\d+)(?=\.mp3$)', original_mp3)
        orig_width = len(orig_digits.group(1)) if orig_digits else 3
    else:
        orig_width = 3

    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        names = [clean_name(line) for line in f if line.strip()]

    for name in names:
        new_project_path = os.path.join(TEMPLATE_DIR, name)

        if os.path.exists(new_project_path):
            print(f"Skipping (already exists): {name}")
            continue

        shutil.copytree(base_template_path, new_project_path)
        print(f"Created template: {name}")

        # (SRT text insertion and audio filename replacement removed)
        # We only copy the base template folder; no modifications to draft_content.json are performed.

    print("\n✅ Done! CapCut projects created successfully.")


# SRT and audio modification helpers removed. This script now only duplicates the base template folders.



if __name__ == "__main__":
    main()
