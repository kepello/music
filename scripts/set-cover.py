#!/usr/bin/env python3
"""
Install album art at the size distributors expect, upscaling when needed.

    ./scripts/set-cover.py Fly ~/Desktop/Unreleased.png   # install a new cover
    ./scripts/set-cover.py --check                        # audit every album
    ./scripts/set-cover.py --fix-all                      # bring every cover up to spec

One cover per album has to satisfy the strictest consumer:

    CD Baby   1400x1400 minimum, 3000x3000 maximum, square, RGB, under 25MB
    Apple     3000x3000 preferred

So TARGET is 3000: art above it is downscaled, art below it is upscaled.

On upscaling: enlarging cannot recover detail that was never in the source, and
a 1024px original stretched to 3000px is soft at full size no matter how good
the filter. Lanczos is used because it is the best-behaved of the practical
resampling kernels for enlargement, but the honest fix for a small source is to
regenerate the art larger. The upscale factor is always reported so the cost is
visible rather than hidden.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("error: Pillow is required (pip install Pillow)", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).parent.parent.resolve()
TARGET = 3000          # what Apple prefers and CD Baby caps at
CDBABY_MIN = 1400
CDBABY_MAX = 3000
DPI = (300, 300)


def album_dirs():
    for d in sorted(REPO.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and (d / "ALBUM.json").is_file():
            yield d


def find_cover(album: Path):
    for p in sorted(album.iterdir()):
        if p.is_file() and p.stem.upper() == "COVER":
            return p
    return None


def describe(path: Path):
    with Image.open(path) as im:
        return im.size, im.mode, (im.format or path.suffix.lstrip(".")).upper()


def install(album: Path, src: Path, target: int = TARGET):
    """Write src into album as COVER.<ext> at `target` square, 300 DPI, RGB."""
    with Image.open(src) as im:
        w, h = im.size
        if w != h:
            print(f"  error: cover art must be square; {src.name} is {w}x{h}.", file=sys.stderr)
            print("         Crop it first -- which part to keep is your decision.", file=sys.stderr)
            return False

        if im.mode not in ("RGB", "L"):
            print(f"  converting {im.mode} -> RGB")
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")

        if w > target:
            print(f"  downscaling {w} -> {target}")
        elif w < target:
            print(f"  upscaling   {w} -> {target}  ({target / w:.2f}x, Lanczos)")
            if w < CDBABY_MIN:
                print(f"    note: source is below CD Baby's {CDBABY_MIN}px minimum, so this "
                      f"is interpolated detail; regenerating at {target}px would be sharper")
        else:
            print(f"  already {target}px")

        out = im if w == target else im.resize((target, target), Image.LANCZOS)

        # Always JPEG. At 3000px a PNG of this art runs 8-14MB, and the site's
        # home page loads every cover at once -- 35MB of album art before a
        # visitor reads a word. JPEG q95 with no chroma subsampling is visually
        # indistinguishable here, is what CD Baby and Apple both expect, and
        # cuts the payload by about 60%.
        ext = "jpg"
        for old in album.glob("COVER.*"):
            old.unlink()
        dest = album / f"COVER.{ext}"
        if ext == "jpg":
            out.save(dest, "JPEG", quality=95, dpi=DPI, subsampling=0)
        else:
            out.save(dest, "PNG", dpi=DPI, optimize=True)

    size_mb = dest.stat().st_size / 2 ** 20
    print(f"  installed {dest.relative_to(REPO)} at {target}x{target}, 300 DPI, {size_mb:.1f}MB")
    if size_mb > 25:
        print("    WARNING: over CD Baby's 25MB limit", file=sys.stderr)
    return True


def check():
    problems = 0
    print(f"  {'ALBUM':16s} {'SIZE':12s} {'MODE':6s} {'FORMAT':7s} STATUS")
    for album in album_dirs():
        cover = find_cover(album)
        if cover is None:
            print(f"  {album.name:16s} {'-':12s} {'-':6s} {'-':7s} NO COVER")
            problems += 1
            continue
        (w, h), mode, fmt = describe(cover)
        if w != h:
            status, bad = "NOT SQUARE", True
        elif w < CDBABY_MIN:
            status, bad = f"below CD Baby minimum ({CDBABY_MIN})", True
        elif w < TARGET:
            status, bad = f"distributable, under target ({TARGET})", True
        else:
            status, bad = "ok", False
        problems += bad
        print(f"  {album.name:16s} {f'{w}x{h}':12s} {mode:6s} {fmt:7s} {status}")
    print(f"\n  {problems} album(s) below the {TARGET}px target" if problems
          else f"\n  every cover is {TARGET}x{TARGET}")
    return problems


def fix_all():
    fixed = 0
    for album in album_dirs():
        cover = find_cover(album)
        if cover is None:
            print(f"{album.name}: no cover to fix")
            continue
        (w, h), mode, fmt = describe(cover)
        # Nothing to do only when size, format and colour mode are all right --
        # checking dimensions alone silently skips a cover that is the correct
        # size but the wrong format.
        if w == h == TARGET and fmt == "JPEG" and mode == "RGB":
            continue
        print(f"{album.name}:")
        # Resize in place, from the album's current art.
        tmp = album / f".cover-src{cover.suffix}"
        cover.replace(tmp)
        ok = install(album, tmp, TARGET)
        tmp.unlink(missing_ok=True)
        fixed += bool(ok)
    print(f"\n{fixed} cover(s) resized to {TARGET}x{TARGET}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("album", nargs="?")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fix-all", action="store_true")
    ap.add_argument("--target", type=int, default=TARGET)
    args = ap.parse_args()

    if args.check:
        check(); return 0
    if args.fix_all:
        return fix_all()
    if not (args.album and args.source):
        ap.print_help(); return 2

    album = REPO / args.album
    if not album.is_dir():
        print(f"error: no album '{args.album}'", file=sys.stderr); return 1
    src = Path(args.source).expanduser()
    if not src.is_file():
        print(f"error: no such image: {src}", file=sys.stderr); return 1
    print(f"{args.album}:")
    return 0 if install(album, src, args.target) else 1


if __name__ == "__main__":
    sys.exit(main())
