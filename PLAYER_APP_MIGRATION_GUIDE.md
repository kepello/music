# Player App Migration Guide: Catalog Schema v1.0 Updates

## Overview

This document outlines all breaking changes and new features introduced to the music catalog schema. The player app requires significant updates to handle new fields, URL strategies, and download options.

**Migration Priority:** HIGH - The catalog schema has changed substantially. The player app will not function correctly without these updates.

---

## Summary of Changes

### 🔴 Breaking Changes
1. **Track URLs changed from relative paths to full URLs** for MP3/M4A files
2. **Lyrics field changed from file path to full text content**
3. **WAV files strategy**: Master source in git (relative paths), MP3/M4A in releases (full URLs)

### 🟢 New Features
1. **Track titles**: Friendly display names extracted from README files
2. **Track numbering**: Sequential ordering within collections
3. **WAV support**: Master quality audio files now available
4. **Album ZIPs**: Download entire albums in MP3, M4A, or WAV formats with local playlists
5. **Multiple download options**: Individual files + complete albums

### 🟡 Relaxed Requirements
1. **Cover image size**: No longer requires 800×800px (any reasonable size accepted)

---

## Detailed Changes

### 1. Track Object: New Fields

#### `title` (string, optional)
**Purpose:** Friendly display name for tracks

**Example:**
```json
{
  "name": "Anxious",
  "title": "Stop Being Anxious"
}
```

**Extraction:** Extracted from README.md first line in format `_Title Here_`

**Player Implementation:**
- Display `title` if available, fallback to `name`
- Use in track lists, now playing UI, notifications
- Don't modify the `name` field (still used as unique identifier)

```typescript
function getTrackDisplayName(track: Track): string {
  return track.title || track.name;
}
```

---

#### `trackNumber` (number, optional)
**Purpose:** Sequential ordering within collections

**Example:**
```json
{
  "name": "Voice",
  "trackNumber": 19
}
```

**Player Implementation:**
- Sort tracks by `trackNumber` when displaying album track lists
- Show track numbers in UI (e.g., "19. He Hears My Voice")
- Use for next/previous navigation

```typescript
// Sort tracks by trackNumber
const sortedTracks = collection.tracks.sort((a, b) => 
  (a.trackNumber || 0) - (b.trackNumber || 0)
);
```

**Note:** Not all collections have track numbers. When missing, maintain order from catalog array.

---

#### `wav` (string, optional)
**Purpose:** Path to master quality WAV audio file

**Example:**
```json
{
  "wav": "Overtones/Anxious/Anxious.wav"
}
```

**URL Construction:**
```typescript
const wavUrl = `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${track.wav}`;
```

**Player Implementation:**
- Add WAV as third audio format option alongside MP3/M4A
- Allow users to choose preferred format in settings
- Use for audiophile/archival quality playback
- Support WAV downloads (see Download Options section)

---

### 2. Track Object: Changed Fields

#### `mp3` and `m4a` (string, optional)
**BREAKING CHANGE:** Now contains full URLs instead of relative paths

**Before:**
```json
{
  "mp3": "Overtones/Anxious/Anxious.mp3"
}
```

**After:**
```json
{
  "mp3": "https://github.com/kepello/music/releases/download/latest/Anxious.mp3"
}
```

**Player Implementation:**
- Use URLs directly - no construction needed
- Files served from GitHub Releases (CDN)
- Faster loading than raw.githubusercontent.com
- Update TypeScript types to reflect full URLs

**Migration Code:**
```typescript
// OLD - DO NOT USE
const mp3Url = `https://raw.githubusercontent.com/.../${track.mp3}`;

// NEW - Use directly
const mp3Url = track.mp3; // Already full URL
```

---

#### `lyrics` (string, optional)
**BREAKING CHANGE:** Now contains full text content instead of file path

**Before:**
```json
{
  "lyrics": "Overtones/Anxious/LYRICS.txt"
}
```

**After:**
```json
{
  "lyrics": "Stop being anxious\n\nStop being anxious about your lives..."
}
```

**Player Implementation:**
- Display lyrics directly from field
- No need to fetch external file
- Better offline support
- Render with proper line breaks (`\n`)

**Migration Code:**
```typescript
// OLD - DO NOT USE
const lyrics = await fetch(lyricsUrl).then(r => r.text());

