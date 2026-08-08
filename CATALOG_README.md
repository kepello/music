# How this repository works

Short version: **git holds words, the GitHub Release holds audio, your Mac holds the masters.**

```
~/Music/Masters/<Album>/*.wav        WAV masters -- source of truth, never in git
        |
        |  ./scripts/sync-album.sh <Album>
        v
  encode MP3 + M4A  ->  uploaded to the "latest" GitHub Release
  song folders + README.md / LYRICS.txt stubs scaffolded into this repo
        |
        |  git push
        v
  Build Catalog action  ->  regenerates catalog.json + playlists
        |
        v
  kepello.github.io/Musicplayer fetches catalog.json at runtime (no deploy needed)
```

## Adding a new album

1. Put the finished WAVs in `~/Music/Masters/<Album>/` — one file per song, named
   the way you want the song to be identified (`Hope.wav` → song folder `Hope`).
2. Run `./scripts/sync-album.sh <Album>`. It encodes, uploads the audio to the
   release, creates each song folder, and drops `README.md` / `LYRICS.txt` stubs.
3. Fill in the stubs — the story and the lyrics. **This is the only part that is
   actually yours to do.**
4. Open `<Album>/ALBUM.json`, put the tracks in the real running order, and paste
   in the Spotify / Apple / Amazon links once CD Baby has distributed it.
5. `git add . && git commit && git push`. The site updates itself.

Useful flags: `--all` to sweep every album, `-n` / `--dry-run` to see what it
would do without touching anything.

## ALBUM.json

One per album folder. Everything in it is optional; it exists so that adding an
album never means editing Python.

```json
{
  "title": "Overtones",
  "released": "2026-01-15",
  "streaming": {
    "spotify": "https://open.spotify.com/album/...",
    "appleMusic": "https://music.apple.com/...",
    "amazonMusic": "https://music.amazon.com/albums/..."
  },
  "tracks": ["Love", "Bow", "Dove"],
  "trackStreaming": {
    "Love": { "spotify": "https://open.spotify.com/track/..." }
  }
}
```

- `tracks` is the running order. Position in this list becomes `trackNumber`.
- A song on disk but missing from `tracks` still appears — appended at the end,
  with a note in the action log — so nothing silently vanishes.
- A name in `tracks` with no matching folder is skipped with a warning.
- Empty link strings are dropped, so unfilled placeholders never render.

## catalog.json

Generated — never edit it by hand. `scripts/generate-catalog.py` walks the album
folders and writes it, along with the `-MP3.m3u8` / `-M4A.m3u8` playlists.

A song folder counts as a track when it contains a `README.md` or a `LYRICS.txt`.
Discovery is driven by text, not audio, because no audio is present in a CI
checkout.

Per track: `name`, `title`, `trackNumber`, `path`, `readme`, `cover`, `mp3`,
`m4a`, `lyrics`, `streaming`.
Per collection: `name`, `title`, `path`, `readme`, `cover`, `released`,
`streaming`, `playlistM4A`, `playlistMP3`, `tracks`.

The `title` comes from the first `_underscored_` line of the song's `README.md`.

## Conventions worth keeping

- **Nothing deletes release assets.** The action only regenerates text. Audio is
  uploaded additively by `sync-album.sh` with `--clobber`. An earlier version of
  the workflow deleted and recreated the whole release on every push; that is
  gone, deliberately.
- **The masters only exist on your Mac.** `~/Music/Masters/` is not backed up by
  this repo. Back it up somewhere.
- CD Baby never asks for lyrics or descriptions, which is exactly why this repo
  is the canonical home for them.
