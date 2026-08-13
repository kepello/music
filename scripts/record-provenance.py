#!/usr/bin/env python3
"""
Record where each master came from, so identity survives the file itself.

    ./scripts/record-provenance.py            # report what would change
    ./scripts/record-provenance.py --write    # update provenance.json

Suno stamps a generation id into the WAV's comment tag. That id is the only
thing that identifies a recording independently of its bytes -- the same
generation re-downloaded produces a different file hash and a fresh timestamp,
which is exactly how a duplicate slipped in as a seemingly-new take. It is also
fragile: converting to 44.1kHz for CD Baby strips it, and 43 of Carl's masters
have already lost it.

So the id is copied out of the tags into provenance.json, alongside a content
hash of the master and its audio characteristics. Once recorded it cannot be
lost by a later conversion, and a master whose tag is already gone keeps
whatever was captured the first time.

Fields per song:
  sunoId, sunoCreated   from the master's comment tag, when present
  sha256                content hash of the master file
  audioMd5              hash of the decoded audio -- unchanged by re-tagging or
                        by a sample-rate-preserving remux, so it identifies the
                        recording where sha256 identifies the file
  sampleRate, duration, master (filename)
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent.resolve()
MASTERS = Path("/Users/carl/Music/Masters")
OUT = REPO / "provenance.json"


def ffprobe(path: Path, entries: str):
    return subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True).stdout.strip()


def audio_md5(path: Path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a", "-f", "md5", "-"],
                         capture_output=True, text=True).stdout.strip()
    return out.replace("MD5=", "") or None


def sha256(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def master_for(album: str, song: str):
    for ext in ("wav", "mp3"):
        p = MASTERS / album / f"{song}.{ext}"
        if p.is_file():
            return p
    return None


def describe(path: Path):
    comment = ffprobe(path, "format_tags=comment")
    sid = re.search(r"id=([0-9a-f-]{36})", comment)
    created = re.search(r"created=([0-9T:.-]+Z?)", comment)
    rec = {
        "master": path.name,
        "sha256": sha256(path),
        "audioMd5": audio_md5(path),
        "sampleRate": ffprobe(path, "stream=sample_rate").split("\n")[0] or None,
        "duration": round(float(ffprobe(path, "format=duration") or 0), 2) or None,
    }
    if sid:
        rec["sunoId"] = sid.group(1)
    if created:
        rec["sunoCreated"] = created.group(1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="update provenance.json")
    args = ap.parse_args()

    existing = {}
    if OUT.is_file():
        existing = json.loads(OUT.read_text(encoding="utf-8")).get("songs", {})

    songs, missing, new_ids, kept_ids = {}, [], 0, 0
    for album_dir in sorted(REPO.iterdir()):
        meta_path = album_dir / "ALBUM.json"
        if not (album_dir.is_dir() and meta_path.is_file()):
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for song in meta.get("tracks") or []:
            key = f"{album_dir.name}/{song}"
            path = master_for(album_dir.name, song)
            if not path:
                missing.append(key)
                if key in existing:
                    songs[key] = existing[key]   # keep what we knew
                continue
            rec = describe(path)
            prior = existing.get(key, {})
            # A tag lost to conversion must not erase an id captured earlier.
            for field in ("sunoId", "sunoCreated"):
                if field not in rec and field in prior:
                    rec[field] = prior[field]
                    kept_ids += 1
            if "sunoId" in rec and "sunoId" not in prior:
                new_ids += 1
            songs[key] = rec

    with_id = sum(1 for r in songs.values() if "sunoId" in r)
    print(f"songs: {len(songs)}   with a Suno id: {with_id}   without: {len(songs)-with_id}")
    if new_ids:
        print(f"  newly captured ids: {new_ids}")
    if kept_ids:
        print(f"  ids preserved from a previous run whose tag has since been lost: {kept_ids}")
    if missing:
        print(f"  no master found for: {', '.join(missing)}")

    ids = [r["sunoId"] for r in songs.values() if "sunoId" in r]
    if len(ids) != len(set(ids)):
        seen = {}
        for k, r in songs.items():
            if "sunoId" in r:
                seen.setdefault(r["sunoId"], []).append(k)
        for sid, keys in seen.items():
            if len(keys) > 1:
                print(f"  WARNING: one generation used by several songs: {sid} -> {', '.join(keys)}")

    if not args.write:
        print("\nRe-run with --write to update provenance.json")
        return 0

    OUT.write_text(json.dumps({"songs": songs}, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
