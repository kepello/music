# Music Catalog JSON Format

## Overview

To avoid GitHub API rate limiting, the music repository should include a `catalog.json` file in its root directory. This file provides a complete snapshot of the music library structure, eliminating the need for the app to make repeated API calls to traverse the repository.

## Structure

The music library has a simple three-level hierarchy:

**Library (Root)** → **Collections (Albums)** → **Tracks**

- **Library**: The root level with optional cover image and README
- **Collections**: Albums/folders containing tracks, each with a cover image and README
- **Tracks**: Individual audio files within collections

Note: Collections and albums are the same thing - collections ARE albums.

## File Location

The catalog file should be placed at the root of the music repository:

```
https://raw.githubusercontent.com/{owner}/{repo}/main/catalog.json
```

For the current app configuration:

```
https://raw.githubusercontent.com/kepello/music/main/catalog.json
```

## JSON Schema

ver": "cover.jpg",
"readme": "# My Music Library\n\nWelcome to my music collection...",
"co

### Root Structure

```json
{
  "version": "1.0",
  "generatedAt": "2026-01-29T12:00:00Z",
  "repository": {
    "owner": "kepello",
    "repo": "music",
    "branch": "main"
  },
  "collections": []
}
```

### Complete Example

```json
{
  "version": "1.0",
  "generatedAt": "2026-03-09T12:00:00Z",
  "repository": {
    "owner": "kepello",
    "repo": "music",
    "branch": "main"
  },
  "cover": "COVER.jpg",
  "readme": "# My Music Library\n\nWelcome to my music collection...",
  "collections": [
    {
      "name": "Overtones",
      "path": "Overtones",
      "readme": "# Overtones\n\nScripture-based songs...",
      "cover": "Overtones/COVER.png",
      "zipM4A": "https://github.com/kepello/music/releases/download/latest/Overtones-M4A.zip",
      "zipMP3": "https://github.com/kepello/music/releases/download/latest/Overtones-MP3.zip",
      "zipWAV": "https://github.com/kepello/music/releases/download/latest/Overtones-WAV.zip",
      "playlistM4A": "Overtones/Overtones-M4A.m3u8",
      "playlistMP3": "Overtones/Overtones-MP3.m3u8",
      "playlistWAV": "Overtones/Overtones-WAV.m3u8",
      "tracks": [
        {
          "name": "Anxious",
          "title": "Stop Being Anxious",
          "trackNumber": 16,
          "path": "Overtones/Anxious",
          "readme": "_Stop Being Anxious_\n\nThis was one of the first songs...",
          "mp3": "https://github.com/kepello/music/releases/download/latest/Anxious.mp3",
          "m4a": "https://github.com/kepello/music/releases/download/latest/Anxious.m4a",
          "wav": "Overtones/Anxious/Anxious.wav",
          "lyrics": "Stop being anxious\n\nStop being anxious about your lives..."
        },
        {
          "name": "Voice",
          "title": "He Hears My Voice",
          "trackNumber": 19,
          "path": "Overtones/Voice",
          "readme": "_He Hears My Voice_\n\nThis song was created as a gift...",
          "mp3": "https://github.com/kepello/music/releases/download/latest/Voice.mp3",
          "m4a": "https://github.com/kepello/music/releases/download/latest/Voice.m4a",
          "wav": "Overtones/Voice/Voice.wav",
          "lyrics": "I love Jehovah, for he hears my voice..."
        }
      ]
    }
  ]
}
```

## Data Structure Details

### Library Object (Top Level)

| Field               | Type        | Required | Description                                           |
| ------------------- | ----------- | -------- | ----------------------------------------------------- |
| `version`           | string      | Yes      | Schema version (currently "1.0")                      |
| `generatedAt`       | string      | Yes      | ISO 8601 timestamp of when catalog was generated      |
| `repository`        | object      | Yes      | Repository information                                |
| `repository.owner`  | string      | Yes      | GitHub repository owner                               |
| `repository.repo`   | string      | Yes      | GitHub repository name                                |
| `repository.branch` | string      | Yes      | Branch name (typically "main")                        |
| `cover`             | string      | No       | Relative path to library cover image                  |
| `readme`            | string      | No       | Full markdown content of library README.md            |
| `collections`       | array       | Yes      | Array of collection (album) objects                   |

