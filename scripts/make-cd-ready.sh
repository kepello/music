#!/usr/bin/env bash
#
# make-cd-ready.sh -- produce 44.1kHz/16-bit WAVs for CD Baby upload.
#
#   ./scripts/make-cd-ready.sh OneMoreThing    # one album
#   ./scripts/make-cd-ready.sh --all           # every album
#   ./scripts/make-cd-ready.sh --all -n        # dry run
#
# Output goes to ~/Music/Masters/.cdready/<Album>/, one complete uploadable set
# per album. The masters themselves are NOT modified.
#
# Why alongside rather than in place:
#
#   Suno renders at 48kHz and CD Baby wants 44.1kHz (Red Book). Downsampling is
#   irreversible, so converting a master in place would discard the highest
#   quality copy Carl has. It also historically destroyed provenance: 38 of his
#   66 masters have lost the Suno id from their comment tag, and every one of
#   them belongs to an album that has been through this conversion.
#
#   So the 48kHz master stays canonical -- the site keeps publishing from it --
#   and the CD-ready copy is a derived artifact that can be regenerated or
#   deleted freely. Metadata is carried across explicitly so the copy keeps its
#   provenance too.
#
# Tracks already at 44.1kHz are copied through untouched: re-encoding a file
# that is already at the target rate would only lose quality, and the folder
# needs the whole album to be uploadable.

set -eo pipefail

MASTERS_DIR="${MUSIC_MASTERS_DIR:-$HOME/Music/Masters}"
OUT_ROOT="$MASTERS_DIR/.cdready"
DRY_RUN=0
ALL=0
ALBUM_COUNT=0
ALBUMS=()

for arg in "$@"; do
  case "$arg" in
    -n|--dry-run) DRY_RUN=1 ;;
    --all)        ALL=1 ;;
    -h|--help)    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)           echo "unknown option: $arg" >&2; exit 2 ;;
    *)            ALBUMS[$ALBUM_COUNT]="$arg"; ALBUM_COUNT=$((ALBUM_COUNT + 1)) ;;
  esac
done

command -v ffmpeg >/dev/null 2>&1 || { echo "error: ffmpeg is required" >&2; exit 1; }
[ -d "$MASTERS_DIR" ] || { echo "error: masters dir not found: $MASTERS_DIR" >&2; exit 1; }

# ffmpeg's built-in resampler is used unless libsoxr is present, in which case
# prefer it -- soxr has a materially better anti-aliasing filter for 48k->44.1k,
# which is not an integer ratio.
if ffmpeg -hide_banner -version 2>/dev/null | grep -q 'enable-libsoxr'; then
  RESAMPLE="aresample=resampler=soxr:precision=28:dither_method=triangular"
  RESAMPLER_NAME="soxr (precision 28)"
else
  RESAMPLE="aresample=resampler=swr:dither_method=triangular"
  RESAMPLER_NAME="swr built-in"
fi

if [ "$ALL" = 1 ] || [ "$ALBUM_COUNT" -eq 0 ]; then
  ALBUMS=(); ALBUM_COUNT=0
  for d in "$MASTERS_DIR"/*/; do
    [ -d "$d" ] || continue
    base="$(basename "$d")"
    ALBUMS[$ALBUM_COUNT]="$base"; ALBUM_COUNT=$((ALBUM_COUNT + 1))
  done
fi
[ "$ALBUM_COUNT" -eq 0 ] && { echo "error: no albums found in $MASTERS_DIR" >&2; exit 1; }

say() { printf '%s\n' "$*"; }
say "resampler: $RESAMPLER_NAME"

converted=0; copied=0; skipped=0
for album in "${ALBUMS[@]}"; do
  src="$MASTERS_DIR/$album"
  [ -d "$src" ] || { echo "skipping '$album': no such folder" >&2; continue; }
  out="$OUT_ROOT/$album"

  say ""
  say "=== $album ==="
  [ "$DRY_RUN" = 1 ] || mkdir -p "$out"

  while IFS= read -r f; do
    base="$(basename "${f%.*}")"
    dst="$out/$base.wav"
    sr="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate \
          -of default=nw=1:nk=1 "$f" 2>/dev/null)"

    # Already current? Compare against the source's hash, same rule sync-album
    # uses -- an mtime test silently skips when a master is replaced by an
    # older file.
    stamp="$dst.src-sha256"
    now="$(shasum -a 256 "$f" | cut -d' ' -f1)"
    if [ -f "$dst" ] && [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$now" ]; then
      skipped=$((skipped + 1)); continue
    fi

    if [ "$sr" = "44100" ]; then
      say "  copy      $base.wav (already 44.1kHz)"
      if [ "$DRY_RUN" = 0 ]; then
        cp "$f" "$dst"; printf '%s' "$now" > "$stamp"
      fi
      copied=$((copied + 1))
    else
      say "  resample  $base.wav (${sr}Hz -> 44100Hz)"
      if [ "$DRY_RUN" = 0 ]; then
        # -map_metadata 0 keeps the Suno id; losing it is how provenance eroded
        # on the albums that have already shipped.
        ffmpeg -nostdin -loglevel error -y -i "$f" \
          -map_metadata 0 -vn -af "$RESAMPLE" \
          -ar 44100 -c:a pcm_s16le "$dst"
        printf '%s' "$now" > "$stamp"
      fi
      converted=$((converted + 1))
    fi
  done < <(find "$src" -maxdepth 1 -type f \( -iname '*.wav' -o -iname '*.mp3' \) | sort)
done

say ""
say "resampled $converted, copied $copied, already current $skipped"
[ "$DRY_RUN" = 1 ] && say "(dry run -- nothing written)"
say "CD-ready sets: $OUT_ROOT/<Album>/"
