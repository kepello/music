#!/usr/bin/env bash
#
# set-cover.sh -- install album art at a size that works everywhere.
#
#   ./scripts/set-cover.sh Fly ~/Desktop/Unreleased.png    # install a new cover
#   ./scripts/set-cover.sh --check                         # audit every album
#
# One cover per album serves both the site and CD Baby, so it has to satisfy the
# strictest consumer:
#
#   CD Baby   1400x1400 minimum, 3000x3000 maximum, square, RGB, under 25MB
#   Apple     3000x3000 preferred for best presentation
#
# So the target is 3000x3000 when the source allows it, and the source's own
# size when it does not. Art is never upscaled: enlarging invents detail that
# was not photographed or drawn, and looks worse than the original at every size
# it will actually be viewed. A source below 1400 is installed for the site and
# reported as undistributable, which is a fact worth surfacing early rather than
# discovering at upload.

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CDBABY_MIN=1400
CDBABY_MAX=3000

command -v sips >/dev/null 2>&1 || { echo "error: sips is required (macOS)" >&2; exit 1; }

dim() { sips -g "$1" "$2" 2>/dev/null | tail -1 | awk '{print $2}'; }

check_all() {
  local issues=0
  printf "  %-16s %-12s %-9s %s\n" "ALBUM" "SIZE" "FORMAT" "STATUS"
  for meta in "$REPO_ROOT"/*/ALBUM.json; do
    [ -f "$meta" ] || continue
    local album cover w h fmt status
    album="$(basename "$(dirname "$meta")")"
    cover="$(find "$REPO_ROOT/$album" -maxdepth 1 -iname 'COVER.*' | head -1)"
    if [ -z "$cover" ]; then
      printf "  %-16s %-12s %-9s %s\n" "$album" "-" "-" "NO COVER"
      issues=$((issues + 1)); continue
    fi
    w="$(dim pixelWidth "$cover")"; h="$(dim pixelHeight "$cover")"
    fmt="$(dim format "$cover")"
    if [ "$w" != "$h" ]; then
      status="NOT SQUARE"; issues=$((issues + 1))
    elif [ "$w" -lt "$CDBABY_MIN" ]; then
      status="below CD Baby minimum (${CDBABY_MIN}) - site only"; issues=$((issues + 1))
    elif [ "$w" -lt "$CDBABY_MAX" ]; then
      status="ok (Apple prefers ${CDBABY_MAX})"
    else
      status="ok"
    fi
    printf "  %-16s %-12s %-9s %s\n" "$album" "${w}x${h}" "$fmt" "$status"
  done
  [ "$issues" -eq 0 ] && echo "  all covers distributable" || echo "  $issues album(s) need better art"
  return 0
}

[ "${1:-}" = "--check" ] && { check_all; exit 0; }

ALBUM="${1:-}"; SRC="${2:-}"
[ -n "$ALBUM" ] && [ -n "$SRC" ] || { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ -d "$REPO_ROOT/$ALBUM" ] || { echo "error: no album '$ALBUM'" >&2; exit 1; }
[ -f "$SRC" ] || { echo "error: no such image: $SRC" >&2; exit 1; }

W="$(dim pixelWidth "$SRC")"; H="$(dim pixelHeight "$SRC")"
[ -n "$W" ] && [ -n "$H" ] || { echo "error: '$SRC' is not a readable image" >&2; exit 1; }
echo "  source: ${W}x${H}"

if [ "$W" != "$H" ]; then
  echo "error: cover art must be square; this is ${W}x${H}." >&2
  echo "       Crop it first -- cropping is your decision, not one to make automatically." >&2
  exit 1
fi

# Replace whatever cover the album has, whatever its extension.
find "$REPO_ROOT/$ALBUM" -maxdepth 1 -iname 'COVER.*' -delete
EXT="$(printf '%s' "${SRC##*.}" | tr 'A-Z' 'a-z')"; [ "$EXT" = "jpeg" ] && EXT="jpg"
DEST="$REPO_ROOT/$ALBUM/COVER.$EXT"

if [ "$W" -gt "$CDBABY_MAX" ]; then
  echo "  downscaling to ${CDBABY_MAX}x${CDBABY_MAX} (CD Baby maximum)"
  sips -s format "$([ "$EXT" = jpg ] && echo jpeg || echo "$EXT")" \
       -z "$CDBABY_MAX" "$CDBABY_MAX" -s dpiHeight 300 -s dpiWidth 300 \
       "$SRC" --out "$DEST" >/dev/null
else
  echo "  keeping native size (never upscaled)"
  sips -s dpiHeight 300 -s dpiWidth 300 "$SRC" --out "$DEST" >/dev/null
fi

NW="$(dim pixelWidth "$DEST")"
echo "  installed: ${ALBUM}/COVER.$EXT at ${NW}x${NW}, 300 DPI"
if [ "$NW" -lt "$CDBABY_MIN" ]; then
  echo
  echo "  WARNING: ${NW}px is below CD Baby's ${CDBABY_MIN}px minimum."
  echo "           Fine for the site; this album cannot be distributed with this art."
  echo "           Regenerate the source at ${CDBABY_MAX}x${CDBABY_MAX} rather than upscaling."
fi
