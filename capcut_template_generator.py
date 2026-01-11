# py capcut_template_generator.py   


import os
import shutil
import re
import json
import uuid
import copy
import argparse

# === CONFIG ===
# If TEMPLATE_DIR is None the script attempts to auto-detect the CapCut projects
# location using the %LOCALAPPDATA% environment variable. You can override the
# detected path by passing --template-dir (or -t) on the command line.
TEMPLATE_DIR = None  # e.g. r"C:\Users\<you>\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
NAMES_FILE = r"data/quran_sura_names_uzbek.txt"

# SRT handling removed — this script only duplicates template folders

# Name of ONE existing template folder to duplicate. If this folder does not exist
# the script will try to auto-detect a suitable folder inside `TEMPLATE_DIR`.
BASE_TEMPLATE_FOLDER = "data/BASE_TEMPLATE"  # change this to your real folder name
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
    parser = argparse.ArgumentParser(description="Create CapCut templates from a base project folder.")
    parser.add_argument('-t', '--template-dir', help='Path to CapCut projects directory (overrides auto-detection)')
    args = parser.parse_args()

    def resolve_template_dir(provided):
        # If user explicitly provided a path, validate and use it
        if provided:
            path = os.path.normpath(os.path.expanduser(provided))
            if os.path.isdir(path):
                return path
            raise FileNotFoundError(f"Provided template directory not found: {path}")

        # Try to auto-detect CapCut projects under %LOCALAPPDATA% (Windows)
        localappdata = os.getenv('LOCALAPPDATA')
        if localappdata:
            candidate = os.path.join(localappdata, 'CapCut', 'User Data', 'Projects', 'com.lveditor.draft')
            if os.path.isdir(candidate):
                return os.path.normpath(candidate)
            parent = os.path.join(localappdata, 'CapCut', 'User Data', 'Projects')
            if os.path.isdir(parent):
                entries = [d for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d)) and not d.startswith('.')]
                if entries:
                    return os.path.normpath(os.path.join(parent, entries[0]))

        # Fallback to legacy hardcoded path if present (keeps compatibility)
        legacy = r"C:\Users\davro\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"
        if os.path.isdir(legacy):
            return os.path.normpath(legacy)

        raise FileNotFoundError("Could not locate CapCut template directory. Pass --template-dir or ensure the folder exists under %LOCALAPPDATA%\\CapCut\\User Data\\Projects")

    template_dir = resolve_template_dir(args.template_dir)
    print(f"Using template directory: {template_dir}")

    def find_base_template(template_dir, base_folder):
        # If user provided a base folder name or path, prefer that when it exists.
        if base_folder:
            # Absolute path provided -> use directly if it exists
            if os.path.isabs(base_folder):
                if os.path.isdir(base_folder):
                    return os.path.normpath(base_folder)
            else:
                # First, check relative to the script/project directory (e.g. "data/BASE_TEMPLATE")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                candidate = os.path.normpath(os.path.join(script_dir, base_folder))
                if os.path.isdir(candidate):
                    return candidate

                # Next, check inside the detected template_dir for backward compatibility
                candidate = os.path.join(template_dir, base_folder)
                if os.path.isdir(candidate):
                    return os.path.normpath(candidate)

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

    # Sanity check: ensure we resolved a concrete path
    if not isinstance(template_dir, (str, bytes, os.PathLike)):
        raise TypeError("Resolved template directory is not a valid path")
    if not os.path.isdir(template_dir):
        raise FileNotFoundError(f"Resolved template directory does not exist: {template_dir}")

    for name in names:
        new_project_path = os.path.join(template_dir, name)

        if os.path.exists(new_project_path):
            print(f"Skipping (already exists): {name}")
            continue

        shutil.copytree(base_template_path, new_project_path)
        print(f"Created template: {name}")

        # We only copy the base template folder; no other modifications are performed.

    print("\n✅ Done! CapCut projects created successfully.")


# Audio modification helpers removed. This script now only duplicates the base template folders.



if __name__ == "__main__":
    main()