// NEW - Use directly
const lyrics = track.lyrics; // Already full text
```

---

### 3. Collection Object: New Fields

#### `zipWAV` (string, optional)
**Purpose:** URL to complete album ZIP in WAV format

**Example:**
```json
{
  "zipWAV": "https://github.com/kepello/music/releases/download/latest/Overtones-WAV.zip"
}
```

**ZIP Contents:**
- All WAV files for the album
- Local M3U8 playlist with relative paths
- Allows offline double-click playback after extraction

**Player Implementation:**
- Add "Download Album (WAV)" option
- Show file size estimate (~10-50MB per track)
- Mention playlist included for offline use

---

#### `zipMP3` and `zipM4A` (string, optional)
**Purpose:** URLs to complete album ZIPs in MP3/M4A formats

**Example:**
```json
{
  "zipMP3": "https://github.com/kepello/music/releases/download/latest/Overtones-MP3.zip",
  "zipM4A": "https://github.com/kepello/music/releases/download/latest/Overtones-M4A.zip"
}
```

**ZIP Contents:**
- All MP3 or M4A files for the album
- Local M3U8 playlist with relative paths
- Smaller than WAV (~5-15MB per track)

**Player Implementation:**
- Add "Download Album" button with format selector
- Three options: MP3, M4A, WAV
- Inform users about included playlists

---

#### `playlistWAV` (string, optional)
**Purpose:** Streaming playlist for WAV files

**Example:**
```json
{
  "playlistWAV": "Overtones/Overtones-WAV.m3u8"
}
```

**Player Implementation:**
- Add WAV streaming option
- Warn about bandwidth usage (high quality)
- Construct URL: `https://raw.githubusercontent.com/.../Overtones-WAV.m3u8`

---

### 4. Download Options

The catalog now supports comprehensive download functionality:

#### Individual Track Downloads

Users can download individual tracks in three formats:

```typescript
interface DownloadOptions {
  mp3: string;  // Full URL to GitHub Releases
  m4a: string;  // Full URL to GitHub Releases
  wav: string;  // Construct from repository + relative path
}

function getTrackDownloadUrls(track: Track, catalog: Catalog): DownloadOptions {
  return {
    mp3: track.mp3,
    m4a: track.m4a,
    wav: `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${track.wav}`
  };
}
```

**UI Implementation:**
- Add download icon/button on each track
- Show format picker (MP3, M4A, WAV)
- Display file size estimates:
  - MP3: ~5-10MB
  - M4A: ~5-10MB
  - WAV: ~30-50MB

---

#### Album ZIP Downloads

Users can download complete albums:

```typescript
interface AlbumDownloadOptions {
  zipMP3: string;  // Full URL
  zipM4A: string;  // Full URL
  zipWAV: string;  // Full URL
}

function getAlbumDownloadUrls(collection: Collection): AlbumDownloadOptions {
  return {
    zipMP3: collection.zipMP3,
    zipM4A: collection.zipM4A,
    zipWAV: collection.zipWAV
  };
}
```

**UI Implementation:**
- Add "Download Album" button on album view
- Format selector: MP3 / M4A / WAV
- Show total size estimate
- Mention: "Includes playlist for offline playback"

**User Flow:**
1. User clicks "Download Album"
2. Selects format (MP3/M4A/WAV)
3. Browser downloads ZIP file
4. User extracts ZIP
5. User double-clicks `.m3u8` playlist file
6. Media player opens and plays entire album

---

#### Streaming Playlists

Three streaming playlists per collection:

```typescript
interface StreamingPlaylists {
  playlistMP3: string;  // Relative path
  playlistM4A: string;  // Relative path
  playlistWAV: string;  // Relative path
}

function getPlaylistUrl(path: string, catalog: Catalog): string {
  return `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${path}`;
}
```

**UI Implementation:**
- Add "Play Album" button with format selector
- Support loading M3U8 playlists in built-in player
- Allow users to choose default streaming quality in settings

