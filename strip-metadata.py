#!/usr/bin/env python3
"""
Strip all metadata (including embedded images) from audio files.

This script removes all ID3 tags, embedded artwork, and other metadata
from MP3 and M4A files to minimize file size and ensure privacy.
"""

import sys
from pathlib import Path
from typing import List

try:
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.id3 import ID3
except ImportError:
    print("Error: mutagen library not found.")
    print("Install it with: pip install mutagen")
    sys.exit(1)


def strip_mp3_metadata(filepath: Path) -> bool:
    """Remove all metadata from an MP3 file."""
    try:
        audio = MP3(filepath)
        # Delete all ID3 tags
        audio.delete()
        audio.save()
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def strip_m4a_metadata(filepath: Path) -> bool:
    """Remove all metadata from an M4A file."""
    try:
        audio = MP4(filepath)
        # Delete all tags
        audio.delete()
        audio.save()
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def find_audio_files(root_dir: Path) -> List[Path]:
    """Find all MP3 and M4A files in the repository."""
    audio_files = []
    audio_files.extend(root_dir.rglob("*.mp3"))
    audio_files.extend(root_dir.rglob("*.MP3"))
    audio_files.extend(root_dir.rglob("*.m4a"))
    audio_files.extend(root_dir.rglob("*.M4A"))
    return sorted(audio_files)


def main():
    repo_root = Path(__file__).parent.resolve()
    
    print("Finding audio files...")
    audio_files = find_audio_files(repo_root)
    
    if not audio_files:
        print("No audio files found.")
        return
    
    print(f"Found {len(audio_files)} audio files\n")
    
    mp3_count = 0
    m4a_count = 0
    success_count = 0
    
    for audio_file in audio_files:
        relative_path = audio_file.relative_to(repo_root)
        ext = audio_file.suffix.lower()
        
        print(f"Processing: {relative_path}")
        
        if ext == '.mp3':
            if strip_mp3_metadata(audio_file):
                mp3_count += 1
                success_count += 1
            else:
                print(f"  ❌ Failed")
        elif ext == '.m4a':
            if strip_m4a_metadata(audio_file):
                m4a_count += 1
                success_count += 1
            else:
                print(f"  ❌ Failed")
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  MP3 files processed: {mp3_count}")
    print(f"  M4A files processed: {m4a_count}")
    print(f"  Total succeeded: {success_count} of {len(audio_files)}")
    print(f"{'='*60}")
    
    if success_count < len(audio_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
