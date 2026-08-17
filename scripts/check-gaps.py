#!/usr/bin/env python3
"""
Report what's missing from the music catalog.

Run it any time:      ./scripts/check-gaps.py
Machine-readable:     ./scripts/check-gaps.py --json

Checks, in rough order of how much they matter:

  story/lyrics   a song with no README.md or LYRICS.txt, or one still holding
                 the TODO stub sync-album.sh writes
  audio          a song with no MP3/M4A in the "latest" release (needs `gh`;
                 skipped with a note when unavailable)
  sequencing     songs on disk that ALBUM.json doesn't sequence, and names in
                 ALBUM.json with no matching folder
  links          albums with no streaming links or no release date
  unpublished    albums sitting in ~/Music/Masters that aren't in the repo at
                 all (only visible when run locally)

Exit code is 0 when nothing needs attention, 1 otherwise, so it can gate a job.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
MASTERS_DIR = Path(os.environ.get("MUSIC_MASTERS_DIR", Path.home() / "Music" / "Masters"))
STUB_MARKER = "TODO"
SERVICES = ("spotify", "appleMusic", "amazonMusic")


def is_stub_or_empty(path: Path) -> bool:
    """True when the file is missing, empty, or still the generated stub."""
    if not path.is_file():
        return True
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return True
    # Stub is a title line plus a TODO line and nothing else of substance.
    body = [ln for ln in text.splitlines() if ln.strip()]
    return len(body) <= 2 and any(STUB_MARKER in ln for ln in body)


def album_dirs():
    for item in sorted(REPO_ROOT.iterdir()):
        if item.is_dir() and not item.name.startswith(".") and item.name != "scripts":
            if any(c.is_dir() for c in item.iterdir()):
                yield item


def song_dirs(album: Path):
    for item in sorted(album.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            if (item / "README.md").is_file() or (item / "LYRICS.txt").is_file():
                yield item


def release_assets():
    """Names of assets on the 'latest' release, or None if gh is unavailable."""
    try:
        out = subprocess.run(
            ["gh", "release", "view", "latest", "--json", "assets",
             "-q", ".assets[].name", "--repo", "kepello/music"],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        if out.returncode != 0:
            return None
        return {line.strip() for line in out.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        return None


def collect():
    findings = {
        "missingStory": [], "missingLyrics": [], "missingAudio": [],
        "unsequenced": [], "danglingInAlbumJson": [],
        "missingLinks": [], "missingReleaseDate": [], "unpublishedAlbums": [],
        "draftPastRelease": [], "coverProblem": [],
    }
    assets = release_assets()
    findings["_assetsChecked"] = assets is not None

    repo_albums = set()

    for album in album_dirs():
        repo_albums.add(album.name)
        meta_path = album / "ALBUM.json"
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}

        songs = list(song_dirs(album))
        names = [s.name for s in songs]
        listed = meta.get("tracks") or []

        for extra in [n for n in names if n not in listed]:
            findings["unsequenced"].append(f"{album.name}/{extra}")
        for missing in [n for n in listed if n not in names]:
            findings["danglingInAlbumJson"].append(f"{album.name}/{missing}")

        # Cover art has to satisfy the strictest consumer: CD Baby wants
        # 1400x1400 minimum, square. Art that is too small only fails at upload,
        # which is far too late to discover it.
        cover = next((c for c in album.glob("COVER.*")), None)
        if cover is None:
            findings["coverProblem"].append(f"{album.name}: no cover art")
        else:
            try:
                out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(cover)],
                                     capture_output=True, text=True, timeout=30).stdout
                dims = [int(x.split(":")[1]) for x in out.strip().splitlines() if ":" in x and x.split(":")[1].strip().isdigit()]
                if len(dims) == 2:
                    w, h = dims
                    if w != h:
                        findings["coverProblem"].append(f"{album.name}: {w}x{h} is not square")
                    elif w < 1400:
                        findings["coverProblem"].append(
                            f"{album.name}: {w}x{w} is below CD Baby's 1400 minimum")
            except (OSError, subprocess.SubprocessError, ValueError):
                pass

        # A draft whose release date has arrived is just an album nobody published.
        if meta.get("draft"):
            released = (meta.get("released") or "").strip()
            if released and released <= date.today().isoformat():
                findings["draftPastRelease"].append(f"{album.name} (released {released})")

        # A collection that was never distributed has no release date or store
        # links to be missing, so don't nag about them forever.
        if meta.get("distributed", True):
            links = meta.get("streaming") or {}
            if not any((links.get(s) or "").strip() for s in SERVICES):
                findings["missingLinks"].append(album.name)
            if not (meta.get("released") or "").strip():
                findings["missingReleaseDate"].append(album.name)

        for song in songs:
            label = f"{album.name}/{song.name}"
            if is_stub_or_empty(song / "README.md"):
                findings["missingStory"].append(label)
            if is_stub_or_empty(song / "LYRICS.txt"):
                findings["missingLyrics"].append(label)
            if assets is not None:
                # Must match asset_slug() in generate-catalog.py.
                base = f"{re.sub(r'[^A-Za-z0-9]+', '', album.name)}-{re.sub(r'[^A-Za-z0-9]+', '', song.name)}"
                want = {f"{base}.mp3", f"{base}.m4a"}
                absent = want - assets
                if absent:
                    findings["missingAudio"].append(f"{label} ({', '.join(sorted(absent))})")

    if MASTERS_DIR.is_dir():
        for d in sorted(MASTERS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name not in repo_albums:
                count = len(list(d.glob("*.wav")))
                if count:
                    findings["unpublishedAlbums"].append(f"{d.name} ({count} songs)")

    return findings


SECTIONS = [
    ("draftPastRelease", "Albums still marked draft whose release date has passed",
     "Set \"draft\": false in the album's ALBUM.json to put it on the site"),
    ("coverProblem", "Album art that cannot be distributed",
     "Regenerate at 3000x3000 and run: ./scripts/set-cover.sh <album> <image>"),
    ("unpublishedAlbums", "Albums on your Mac that aren't on the site yet",
     "Run: ./scripts/sync-album.sh '<name>'"),
    ("missingAudio", "Songs with no audio in the release",
     "Run: ./scripts/sync-album.sh '<album>'"),
    ("missingStory", "Songs with no story written yet", "Edit each README.md"),
    ("missingLyrics", "Songs with no lyrics yet", "Edit each LYRICS.txt"),
    ("unsequenced", "Songs not placed in the album running order",
     "Add them to the album's ALBUM.json \"tracks\" list"),
    ("danglingInAlbumJson", "Named in ALBUM.json but no such folder",
     "Fix the name or remove the entry"),
    ("missingLinks", "Albums with no streaming links",
     "Paste Spotify/Apple/Amazon URLs into ALBUM.json"),
    ("missingReleaseDate", "Albums with no release date",
     "Set \"released\" in ALBUM.json"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON instead of prose")
    args = ap.parse_args()

    f = collect()
    if args.json:
        print(json.dumps(f, indent=2))
        return 0 if not any(f[k] for k, _, _ in SECTIONS) else 1

    total = 0
    for key, heading, hint in SECTIONS:
        items = f[key]
        if not items:
            continue
        total += len(items)
        print(f"\n{heading} ({len(items)}):")
        for item in items[:25]:
            print(f"  - {item}")
        if len(items) > 25:
            print(f"  ... and {len(items) - 25} more")
        print(f"  -> {hint}")

    if not f["_assetsChecked"]:
        print("\nNote: could not reach the GitHub release, so audio was not checked.")

    print()
    if total == 0:
        print("Nothing missing. The catalog is complete.")
        return 0
    print(f"{total} thing(s) need attention.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
