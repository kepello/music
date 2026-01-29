#!/usr/bin/env python3
"""
Generate catalog.json for the music repository.

This script traverses the repository structure and generates a JSON catalog
following the schema defined in CATALOG_README.md.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def find_file_by_pattern(directory: Path, patterns: List[str]) -> Optional[str]:
    """Find a file matching any of the given patterns (case-insensitive)."""
    if not directory.is_dir():
        return None
    
    for item in directory.iterdir():
        if item.is_file():
            item_lower = item.name.lower()
            for pattern in patterns:
                if item_lower == pattern.lower() or item_lower.startswith(pattern.lower()):
                    # Return relative path from repo root
                    return str(item.relative_to(repo_root))
    return None


def read_readme(directory: Path) -> Optional[str]:
    """Read README.md content if it exists."""
    readme_path = directory / "README.md"
    if readme_path.is_file():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read {readme_path}: {e}")
    return None


def find_cover_image(directory: Path) -> Optional[str]:
    """Find cover image in directory."""
    if not directory.is_dir():
        return None
    
    for item in directory.iterdir():
        if item.is_file():
            item_lower = item.name.lower()
            if item_lower.startswith('cover'):
                ext = item.suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    return str(item.relative_to(repo_root))
    return None


def process_track(track_dir: Path) -> Optional[Dict]:
    """Process a track directory and return track object."""
    if not track_dir.is_dir():
        return None
    
    # Check if this directory contains audio files
    mp3_file = None
    m4a_file = None
    lyrics_file = None
    playlist_file = None
    
    for item in track_dir.iterdir():
        if item.is_file():
            ext = item.suffix.lower()
            if ext == '.mp3':
                mp3_file = str(item.relative_to(repo_root))
            elif ext == '.m4a':
                m4a_file = str(item.relative_to(repo_root))
            elif ext == '.txt' and 'lyric' in item.name.lower():
                lyrics_file = str(item.relative_to(repo_root))
            elif ext == '.m3u8':
                playlist_file = str(item.relative_to(repo_root))
    
    # Must have at least one audio file to be considered a track
    if not mp3_file and not m4a_file:
        return None
    
    track = {
        "name": track_dir.name,
        "path": str(track_dir.relative_to(repo_root)),
        "readme": read_readme(track_dir),
        "cover": find_cover_image(track_dir),
        "mp3": mp3_file,
        "m4a": m4a_file,
        "playlist": playlist_file,
        "lyrics": lyrics_file
    }
    
    return track


    return album


def process_collection(collection_dir: Path) -> Optional[Dict]:
    """Process a collection directory and return collection object."""
    if not collection_dir.is_dir() or collection_dir.name.startswith('.'):
        return None
    
    albums = []
    tracks = []
    
    # Look for subdirectories - they could be albums or tracks
    for item in sorted(collection_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            # Try processing as album first
            album = process_album(item)
            if album:
                albums.append(album)
            else:
                # Try processing as track (two-level hierarchy)
                track = process_track(item)
                if track:
                    tracks.append(track)
    
    # Must have either albums or tracks to be a valid collection
    if not albums and not tracks:
        return None
    
    collection = {
        "name": collection_dir.name,
        "path": str(collection_dir.relative_to(repo_root)),
        "readme": read_readme(collection_dir),
        "cover": find_cover_image(collection_dir),
        "albums": albums,
        "tracks": tracks
    }
    
    return collection


def process_collection(collection_dir: Path) -> Optional[Dict]:
    """Process a collection/album directory and return collection object."""
    if not collection_dir.is_dir() or collection_dir.name.startswith('.'):
        return None
    
    tracks = []
    
    # Look for track subdirectories
    for item in sorted(collection_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            track = process_track(item)
            if track:
                tracks.append(track)
    
    # Must have tracks to be a valid collection
    if not tracks:
        return None
    
    # Look for collection-level ZIP and playlist files
    collection_name = collection_dir.name
    zip_m4a = find_file_by_pattern(collection_dir, [f"{collection_name}-M4A.zip", f"{collection_name}-m4a.zip"])
    zip_mp3 = find_file_by_pattern(collection_dir, [f"{collection_name}-MP3.zip", f"{collection_name}-mp3.zip"])
    playlist_m4a = find_file_by_pattern(collection_dir, [f"{collection_name}-M4A.m3u8", f"{collection_name}-m4a.m3u8"])
    playlist_mp3 = find_file_by_pattern(collection_dir, [f"{collection_name}-MP3.m3u8", f"{collection_name}-mp3.m3u8"])
    
    collection = {
        "name": collection_dir.name,
        "path": str(collection_dir.relative_to(repo_root)),
        "readme": read_readme(collection_dir),
        "cover": find_cover_image(collection_dir),
        "zipM4A": zip_m4a,
        "zipMP3": zip_mp3,
        "playlistM4A": playlist_m4a,
        "playlistMP3": playlist_mp3,
        "tracks": tracks
    }
    
    return collection


def generate_catalog(repo_path: Path, owner: str = "kepello", repo: str = "music", branch: str = "main") -> Dict:
    """Generate the complete catalog structure."""
    collections = []
    
    # Iterate through top-level directories
    for item in sorted(repo_path.iterdir()):
        if item.is_dir() and not item.name.startswith('.') and item.name != '.git':
            collection = process_collection(item)
            if collection:
                collections.append(collection)
    
    # Look for library-level cover and readme at repository root
    library_cover = find_cover_image(repo_path)
    library_readme = read_readme(repo_path)
    
    catalog = {
        "version": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "owner": owner,
            "repo": repo,
            "branch": branch
        },
        "cover": library_cover,
        "readme": library_readme,
        "collections": collections
    }
    
    return catalog


def clean_catalog(obj):
    """Remove None values from the catalog structure."""
    if isinstance(obj, dict):
        return {k: clean_catalog(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [clean_catalog(item) for item in obj]
    else:
        return obj


if __name__ == "__main__":
    # Get repository root (assumes script is in repo root)
    repo_root = Path(__file__).parent.resolve()
    
    print(f"Generating catalog for repository at: {repo_root}", flush=True)
    
    # Generate catalog
    catalog = generate_catalog(repo_root)
    
    # Clean up None values
    catalog = clean_catalog(catalog)
    
    # Write to catalog.json
    catalog_path = repo_root / "catalog.json"
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"Catalog generated successfully!", flush=True)
    print(f"Collections: {len(catalog['collections'])}", flush=True)
    print(f"Output: {catalog_path}", flush=True)
