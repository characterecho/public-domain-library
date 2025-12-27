#!/usr/bin/env python3
"""
Lightweight validator tuned to this repo's JSON shapes:
- publications/*/manifest.json
- publications/*/segments/*/dialogues.json
- publications/recent.json

Run: python tools/validate_data.py
"""

import json
import os
import sys

# utility helpers
def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_publication_manifest(path):
    return os.path.basename(path) == "manifest.json" and os.path.sep + "publications" + os.path.sep in path

def is_dialogues(path):
    return os.path.basename(path) == "dialogues.json" and os.path.sep + "segments" + os.path.sep in path

def is_recent(path):
    # handle both ./publications/recent.json and publications/recent.json
    return os.path.normpath(path).endswith(os.path.join('publications', 'recent.json'))

def get_identifier_from(obj):
    # accept multiple possible identifier keys
    for k in ("identifier", "id", "publication_identifier"):
        if isinstance(obj, dict) and k in obj:
            return obj.get(k)
    return None

def get_author_from(obj):
    for k in ("author", "author_name", "author_names"):
        if isinstance(obj, dict) and k in obj:
            return obj.get(k)
    return None

errors = []

print("🔍 Repo-shaped validator starting...")

for root, dirs, files in os.walk(".", topdown=True):
    # skip typical vendored/hidden dirs
    skip_dirs = {".git", ".github", "node_modules", "__pycache__"}
    dirs[:] = [d for d in dirs if d not in skip_dirs]

    for fname in files:
        if not fname.endswith(".json"):
            continue
        # skip package metadata or intentionally ignored names
        if fname == "meta.json" or fname.startswith("package"):
            continue

        path = os.path.join(root, fname)
        try:
            data = read_json(path)
        except Exception as e:
            errors.append(f"🔥 {path}: JSON parse error: {e}")
            continue

        # manifest.json validation
        if is_publication_manifest(path):
            # required keys in manifest shape
            required = ["identifier", "title"]
            for r in required:
                if r not in data:
                    errors.append(f"❌ {path}: Missing required manifest field '{r}'")

            # check directory (parent) name matches identifier
            parent_dir = os.path.basename(os.path.dirname(path))
            identifier = get_identifier_from(data)
            if identifier is not None and str(parent_dir) != str(identifier):
                errors.append(f"⚠️ {path}: Parent dir '{parent_dir}' != identifier '{identifier}'")
            elif identifier is None:
                errors.append(f"❌ {path}: manifest missing identifier field")

        # dialogues validation (array of objects)
        elif is_dialogues(path):
            if not isinstance(data, list):
                errors.append(f"❌ {path}: dialogues file should be a JSON array")
            else:
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        errors.append(f"❌ {path}[{i}]: dialogue entry not an object")
                        continue
                    for rf in ("character_identifier", "ordinal", "text"):
                        if rf not in item:
                            errors.append(f"❌ {path}[{i}]: Missing required dialogue field '{rf}'")

        # recent.json validation (array of publication entries)
        elif is_recent(path):
            if not isinstance(data, list):
                errors.append(f"❌ {path}: expected array of recent items")
            else:
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        errors.append(f"❌ {path}[{i}]: recent entry not an object")
                        continue
                    if get_identifier_from(item) is None:
                        errors.append(f"❌ {path}[{i}]: missing publication identifier (publication_identifier/identifier/id)")
                    if get_author_from(item) is None:
                        errors.append(f"❌ {path}[{i}]: missing author field (author_names/author)")

        # generic publication top-level JSON in publications/<id>/*.json (if any)
        elif os.path.sep + "publications" + os.path.sep in path:
            # If there are JSON files directly inside a per-publication dir besides manifest/segments,
            # ensure they contain an identifier or are allowed shapes. For now check identifier presence.
            if isinstance(data, dict):
                if get_identifier_from(data) is None:
                    # allow files whose name is not manifest.json (e.g., other metadata) but warn
                    errors.append(f"⚠️ {path}: expected an identifier key (identifier/id/publication_identifier)")

# Finish
if errors:
    print(f"\nFound {len(errors)} issues:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("✅ All validations passed.")
    sys.exit(0)

