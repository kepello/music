# Music Catalog JSON Format

## Overview

To avoid GitHub API rate limiting, the music repository should include a `catalog.json` file in its root directory. This file provides a complete snapshot of the music library structure, eliminating the need for the app to make repeated API calls to traverse the repository.

## Structure

The music library has a simple three-level hierarchy:

**Library (Root)** → **Collections (Albums)** → **Tracks**

- **Library**: The root level with optional cover image (800×800) and README
- **Collections**: Albums/folders containing tracks, each with a cover image (800×800) and README
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
  "generatedAt": "2026-01-29T12:00:00Z",
  "repository": {
    "owner": "kepello",
    "repo": "music",
    "ver": "cover.jpg",
  "readme": "# My Music Library\n\nWelcome to my music collection...",
  "collections": [
    {
      "name": "Beethoven-Symphony-No-9",
      "path": "Beethoven-Symphony-No-9",
      "readme": "# Symphony No. 9\n\nBeethoven's final symphony...",
      "cover": "Beethoven-Symphony-No-9/cover.jpg",
      "zipM4A": "Beethoven-Symphony-No-9/Beethoven-Symphony-No-9-m4a.zip",
      "zipMP3": "Beethoven-Symphony-No-9/Beethoven-Symphony-No-9-mp3.zip",
      "playlistM4A": "Beethoven-Symphony-No-9/Beethoven-Symphony-No-9-m4a.m3u8",
      "playlistMP3": "Beethoven-Symphony-No-9/Beethoven-Symphony-No-9-mp3.m3u8",
      "tracks": [
        {
          "name": "01-Allegro-ma-non-troppo",
          "path": "Beethoven-Symphony-No-9/01-Allegro-ma-non-troppo",
          "readme": "# Allegro ma non troppo, un poco maestoso\n\nThe first movement...",
          "mp3": "Beethoven-Symphony-No-9/01-Allegro-ma-non-troppo/track.mp3",
          "m4a": "Beethoven-Symphony-No-9/01-Allegro-ma-non-troppo/track.m4a",
          "playlist": "Beethoven-Symphony-No-9/01-Allegro-ma-non-troppo/01-Allegro-ma-non-troppo.m3u8",
          "lyrics": "Beethoven-Symphony-No-9/01-Allegro-ma-non-troppo/lyrics.txt"
        },
        {
          "name": "02-Molto-vivace",
          "path": "Beethoven-Symphony-No-9/02-Molto-vivace",
          "readme": "# Molto vivace\n\nThe scherzo movement...",
          "mp3": "Beethoven-Symphony-No-9/02-Molto-vivace/track.mp3",
          "m4a": "Beethoven-Symphony-No-9/02-Molto-vivace/track.m4a",
          "playlist": "Beethoven-Symphony-No-9/02-Molto-vivace/02-Molto-vivace.m3u8",
          "lyrics": null
        }
      ]
    },
    {
      "name": "Take-Five",
      "path": "Take-Five",
      "readme": "# Take Five\n\nDave Brubeck's iconic composition...",
      "cover": "Take-Five/cover.jpg",
      "zipM4A": "Take-Five/Take-Five-m4a.zip",
      "zipMP3": "Take-Five/Take-Five-mp3.zip",
      "playlistM4A": "Take-Five/Take-Five-m4a.m3u8",
      "playlistMP3": "Take-Five/Take-Five-mp3.m3u8",
      "tracks": [
        {
          "name": "Take-Five",
          "path": "Take-Five/Take-Five",
          "readme": "# Take Five\n\nIconic jazz composition...",
          "mp3": "Take-Five/Take-Five/track.mp3",
          "m4a": "Take-Five/Take-Five/track.m4a",
          "playlist": "Take-Five-Five/track.mp3",
          "m4a": "Jazz/Take-Five/track.m4a",
          "playlist": "Jazz/Take-Five/Take-Five.m3u8",
          "lyrics": null
        }
      ]
    }
  ]
}
```

## Data Structure Details

### Top Level

| Field | Typ (Library Root)

| Field               | Type        | Required | Description                                           |
| ------------------- | ----------- | -------- | ----------------------------------------------------- |
| `version`           | string      | Yes      | Schema version (currently "1.0")                      |
| `generatedAt`       | string      | Yes      | ISO 8601 timestamp of when catalog was generated      |
| `repository`        | object      | Yes      | Repository information                                |
| `repository.owner`  | string      | Yes      | GitHub repository owner                               |
| `repository.repo`   | string      | Yes      | GitHub repository name                                |
| `repository.branch` | string      | Yes      | Branch name (typically "main")                        |
| `cover`             | string      | No       | Relative path to library cover image (800×800 pixels) |
| `readme`            | string      | No       | Full markdown content of library README.md            |
| `collections`       | arr (Album) |

Collections and albums are the same thing. Each collection is an album containing tracks.

| Field         | Type   | Required | Description                                    |
| ------------- | ------ | -------- | ---------------------------------------------- |
| `name`        | string | Yes      | Folder name (display name)                     |
| `path`        | string | Yes      | Relative path from repository root             |
| `readme`      | string | No       | Full markdown content of README.md if exists   |
| `cover`       | string | No       | Relative path to cover image (800×800 pixels)  |
| `zipM4A`      | string | No       | Relative path to M4A format ZIP file           |
| `zipMP3`      | string | No       | Relative path to MP3 format ZIP file           |
| `playlistM4A` | string | No       | Relative path to M4A format M3U8 playlist file |
| `playlistMP3` | string | No       | Relative path to MP3 format M3U8 playlist file |
| `tracks`      | array  | Yes      | Array of track objects                         |

### Track Object

Represents an individual track folder.

| Field      | Type   | Required | Description                                  |
| ---------- | ------ | -------- | -------------------------------------------- |
| `name`     | string | Yes      | Folder name (display name)                   |
| `path`     | string | Yes      | Relative path from repository root           |
| `readme`   | string | No       | Full markdown content of README.md if exists |
| `mp3`      | string | No       | Relative path to MP3 audio file              |
| `m4a`      | string | No       | Relative path to M4A audio file              |
| `playlist` | string | No       | Relative path to M3U8 playlist file          |
| `lyrics`   | string | No       | Relative path to lyrics text file            |

## Important Notes

### 1. All Paths Are Relative

All file paths in the catalog should be relative to the repository root. The app will construct full URLs using:

```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
```

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

The catalog supports two structures:

**Three-level hierarchy** (Collection → Album → Track):

```
Classical/
  └─ Beethoven-Symphony-No-9/
      └─ 01-Allegro-ma-non-troppo/