---

### 5. URL Construction Strategies

**IMPORTANT:** Different files use different URL strategies

#### Files in GitHub Releases (Full URLs provided)
- MP3 files: `track.mp3` ✅ Use directly
- M4A files: `track.m4a` ✅ Use directly
- Album ZIPs: `collection.zipMP3`, `collection.zipM4A`, `collection.zipWAV` ✅ Use directly

#### Files in Git Repository (Relative paths provided)
- WAV files: `track.wav` ⚠️ Construct URL
- Playlists: `collection.playlistMP3`, etc. ⚠️ Construct URL
- Cover images: `collection.cover` ⚠️ Construct URL
- README files: Already full text in catalog

**Construction Pattern:**
```typescript
function constructGitUrl(relativePath: string, catalog: Catalog): string {
  return `https://raw.githubusercontent.com/${catalog.repository.owner}/${catalog.repository.repo}/${catalog.repository.branch}/${relativePath}`;
}

// Usage
const wavUrl = constructGitUrl(track.wav, catalog);
const coverUrl = constructGitUrl(collection.cover, catalog);
const playlistUrl = constructGitUrl(collection.playlistMP3, catalog);
```

---

## TypeScript Type Updates

Update your type definitions:

```typescript
interface Repository {
  owner: string;
  repo: string;
  branch: string;
}

interface Track {
  name: string;
  title?: string;              // NEW: Friendly display name
  trackNumber?: number;        // NEW: Sequential order
  path: string;
  readme?: string;
  cover?: string;
  mp3?: string;                // CHANGED: Now full URL
  m4a?: string;                // CHANGED: Now full URL
  wav?: string;                // NEW: Relative path to WAV file
  lyrics?: string;             // CHANGED: Now full text content
}

interface Collection {
  name: string;
  path: string;
  readme?: string;
  cover?: string;
  zipMP3?: string;             // NEW: Full URL to MP3 album ZIP
  zipM4A?: string;             // NEW: Full URL to M4A album ZIP
  zipWAV?: string;             // NEW: Full URL to WAV album ZIP
  playlistMP3?: string;        // Relative path
  playlistM4A?: string;        // Relative path
  playlistWAV?: string;        // NEW: Relative path to WAV playlist
  tracks: Track[];
}

interface Catalog {
  version: string;
  generatedAt: string;
  repository: Repository;
  cover?: string;
  readme?: string;
  collections: Collection[];
}
```

---

## Migration Checklist

### Phase 1: Type Updates
- [ ] Update TypeScript interfaces with new fields
- [ ] Add optional chaining for all new optional fields
- [ ] Update mock/test data with new structure

### Phase 2: Track Display
- [ ] Update track list UI to use `title` field (fallback to `name`)
- [ ] Add track number display when available
- [ ] Sort tracks by `trackNumber` in album views

### Phase 3: Audio Playback
- [ ] Update MP3/M4A playback to use full URLs directly
- [ ] Add WAV playback support with URL construction
- [ ] Add format selector in settings (MP3/M4A/WAV preference)

### Phase 4: Lyrics Display
- [ ] Update lyrics viewer to render text directly from catalog
- [ ] Remove lyrics file fetching logic
- [ ] Handle line breaks properly (`\n`)

### Phase 5: Downloads (Individual Tracks)
- [ ] Add download button to track UI
- [ ] Implement format selector (MP3/M4A/WAV)
- [ ] Show file size estimates
- [ ] Use correct URL strategy per format

### Phase 6: Downloads (Album ZIPs)
- [ ] Add "Download Album" button to collection view
- [ ] Implement format selector (MP3/M4A/WAV)
- [ ] Show total size estimate
- [ ] Add note about included playlist

### Phase 7: Streaming Playlists
- [ ] Add "Play Album" functionality
- [ ] Support M3U8 playlist parsing
- [ ] Add format selector for streaming quality
- [ ] Construct URLs correctly for git-hosted playlists

### Phase 8: Cover Images
- [ ] Remove 800×800px size validation
- [ ] Handle varying cover sizes gracefully
- [ ] Continue using git URL construction for covers

### Phase 9: Testing
- [ ] Test with current catalog.json
- [ ] Verify all download options work
- [ ] Check WAV file playback
- [ ] Validate track ordering
- [ ] Test lyrics display
- [ ] Verify cover image loading

### Phase 10: Polish
- [ ] Update help/documentation in app
- [ ] Add tooltips for new features
- [ ] Optimize caching strategy
- [ ] Add format preference persistence

---

## Testing Examples

### Test Track: "Anxious" (Stop Being Anxious)

```json
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
}
```

**Verify:**
- Display shows "Stop Being Anxious" (not "Anxious")
- Track number 16 appears in UI
- MP3 URL works: `https://github.com/kepello/music/releases/download/latest/Anxious.mp3`
- WAV URL constructed: `https://raw.githubusercontent.com/kepello/music/main/Overtones/Anxious/Anxious.wav`
- Lyrics display directly without fetching

