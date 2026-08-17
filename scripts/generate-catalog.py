#!/usr/bin/env python3
"""
Generate catalog.json (and the per-album M3U8 playlists) for the music repository.

Track discovery is driven by the *text* in the repo -- a song folder counts as a
track when it holds a README.md or LYRICS.txt.  Audio never lives in git: the
MP3/M4A are uploaded to the "latest" GitHub Release by scripts/sync-album.sh and
referenced here by URL, and the WAV masters stay on Carl's machine under
~/Music/Masters.

Album ordering, descriptions and streaming links come from an ALBUM.json in each
album folder, so adding an album never requires editing this file.
See CATALOG_README.md for the schema.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

RELEASE_TAG = "latest"

# A song folder is a track when it contains one of these.
TRACK_MARKERS = ("README.md", "LYRICS.txt")

COVER_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def read_text(path: Path) -> Optional[str]:
    """Read a UTF-8 text file, returning None when absent or empty."""
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content or None
    except (OSError, UnicodeDecodeError):
        return None


def read_readme(directory: Path) -> Optional[str]:
    return read_text(directory / "README.md")


# Suno takes structural direction inline -- [Intro], [Verse 1, Female Vocals],
# [Instrumental]. Useful to keep in the source file, since it is what gets fed
# back to Suno on a re-generation, but it is production scaffolding and no
# reader wants it in the middle of the words.
SUNO_DIRECTIVE = re.compile(r"^\s*\[[^\]]*\]\s*$")
# A direction can also sit at the head of a sung line -- "[quieter, nearly
# whispered] \"Curse God and die!\"" -- where dropping the whole line would take
# the lyric with it. Strip only the leading bracket, keep what follows.
LEADING_DIRECTIVE = re.compile(r"^\s*\[[^\]]*\]\s*")


def strip_suno_directives(text: Optional[str]) -> Optional[str]:
    """
    Drop whole lines that are nothing but a bracketed Suno directive.

    Whole-line tags are dropped. A direction at the head of a sung line has its
    bracket removed and the words kept. Brackets anywhere else survive:
    stripping every [...] in the file, as the old clean-lyrics.py did, would
    quietly eat part of a real line.
    """
    if not text:
        return text
    kept = []
    for ln in text.splitlines():
        if SUNO_DIRECTIVE.match(ln):
            continue                      # the whole line is direction
        kept.append(LEADING_DIRECTIVE.sub("", ln))
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or None


# Roughly two thirds of the lyric files open with a _Title_ line and the rest
# do not. The site already shows the track title above the lyric, so where the
# line is present it renders the title twice.
LYRIC_TITLE = re.compile(r"^_.+_$")


def strip_leading_title(text: Optional[str]) -> Optional[str]:
    """Drop a _Title_ line if it is the first non-empty line, and only there."""
    if not text:
        return text
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if LYRIC_TITLE.match(line.strip()):
            return "\n".join(lines[i + 1:]).strip() or None
        break   # first real line isn't a title; leave underscores alone elsewhere
    return text


def read_lyrics(directory: Path) -> Optional[str]:
    return strip_leading_title(strip_suno_directives(read_text(directory / "LYRICS.txt")))


def read_album_meta(album_dir: Path) -> Dict:
    """Load ALBUM.json if present. Missing file is fine -- everything is optional."""
    meta_path = album_dir / "ALBUM.json"
    if not meta_path.is_file():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  WARNING: could not read {meta_path.name}: {exc}", flush=True)
        return {}


def clean_links(links: Optional[Dict]) -> Optional[Dict]:
    """Drop unfilled placeholders so the site never renders an empty link."""
    if not isinstance(links, dict):
        return None
    filled = {k: v for k, v in links.items() if isinstance(v, str) and v.strip()}
    return filled or None


def extract_friendly_name(directory: Path) -> Optional[str]:
    """Pull the display title from the first _underscored_ line of README.md."""
    readme = read_readme(directory)
    if not readme:
        return None

    for line in readme.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("_") and line.endswith("_") and len(line) > 2:
            return line[1:-1].strip()
        # First non-empty line wasn't a title -- stop looking.
        return None
    return None


def find_cover_image(directory: Path, repo_root: Path) -> Optional[str]:
    """Find a cover*.{jpg,png,...} in the directory, as a repo-relative path."""
    if not directory.is_dir():
        return None

    for item in sorted(directory.iterdir()):
        if item.is_file() and item.name.lower().startswith("cover"):
            if item.suffix.lower() in COVER_EXTS:
                return str(item.relative_to(repo_root))
    return None


def is_track_dir(path: Path) -> bool:
    if not path.is_dir() or path.name.startswith("."):
        return False
    return any((path / marker).is_file() for marker in TRACK_MARKERS)


def asset_slug(text: str) -> str:
    """
    Reduce a name to letters and digits only.

    Release assets share one flat namespace, so audio is published as
    <Album>-<Song>.<ext>: 'Cami' means one thing in Digressions and another in
    Moved Me First. Stripping punctuation also sidesteps GitHub rewriting
    spaces to dots in asset filenames, which would break these URLs.
    """
    return re.sub(r"[^A-Za-z0-9]+", "", text)


def asset_name(album: str, song: str, ext: str) -> str:
    return f"{asset_slug(album)}-{asset_slug(song)}.{ext}"


def release_url(owner: str, repo: str, filename: str) -> str:
    return f"https://github.com/{owner}/{repo}/releases/download/{RELEASE_TAG}/{filename}"


def stream_url(owner: str, repo: str, branch: str, filename: str) -> str:
    """
    Playback URL, served from raw.githubusercontent.

    iOS will not play a GitHub release asset: those arrive as
    application/octet-stream through a signed cross-host redirect and fail with
    SRC_NOT_SUPPORTED. raw.githubusercontent serves a clean path as audio/mpeg.
    """
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/stream/{filename}"


def process_track(
    track_dir: Path,
    repo_root: Path,
    owner: str,
    repo: str,
    branch: str,
    album_name: str,
    track_number: Optional[int],
    streaming: Optional[Dict],
) -> Dict:
    """Build a track object. Audio URLs are derived from the folder name."""
    name = track_dir.name

    return {
        "name": name,
        "title": extract_friendly_name(track_dir),
        "trackNumber": track_number,
        "path": str(track_dir.relative_to(repo_root)),
        "readme": read_readme(track_dir),
        "cover": find_cover_image(track_dir, repo_root),
        # mp3 is what the player loads; m4a stays on the release as the
        # fallback and the download.
        "mp3": stream_url(owner, repo, branch, asset_name(album_name, name, "mp3")),
        "m4a": release_url(owner, repo, asset_name(album_name, name, "m4a")),
        "download": release_url(owner, repo, asset_name(album_name, name, "mp3")),
        "lyrics": read_lyrics(track_dir),
        "streaming": clean_links(streaming),
    }


def order_tracks(track_dirs: List[Path], meta: Dict) -> List[Path]:
    """
    Order tracks by the "tracks" list in ALBUM.json.

    Anything listed but missing from disk is reported and skipped; anything on
    disk but unlisted is appended alphabetically so a new song still shows up
    before its sequencing has been decided.
    """
    by_name = {d.name: d for d in track_dirs}
    listed = meta.get("tracks") or []

    ordered: List[Path] = []
    for name in listed:
        if name in by_name:
            ordered.append(by_name.pop(name))
        else:
            print(f"  WARNING: ALBUM.json lists '{name}' but no such folder exists", flush=True)

    leftovers = sorted(by_name.values(), key=lambda d: d.name)
    for extra in leftovers:
        print(f"  NOTE: '{extra.name}' is not sequenced in ALBUM.json (appended)", flush=True)
    ordered.extend(leftovers)

    return ordered


def write_playlist(path: Path, entries: List[tuple]) -> None:
    """Write an EXTM3U playlist of (display title, url) pairs."""
    lines = ["#EXTM3U", "#EXTENC:UTF-8"]
    for title, url in entries:
        lines.append(f"#EXTINF:-1,{title}")
        lines.append(url)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_collection(album_dir: Path, repo_root: Path, owner: str, repo: str, branch: str) -> Optional[Dict]:
    """Process an album folder into a collection object, writing its playlists."""
    if not album_dir.is_dir() or album_dir.name.startswith("."):
        return None

    album_name = album_dir.name
    track_dirs = [d for d in sorted(album_dir.iterdir()) if is_track_dir(d)]
    if not track_dirs:
        return None

    meta = read_album_meta(album_dir)
    if meta.get("draft"):
        print(f"Collection: {album_name} -- SKIPPED (draft: not yet released)", flush=True)
        return None

    print(f"Collection: {album_name}", flush=True)
    ordered = order_tracks(track_dirs, meta)

    per_track_streaming = meta.get("trackStreaming") or {}
    tracks = [
        process_track(
            track_dir,
            repo_root,
            owner,
            repo,
            branch,
            album_name,
            track_number=index,
            streaming=per_track_streaming.get(track_dir.name),
        )
        for index, track_dir in enumerate(ordered, start=1)
    ]

    # Playlists mirror the catalog order and point at the release assets.
    playlist_m4a = album_dir / f"{album_name}-M4A.m3u8"
    playlist_mp3 = album_dir / f"{album_name}-MP3.m3u8"
    write_playlist(playlist_m4a, [(t["title"] or t["name"], t["m4a"]) for t in tracks])
    write_playlist(playlist_mp3, [(t["title"] or t["name"], t["mp3"]) for t in tracks])

    print(f"  {len(tracks)} tracks", flush=True)

    return {
        "name": album_name,
        "title": meta.get("title") or album_name,
        "artist": (meta.get("artist") or "").strip() or None,
        "path": str(album_dir.relative_to(repo_root)),
        "readme": read_readme(album_dir),
        "cover": find_cover_image(album_dir, repo_root),
        "released": meta.get("released"),
        "streaming": clean_links(meta.get("streaming")),
        "playlistM4A": str(playlist_m4a.relative_to(repo_root)),
        "playlistMP3": str(playlist_mp3.relative_to(repo_root)),
        "tracks": tracks,
    }


def generate_catalog(repo_root: Path, owner: str = "kepello", repo: str = "music", branch: str = "main") -> Dict:
    """Generate the complete catalog structure."""
    collections = []

    for item in sorted(repo_root.iterdir()):
        if item.is_dir() and not item.name.startswith(".") and item.name != "scripts":
            collection = process_collection(item, repo_root, owner, repo, branch)
            if collection:
                collections.append(collection)

    return {
        "version": "1.1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "repository": {"owner": owner, "repo": repo, "branch": branch},
        "cover": find_cover_image(repo_root, repo_root),
        "readme": read_readme(repo_root),
        "collections": collections,
    }


def clean_catalog(obj):
    """Remove None values from the catalog structure."""
    if isinstance(obj, dict):
        return {k: clean_catalog(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [clean_catalog(item) for item in obj]
    return obj


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent.resolve()

    print(f"Generating catalog for repository at: {repo_root}", flush=True)

    catalog = clean_catalog(generate_catalog(repo_root))

    catalog_path = repo_root / "catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    total = sum(len(c["tracks"]) for c in catalog["collections"])
    print("Catalog generated successfully!", flush=True)
    print(f"Collections: {len(catalog['collections'])}  Tracks: {total}", flush=True)
    print(f"Output: {catalog_path}", flush=True)
