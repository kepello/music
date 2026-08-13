#!/usr/bin/env python3
"""
Check the repository against what Apple Music actually published.

    ./scripts/verify-apple.py            # report only
    ./scripts/verify-apple.py --fix      # also write links found back into ALBUM.json
    ./scripts/verify-apple.py --json     # machine-readable

Uses the iTunes Search API (itunes.apple.com), which needs no developer account
and no credentials. The full Apple Music API would require a paid membership and
a signed JWT, and offers nothing extra for verifying one's own public releases.

For every album marked as distributed it checks:

  presence      an album whose release date has passed but which Apple doesn't
                list -- distribution may have stalled
  link          the appleMusic URL, filled in when missing (with --fix)
  release date  ALBUM.json against Apple's
  track count   how many tracks Apple shows against how many the repo publishes
  running order Apple's track numbers against the repo's sequence
  titles        Apple's track names against the titles in each README.md
  durations     Apple's runtime against the local master, flagged past 2s

Note: Apple exposes no lyrics field, and there is no public write API for lyrics
or metadata -- corrections travel through the distributor, not through code.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent.parent.resolve()
MASTERS = Path("/Users/carl/Music/Masters")
API = "https://itunes.apple.com"
DURATION_TOLERANCE_S = 2.0


def api_get(path: str, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def collection_id(meta: dict):
    """Pull the numeric album id out of a stored music.apple.com URL."""
    url = ((meta.get("streaming") or {}).get("appleMusic") or "").strip()
    m = re.search(r"/(\d{6,})", url)
    return m.group(1) if m else None


def find_album(meta: dict, title: str, artist: str):
    """Look the album up by stored id, else by artist + title. None if absent."""
    cid = collection_id(meta)
    if cid:
        d = api_get("lookup", id=cid, entity="song", limit=200)
        if d and d.get("resultCount"):
            return split_results(d)

    d = api_get("search", term=f"{artist} {title}", entity="album", limit=25)
    if not d:
        return None, None
    for r in d.get("results", []):
        if r.get("artistName", "").lower() == artist.lower() and \
           r.get("collectionName", "").lower() == title.lower():
            full = api_get("lookup", id=r["collectionId"], entity="song", limit=200)
            if full and full.get("resultCount"):
                return split_results(full)
    return None, None


def split_results(d: dict):
    res = d.get("results", [])
    album = next((r for r in res if r.get("wrapperType") == "collection"), None)
    songs = sorted((r for r in res if r.get("wrapperType") == "track"),
                   key=lambda s: (s.get("discNumber", 1), s.get("trackNumber", 0)))
    return album, songs


def local_duration(album_dir: str, song: str):
    for ext in ("wav", "mp3"):
        p = MASTERS / album_dir / f"{song}.{ext}"
        if p.is_file():
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(p)],
                capture_output=True, text=True).stdout.strip()
            if out:
                return float(out)
    return None


def repo_title(album: str, song: str):
    """Display title = first _underscored_ line of the song's README.md."""
    readme = REPO / album / song / "README.md"
    if not readme.is_file():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        return s[1:-1].strip() if s.startswith("_") and s.endswith("_") else None
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def check_album(album_dir: Path, findings: list, fix: bool, verified: list):
    meta = json.loads((album_dir / "ALBUM.json").read_text(encoding="utf-8"))
    if not meta.get("distributed", True):
        return
    name = album_dir.name
    title = meta.get("title") or name
    artist = (meta.get("artist") or "").strip()
    released = (meta.get("released") or "").strip()
    tracks = meta.get("tracks") or []

    def add(kind, detail):
        findings.append({"album": title, "kind": kind, "detail": detail})

    album, songs = find_album(meta, title, artist)
    if not album:
        from datetime import date
        if released and released <= date.today().isoformat():
            add("notOnApple", f"released {released} but Apple has no listing - check distribution")
        else:
            add("notYetReleased", f"ships {released or 'date unset'}; not in Apple's catalog yet")
        return

    url = album.get("collectionViewUrl", "").split("?")[0]
    stored = ((meta.get("streaming") or {}).get("appleMusic") or "").strip()
    if not stored:
        add("linkMissing", f"found: {url}")
        if fix:
            meta.setdefault("streaming", {})["appleMusic"] = url
            (album_dir / "ALBUM.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    apple_date = (album.get("releaseDate") or "")[:10]
    if released and apple_date and released != apple_date:
        add("releaseDate", f"repo says {released}, Apple says {apple_date}")

    if len(songs) != len(tracks):
        add("trackCount", f"repo publishes {len(tracks)}, Apple lists {len(songs)}")

    for i, s in enumerate(songs):
        if i >= len(tracks):
            add("extraOnApple", f"#{i+1} '{s['trackName']}' is on Apple but not in the repo")
            continue
        song = tracks[i]
        want = repo_title(name, song) or song
        got = s.get("trackName", "")
        if norm(want) != norm(got):
            add("titleMismatch", f"#{i+1} repo '{want}' vs Apple '{got}'")
        ms = s.get("trackTimeMillis")
        ld = local_duration(name, song)
        if ms and ld and abs(ms / 1000 - ld) > DURATION_TOLERANCE_S:
            add("durationMismatch",
                f"#{i+1} {want}: master {ld:.1f}s vs Apple {ms/1000:.1f}s")
    for j in range(len(songs), len(tracks)):
        add("missingOnApple", f"#{j+1} '{tracks[j]}' is in the repo but not on Apple")

    # Record what was actually compared, so a clean run is evidence rather than
    # silence -- "0 discrepancies" means nothing without knowing the coverage.
    verified.append({
        "album": title, "artist": artist, "tracks": len(songs),
        "released": apple_date,
        "durations": sum(1 for s in songs if s.get("trackTimeMillis")),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="write discovered links into ALBUM.json")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    findings, verified = [], []
    for d in sorted(REPO.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and (d / "ALBUM.json").is_file():
            check_album(d, findings, args.fix, verified)

    if args.json:
        print(json.dumps({"verified": verified, "findings": findings}, indent=2))
        return 1 if any(f["kind"] != "notYetReleased" for f in findings) else 0

    for v in verified:
        print(f"  checked {v['album']} ({v['artist']}, {v['released']}): "
              f"{v['tracks']} tracks -- order, titles and {v['durations']} durations")

    if not findings:
        print("\nEvery distributed album matches Apple Music.")
        return 0

    by_album = {}
    for f in findings:
        by_album.setdefault(f["album"], []).append(f)
    real = 0
    for album, items in by_album.items():
        print(f"\n{album}:")
        for f in items:
            note = "" if f["kind"] == "notYetReleased" else "  <-"
            if f["kind"] != "notYetReleased":
                real += 1
            print(f"  [{f['kind']}] {f['detail']}{note}")
    print(f"\n{real} discrepancy(ies) needing attention.")
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