```

**Two-level hierarchy** (Collection → Track):

````
Jazz/
  └─ Take-Five/
```uses a simple three-level hierarchy:

**Library → Collection (Album) → Track**:
````

Library (root)
└─ Beethoven-Symphony-No-9/ (Collection/Album)
└─ 01-Allegro-ma-non-troppo/ (Track)
└─ 02-Molto-vivace/ (Track)

```

Collections ARE albums. There is no nested album structure - each collection directly contains tracks

**Cover images:**
- Must start with "cover" (case-insensitive)
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`

### 6. Generation Timestamp

The `generatedAt` timestamp allows the app to:
- Display when the catalog was last updated
- Optionally cache the catalog with an expiration policy
- Collection/Album-level files:**
- ZIP: `{collection-name}-m4a.zip` and `{collection-name}-mp3.zip`
- Playlists: `{collection-name}-m4a.m3u8` and `{collection-name}-mp3.m3u8`

**Track-level files:**
- Audio: Any name ending in `.mp3` or `.m4a`
- Playlist: `{track-name}.m3u8`
- Lyrics: Any name ending in `.txt`

**Cover images:**
- Library: `cover.jpg` at repository root (800×800 pixels)
- Collections: `{collection-name}/cover.jpg` (800×800 pixels)
- All images should be 800×800 pixels for optimal display and file size
git add catalog.json
git commit -m "Update catalog"
git push
```

The generation script should:

1. Traverse all directories in the repository
2. Read README.md files and store their content
3. Find all audio files, cover images, and supplementary files
4. Build the JSON structure according to this schema
5. Write to `catalog.json` in the repository root

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

4. Construct file URLs using the pattern:

```typescript
function getRawFileUrl(path: string): string {
  return `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/${path}`;
}
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
✅ **Optimized Images**: All cover images are 800×800 pixels
