#!/usr/bin/env bash
#
# sync-album.sh -- encode WAV masters and publish them, without putting audio in git.
#
#   ./scripts/sync-album.sh Overtones      # one album
#   ./scripts/sync-album.sh --all          # every album under the masters dir
#   ./scripts/sync-album.sh Overtones -n   # dry run, just say what would happen
#
# For each WAV in ~/Music/Masters/<Album>/ it will:
#   1. encode MP3 + M4A into a local cache (skipped when already current)
#   2. upload them to the "latest" GitHub release with --clobber (never deletes)
#   3. create <Album>/<Song>/ in the repo with README.md + LYRICS.txt stubs
#   4. add the song to <Album>/ALBUM.json if it isn't sequenced yet
#
# It never touches the WAVs and never removes a release asset.

# NOTE: macOS ships bash 3.2, where expanding an empty array under `set -u`
# is itself an error -- so -u is deliberately left off.
set -eo pipefail

MASTERS_DIR="${MUSIC_MASTERS_DIR:-$HOME/Music/Masters}"
CACHE_DIR="${MUSIC_ENCODE_CACHE:-$MASTERS_DIR/.encoded}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_TAG="latest"
ARTIST="Kepello"
SITE_URL="https://kepello.github.io/Musicplayer/"
CD_SAMPLE_RATE=44100          # Red Book / what CD Baby requires

# soxr has a materially better anti-aliasing filter for 48k->44.1k, which is not
# an integer ratio. Fall back to ffmpeg's built-in resampler when it is absent.
if ffmpeg -hide_banner -version 2>/dev/null | grep -q 'enable-libsoxr'; then
  RESAMPLE="aresample=resampler=soxr:precision=28:dither_method=triangular"
else
  RESAMPLE="aresample=resampler=swr:dither_method=triangular"
fi

DRY_RUN=0
ALL=0
ALBUM_COUNT=0
ALBUMS=()

for arg in "$@"; do
  case "$arg" in
    -n|--dry-run) DRY_RUN=1 ;;
    --all)        ALL=1 ;;
    -h|--help)    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' ; exit 0 ;;
    -*)           echo "unknown option: $arg" >&2 ; exit 2 ;;
    *)            ALBUMS[$ALBUM_COUNT]="$arg" ; ALBUM_COUNT=$((ALBUM_COUNT + 1)) ;;
  esac
done

say()  { printf '%s\n' "$*"; }
run()  { if [ "$DRY_RUN" = 1 ]; then say "  [dry-run] $*"; else "$@"; fi; }

# Release assets are one flat namespace, so audio is published as
# <Album>-<Song>.<ext> with punctuation stripped. Must stay identical to
# asset_slug() in generate-catalog.py or the catalog will point at 404s.
slug() { printf '%s' "$1" | LC_ALL=C tr -cd 'A-Za-z0-9'; }

for tool in ffmpeg gh; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: '$tool' is required but not installed" >&2; exit 1; }
done

[ -d "$MASTERS_DIR" ] || { echo "error: masters dir not found: $MASTERS_DIR" >&2; exit 1; }

