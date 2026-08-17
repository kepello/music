#!/usr/bin/env python3
"""
Reflow song and album notes into Carl's own paragraph style.

    ./scripts/reflow-notes.py --preview <file>   # show before/after, change nothing
    ./scripts/reflow-notes.py --check            # report how fragmented each note is
    ./scripts/reflow-notes.py --apply [files]    # rewrite

Not a rewrite. No word is changed, added or removed -- only the line breaks
between sentences.

Notes assembled from ChatGPT conversations arrive with almost every sentence as
its own paragraph: 91% of paragraphs in the newer notes are a single line,
against a median of 11 words each. Carl's own writing, in the Overtones notes
that predate this workflow, runs a median of 40 words per paragraph. Same voice,
four times the density. TARGET_WORDS aims at his.

Two things are never merged:

  the _Title_ line, which the site reads the display title from

  quoted lyrics -- recognisable because their lines sit consecutively with no
  blank line between them, where prose fragments are each their own paragraph.
  Running them together would turn verse into a sentence.

A run of single-line paragraphs is joined until it reaches TARGET_WORDS, then a
new paragraph starts, so the result breathes at roughly the rhythm of his
earlier writing rather than becoming one slab.
"""

import argparse
import pathlib
import re
import statistics
import sys

REPO = pathlib.Path(__file__).parent.parent.resolve()
TARGET_WORDS = 45          # Overtones median is 40; a little over reads naturally

# Notes already at this density are Carl's own writing and are left untouched.
# Reflowing them merges thoughts he deliberately separated -- the first run
# collapsed a four-paragraph Overtones note into two.
ALREADY_FINE = 25
TITLE = re.compile(r"^_.+_$")


def blocks(text):
    """Split into (kind, lines) where kind is 'title', 'prose' or 'verse'."""
    out, cur = [], []
    for line in text.splitlines():
        if line.strip():
            cur.append(line.rstrip())
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)

    tagged = []
    for i, b in enumerate(out):
        if i == 0 and len(b) == 1 and TITLE.match(b[0].strip()):
            tagged.append(("title", b))
        elif len(b) == 1 and b[0].lstrip().startswith("<"):
            # An <img> for the cover is layout, not a sentence. Merging it into
            # the prose puts the album art inline mid-paragraph.
            tagged.append(("html", b))
        elif len(b) > 1:
            tagged.append(("verse", b))      # consecutive lines = quoted lyric
        else:
            tagged.append(("prose", b))
    return tagged


def reflow(text):
    tagged = blocks(text)
    out, run = [], []

    def flush():
        """Join the accumulated single-line paragraphs into full paragraphs."""
        if not run:
            return
        para, count = [], 0
        for sentence in run:
            para.append(sentence)
            count += len(sentence.split())
            if count >= TARGET_WORDS:
                out.append(" ".join(para)); para, count = [], 0
        if para:
            out.append(" ".join(para))
        run.clear()

    for i, (kind, b) in enumerate(tagged):
        nxt = tagged[i + 1][0] if i + 1 < len(tagged) else None
        if kind == "prose":
            # A line ending in a colon exists to introduce the quote beneath it;
            # swallowing it into the previous paragraph strands the colon
            # mid-sentence and leaves the verse looking unannounced.
            if b[0].rstrip().endswith(":") and nxt == "verse":
                flush()
                out.append(b[0])
            else:
                run.append(b[0])
        else:
            flush()
            out.append("\n".join(b) if kind == "verse" else b[0])
    flush()
    return "\n\n".join(out) + "\n"


def stats(text):
    ps = [b for k, b in blocks(text) if k != "title"]
    if not ps:
        return 0, 0, 0
    words = [sum(len(l.split()) for l in p) for p in ps]
    singles = sum(1 for p in ps if len(p) == 1)
    return len(ps), singles, statistics.median(words)


def note_files():
    return sorted(REPO.glob("*/*/README.md")) + sorted(REPO.glob("*/README.md"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", metavar="FILE")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", nargs="*", metavar="FILE")
    args = ap.parse_args()

    if args.preview:
        p = pathlib.Path(args.preview)
        before = p.read_text(encoding="utf-8")
        after = reflow(before)
        b, a = stats(before), stats(after)
        print(f"=== BEFORE  {b[0]} paragraphs, {b[1]} single-line, median {b[2]:.0f} words ===\n")
        print(before)
        print(f"\n=== AFTER   {a[0]} paragraphs, {a[1]} single-line, median {a[2]:.0f} words ===\n")
        print(after)
        return 0

    if args.check:
        print(f"  {'file':46s} {'paras':>5s} {'1-line':>6s} {'median':>6s}")
        for f in note_files():
            n, s, m = stats(f.read_text(encoding="utf-8"))
            if n:
                print(f"  {str(f.relative_to(REPO)):46s} {n:5d} {s:6d} {m:6.0f}")
        return 0

    if args.apply is not None:
        targets = [pathlib.Path(x) for x in args.apply] if args.apply else note_files()
        changed = 0
        skipped = []
        for f in targets:
            before = f.read_text(encoding="utf-8")
            n0, s0, m0 = stats(before)
            if m0 >= ALREADY_FINE:
                skipped.append((f, m0))
                continue
            after = reflow(before)
            if after != before:
                # No word may be lost: compare the word streams, not the layout.
                if before.split() != after.split():
                    print(f"  REFUSED {f}: word stream would change", file=sys.stderr)
                    continue
                f.write_text(after, encoding="utf-8")
                b, a = stats(before), stats(after)
                print(f"  {str(f.relative_to(REPO)):46s} {b[0]:3d} -> {a[0]:3d} paras, "
                      f"median {b[2]:.0f} -> {a[2]:.0f} words")
                changed += 1
        print(f"\n  {changed} file(s) reflowed, {len(skipped)} already in Carl's style and left alone")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