---

### Test Collection: "Overtones"

```json
{
  "name": "Overtones",
  "path": "Overtones",
  "zipMP3": "https://github.com/kepello/music/releases/download/latest/Overtones-MP3.zip",
  "zipM4A": "https://github.com/kepello/music/releases/download/latest/Overtones-M4A.zip",
  "zipWAV": "https://github.com/kepello/music/releases/download/latest/Overtones-WAV.zip",
  "playlistMP3": "Overtones/Overtones-MP3.m3u8",
  "playlistWAV": "Overtones/Overtones-WAV.m3u8",
  "tracks": [/* 19 tracks */]
}
```

**Verify:**
- Tracks sorted by trackNumber (1-19)
- All three ZIP download options work
- WAV playlist URL constructed correctly
- Album view shows proper track titles

---

## Common Pitfalls

### ❌ Don't construct URLs for MP3/M4A
```typescript
// WRONG
const url = `https://raw.githubusercontent.com/.../${track.mp3}`;
```

```typescript
// CORRECT
const url = track.mp3; // Already full URL
```

---

### ❌ Don't try to fetch lyrics as a file
```typescript
// WRONG
const lyricsUrl = constructUrl(track.lyrics);
const text = await fetch(lyricsUrl).then(r => r.text());
```

```typescript
// CORRECT
const text = track.lyrics; // Already full text
```

---

### ❌ Don't ignore track titles
```typescript
// POOR UX
<div>{track.name}</div>  // Shows "Anxious"
```

```typescript
// GOOD UX
<div>{track.title || track.name}</div>  // Shows "Stop Being Anxious"
```

---

### ❌ Don't use same URL strategy for all files
```typescript
// WRONG - Everything constructed
const mp3Url = constructUrl(track.mp3);  // Already full URL!
const wavUrl = constructUrl(track.wav);  // This one is correct
```

```typescript
// CORRECT - Different strategies
const mp3Url = track.mp3;               // Use directly
const wavUrl = constructUrl(track.wav); // Construct from path
```

---

## Backward Compatibility

**Note:** This is a breaking change. There is no backward compatibility with the old schema. The player app must be updated to work with the new catalog structure.

If you need to support old and new schemas simultaneously during migration:

```typescript
function isNewSchema(track: Track): boolean {
  // New schema has full URLs for mp3/m4a
  return track.mp3?.startsWith('http');
}

function getTrackUrl(track: Track, catalog: Catalog): string {
  if (isNewSchema(track)) {
    return track.mp3; // Use directly
  } else {
    // Old schema - construct URL
    return constructGitUrl(track.mp3, catalog);
  }
}
```

However, the current catalog is already using the new schema, so this is only needed if you're testing with old cached data.

---

## Questions or Issues?

If you encounter any issues during migration:

1. Check the current [catalog.json](https://raw.githubusercontent.com/kepello/music/main/catalog.json)
2. Review [CATALOG_README.md](CATALOG_README.md) for schema documentation
3. Test with a single track/collection first
4. Verify URL construction logic carefully

## Schema Version

This guide documents migration to **Catalog Schema v1.0**.

Current catalog version can be checked:
```typescript
console.log(catalog.version); // "1.0"
```

---

**Last Updated:** March 9, 2026