### Collection Object

Collections and albums are the same thing. Each collection is an album containing tracks.

| Field         | Type   | Required | Description                                                                 |
| ------------- | ------ | -------- | --------------------------------------------------------------------------- |
| `name`        | string | Yes      | Folder name (display name)                                                  |
| `path`        | string | Yes      | Relative path from repository root                                          |
| `readme`      | string | No       | Full markdown content of README.md if exists                                |
| `cover`       | string | No       | Relative path to cover image                                                |
| `zipM4A`      | string | No       | Full URL to M4A album ZIP in GitHub Releases                                |
| `zipMP3`      | string | No       | Full URL to MP3 album ZIP in GitHub Releases                                |
| `zipWAV`      | string | No       | Full URL to WAV album ZIP in GitHub Releases                                |
| `playlistM4A` | string | No       | Relative path to M4A format M3U8 playlist (for streaming)                   |
| `playlistMP3` | string | No       | Relative path to MP3 format M3U8 playlist (for streaming)                   |
| `playlistWAV` | string | No       | Relative path to WAV format M3U8 playlist (for streaming)                   |
| `tracks`      | array  | Yes      | Array of track objects                                                      |

### Track Object

Represents an individual track folder.

| Field         | Type   | Required | Description                                                  |
| ------------- | ------ | -------- | ------------------------------------------------------------ |
| `name`        | string | Yes      | Folder name (unique identifier)                              |
| `title`       | string | No       | Display title extracted from README.md (text between \_\_)   |
| `trackNumber` | number | No       | Track sequence number within the collection                  |
| `path`        | string | Yes      | Relative path from repository root                           |
| `readme`      | string | No       | Full markdown content of README.md if exists                 |
| `mp3`         | string | No       | Full URL to MP3 file in GitHub Releases                      |
| `m4a`         | string | No       | Full URL to M4A file in GitHub Releases                      |
| `wav`         | string | No       | Relative path to WAV file (master source, stored in git)     |
| `lyrics`      | string | No       | Full text content of lyrics file                             |

## Download Options

The catalog supports multiple download strategies for different use cases:

### Individual Track Downloads

Users can download individual tracks in three formats:

- **MP3**: `https://github.com/{owner}/{repo}/releases/download/latest/{trackName}.mp3`
- **M4A**: `https://github.com/{owner}/{repo}/releases/download/latest/{trackName}.m4a`
- **WAV**: `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{relativePath}`

MP3 and M4A files are distributed via GitHub Releases for fast CDN delivery. WAV files are stored in the git repository as master source files and accessed via raw.githubusercontent.com URLs.

### Album ZIP Downloads

Users can download complete albums as ZIP packages in three formats:

- **MP3 ZIP**: Includes all MP3 tracks + local M3U8 playlist (for offline playback)
- **M4A ZIP**: Includes all M4A tracks + local M3U8 playlist (for offline playback)
- **WAV ZIP**: Includes all WAV tracks + local M3U8 playlist (for offline playback)

Each ZIP package contains a playlist file with relative paths, allowing users to double-click the playlist after extraction to play the entire album in their preferred media player.

ZIP URLs are available in the collection object:
- `zipMP3`: Full URL to GitHub Releases
- `zipM4A`: Full URL to GitHub Releases
- `zipWAV`: Full URL to GitHub Releases

### Streaming Playlists

For streaming playback without downloading, the catalog includes M3U8 playlists:

- **playlistMP3**: M3U8 file with URLs to MP3 files in GitHub Releases
- **playlistM4A**: M3U8 file with URLs to M4A files in GitHub Releases
- **playlistWAV**: M3U8 file with URLs to WAV files in git repository

Playlist files are stored in the git repository at relative paths specified in the collection object.

### URL Construction

When implementing the player app, construct URLs based on file type:

```typescript
// MP3 and M4A - use GitHub Releases
const mp3Url = track.mp3; // Already full URL
const m4aUrl = track.m4a; // Already full URL

// WAV - construct from repository info and relative path
const wavUrl = `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${track.wav}`;

// ZIP packages - use directly
const zipUrl = collection.zipMP3; // Already full URL

// Streaming playlists - construct from repository info
const playlistUrl = `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${collection.playlistMP3}`;
```