if [ "$ALL" = 1 ] || [ "$ALBUM_COUNT" -eq 0 ]; then
  ALBUMS=()
  ALBUM_COUNT=0
  for d in "$MASTERS_DIR"/*/; do
    [ -d "$d" ] || continue
    base="$(basename "$d")"
    [ "$base" = ".encoded" ] && continue
    ALBUMS[$ALBUM_COUNT]="$base"
    ALBUM_COUNT=$((ALBUM_COUNT + 1))
  done
fi

if [ "$ALBUM_COUNT" -eq 0 ]; then
  echo "error: no albums found in $MASTERS_DIR" >&2
  exit 1
fi

# Make sure the release exists before we try to upload into it.
ensure_release() {
  if ! gh release view "$RELEASE_TAG" --repo kepello/music >/dev/null 2>&1; then
    say "Creating release '$RELEASE_TAG'..."
    run gh release create "$RELEASE_TAG" --repo kepello/music \
      --title "Latest Album Packages" \
      --notes "Individual track downloads. Updated automatically by sync-album.sh." \
      --latest
  fi
}

# encode <master> <out> <codec-args...>
#
# Freshness is decided by the master's content hash, not its timestamp. An
# mtime comparison silently skips the re-encode when a master is *replaced by an
# older file* -- restoring an archived take, say -- and the site would go on
# serving audio that no longer matches its master. The hash is recorded in a
# sidecar next to the cached encode.
encode_if_stale() {
  local master="$1" out="$2"; shift 2
  local stamp="$out.src-sha256"
  local now
  now="$(shasum -a 256 "$master" | cut -d' ' -f1)"

  if [ -f "$out" ] && [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$now" ]; then
    return 1   # encode was made from exactly this master
  fi

  run ffmpeg -nostdin -loglevel error -y -i "$master" -vn -map_metadata -1 \
    -metadata artist="$ARTIST" -metadata comment="$SITE_URL" "$@" "$out"
  [ "$DRY_RUN" = 1 ] || printf '%s' "$now" > "$stamp"
  return 0
}

# Masters are kept at CD quality so there is only ever one copy of a song.
#
# Suno renders at 48kHz and CD Baby wants 44.1kHz (Red Book), so a WAV master
# arriving at any other rate is converted in place, here, on ingest. Carl chose
# a single CD-quality master over keeping a 48kHz original alongside it; the
# 48kHz version remains recoverable from his Suno library, which is what the
# Suno id in provenance.json is for.
#
# Metadata is carried across explicitly. Losing it is exactly how 38 masters
# ended up with no Suno id: this same conversion, done by a tool that dropped
# the tags.
normalize_master() {
  local master="$1"
  case "$(printf '%s' "${master##*.}" | tr 'A-Z' 'a-z')" in wav) ;; *) return 1 ;; esac

  local sr
  sr="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate \
        -of default=nw=1:nk=1 "$master" 2>/dev/null)"
  [ "$sr" = "$CD_SAMPLE_RATE" ] && return 1

  say "  normalise $(basename "$master") (${sr}Hz -> ${CD_SAMPLE_RATE}Hz, CD quality)"
  [ "$DRY_RUN" = 1 ] && return 0

  local tmp="${master%.wav}.normalising.wav"
  ffmpeg -nostdin -loglevel error -y -i "$master" \
    -map_metadata 0 -vn -af "$RESAMPLE" \
    -ar "$CD_SAMPLE_RATE" -c:a pcm_s16le "$tmp"

  # Only replace once the new file is proven good -- a truncated convert must
  # never be allowed to destroy the only copy of a master.
  local got
  got="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate \
         -of default=nw=1:nk=1 "$tmp" 2>/dev/null)"
  if [ "$got" != "$CD_SAMPLE_RATE" ] || [ ! -s "$tmp" ]; then
    rm -f "$tmp"
    echo "error: conversion of $master failed; master left untouched" >&2
    return 1
  fi
  mv "$tmp" "$master"
  return 0
}

scaffold_song() {
  local album="$1" song="$2"
  local dir="$REPO_ROOT/$album/$song"

  if [ ! -d "$dir" ]; then
    say "  + new song folder: $album/$song"
    run mkdir -p "$dir"
  fi

  if [ ! -f "$dir/README.md" ]; then
    say "  + README.md stub (needs your story)"
    if [ "$DRY_RUN" = 0 ]; then
      printf '_%s_\n\nTODO: write the story behind this song.\n' "$song" > "$dir/README.md"
    fi
  fi

  if [ ! -f "$dir/LYRICS.txt" ]; then
    say "  + LYRICS.txt stub (needs your lyrics)"
    if [ "$DRY_RUN" = 0 ]; then
      printf '_%s_\n\nTODO: paste the lyrics.\n' "$song" > "$dir/LYRICS.txt"
    fi
  fi
}

# Append any unsequenced songs to ALBUM.json so they still appear on the site.
sync_album_json() {
  local album="$1"; shift
  local meta="$REPO_ROOT/$album/ALBUM.json"
  [ "$DRY_RUN" = 1 ] && return 0

  ALBUM_NAME="$album" ALBUM_META="$meta" SONGS="$*" python3 - <<'PY'
import json, os, pathlib
meta_path = pathlib.Path(os.environ["ALBUM_META"])
songs = os.environ["SONGS"].split()
album = os.environ["ALBUM_NAME"]

if meta_path.is_file():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
else:
    meta = {"title": album, "released": "",
            "streaming": {"spotify": "", "appleMusic": "", "amazonMusic": ""},
            "tracks": [], "trackStreaming": {}}

listed = meta.setdefault("tracks", [])
added = [s for s in songs if s not in listed]
listed.extend(added)
meta.setdefault("trackStreaming", {})

meta_path.parent.mkdir(parents=True, exist_ok=True)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
for s in added:
    print(f"  + sequenced '{s}' at position {listed.index(s) + 1} in ALBUM.json")
PY
}

ensure_release

for album in "${ALBUMS[@]}"; do
  src="$MASTERS_DIR/$album"
  [ -d "$src" ] || { echo "skipping '$album': no such folder in $MASTERS_DIR" >&2; continue; }

  say ""
  say "=== $album ==="
  mkdir -p "$CACHE_DIR/$album"

  songs=()
  uploads=()

  while IFS= read -r master; do
    song="$(basename "${master%.*}")"
    songs+=("$song")

    normalize_master "$master" || true

    asset="$(slug "$album")-$(slug "$song")"
    mp3="$CACHE_DIR/$album/$asset.mp3"
    m4a="$CACHE_DIR/$album/$asset.m4a"

    case "$(printf '%s' "${master##*.}" | tr 'A-Z' 'a-z')" in
      mp3)
        # Master is already lossy. Copy the stream rather than re-encoding it,
        # so publishing costs no further generation loss; only the M4A has to
        # be transcoded, and it can be no better than its source.
        if encode_if_stale "$master" "$mp3" -c:a copy; then
          say "  copied  $asset.mp3 (lossy master, stream copied)"; uploads+=("$mp3")
        fi
        if encode_if_stale "$master" "$m4a" -c:a aac -b:a 256k -movflags +faststart; then
          say "  encoded $asset.m4a (transcoded from MP3)"; uploads+=("$m4a")
        fi
        ;;
      *)
        if encode_if_stale "$master" "$mp3" -c:a libmp3lame -q:a 0; then
          say "  encoded $asset.mp3"; uploads+=("$mp3")
        fi
        if encode_if_stale "$master" "$m4a" -c:a aac -b:a 320k -movflags +faststart; then
          say "  encoded $asset.m4a"; uploads+=("$m4a")
        fi
        ;;
    esac

    scaffold_song "$album" "$song"
    # A WAV always wins over an MP3 of the same song, so a later re-export
    # silently upgrades the master without needing the MP3 deleted first.
  done < <(find "$src" -maxdepth 1 -type f \( -iname '*.wav' -o -iname '*.mp3' \) | sort |
           awk -F/ '{ n=$NF; sub(/\.[^.]*$/,"",n); if (!(n in seen) || $0 ~ /\.[wW][aA][vV]$/) { seen[n]=$0 } } END { for (k in seen) print seen[k] }' | sort)

  if [ ${#songs[@]} -eq 0 ]; then
    say "  (no WAV or MP3 masters found)"
    continue
  fi

  sync_album_json "$album" "${songs[@]}"

  if [ ${#uploads[@]} -gt 0 ]; then
    say "  uploading ${#uploads[@]} file(s) to release '$RELEASE_TAG'..."
    run gh release upload "$RELEASE_TAG" "${uploads[@]}" --repo kepello/music --clobber
  else
    say "  all encodings already current -- nothing to upload"
  fi
done

say ""
say "Done. Next: fill in any README.md / LYRICS.txt stubs, then commit and push."
say "The Build Catalog action will regenerate catalog.json and the site picks it up automatically."