## Important Notes

### 1. URL Strategies

The catalog uses different URL strategies based on file type:

**MP3 and M4A files** - Full URLs to GitHub Releases:
```
https://github.com/{owner}/{repo}/releases/download/latest/{filename}
```

**WAV files and other repository content** - Relative paths, construct URLs with:
```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
```

This separation allows:
- Fast CDN delivery for converted files (MP3/M4A)
- Version control for master source files (WAV)
- Smaller git repository size (no binary commits for generated files)

### 2. Optional Fields

Fields marked as "No" in the Required column can be `null` or omitted if the file doesn't exist. This is especially important for:

- README files (not all folders have them)
- Cover images (not all collections/albums have them)
- Lyrics files (most tracks don't have them)
- M4A files (some tracks may only have MP3)
- ZIP/Playlist files (only exist at album level)

### 3. README Content

README content should be stored as the full markdown text, not as a file path. The app will:

- Strip HTML comments from the markdown before display
- Render it using a markdown parser
- Display it in the respective views

### 4. Hierarchical Structure

The library uses a simple hierarchy:

**Library → Collection (Album) → Track**

```
Library (root)
└─ Overtones/ (Collection/Album)
    ├─ Love/ (Track)
    ├─ Anxious/ (Track)
    └─ Voice/ (Track)
```

Collections ARE albums. There is no nested album structure - each collection directly contains tracks.

### 5. Cover Images

Cover images are flexible:
- Must start with "cover" (case-insensitive)
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- No size restrictions (previously required 800×800, now any reasonable size)

### 6. File Naming Patterns

The catalog generation script looks for files following these patterns:

**Collection/Album-level files:**
- ZIP: `{collection-name}-M4A.zip`, `{collection-name}-MP3.zip`, `{collection-name}-WAV.zip`
- Playlists: `{collection-name}-M4A.m3u8`, `{collection-name}-MP3.m3u8`, `{collection-name}-WAV.m3u8`

**Track-level files:**
- Audio: `{track-name}.mp3`, `{track-name}.m4a`, `{track-name}.wav`
- Lyrics: `LYRICS.txt`

**Cover images:**
- Library: `COVER.jpg` (or any cover.* at repository root)
- Collections: `{collection-name}/COVER.jpg`

### 7. Generation Timestamp

The `generatedAt` timestamp allows the app to:
- Display when the catalog was last updated
- Optionally cache the catalog with an expiration policy

## Catalog Generation

To generate or update the catalog, run:
git add catalog.json
git commit -m "Update catalog"
git push
```

The generation script should:

1. Traverse all directories in the repository
## Catalog Generation

To generate or update the catalog, run:

```bash
```bashautomatically:

1. Traverses all directories in the repository
2. Reads README.md files and extracts friendly titles from `_Title_` format
3. Finds all audio files, cover images, and lyrics files
4. Constructs full URLs for MP3/M4A files in GitHub Releases
5. Uses relative paths for WAV files in git repository
6. Builds the JSON structure according to this schema
7. Writes to `catalog.json` in the repository root

## Integration with App

Once the catalog file exists, the app should:

1. Fetch the catalog once at startup:

```typescript
const response = await fetch(
  "https://raw.githubusercontent.com/kepello/music/main/catalog.json",
);
const catalog = await response.json();
```

2. Cache the catalog in memory or localStorage

3. Use the catalog data directly instead of making GitHub API calls

4. Construct file URLs based on file type (see Download Options section above)
```

5. Optionally refresh the catalog periodically (e.g., once per session or once per day)

## Benefits

✅ **Eliminates Rate Limiting**: Single API call instead of hundreds  
✅ **Faster Loading**: No need to traverse directories recursively  
✅ **Offline Capable**: Catalog can be cached indefinitely  
✅ **Predictable**: No API failures or timeouts  
✅ **Scalable**: Works with any repository size

## Versioning

The `version` field allows for future schema changes. If the schema needs to be updated:

- Increment the version number (e.g., "1.1", "2.0")
- Document changes in this README
- Update generation scripts and app code accordingly
- Consider supporting multiple versions for backward compatibility

✅ **Simple Structure**: Library → Collections (Albums) → Tracks