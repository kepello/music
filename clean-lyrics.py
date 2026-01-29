#!/usr/bin/env python3
"""
Remove text within brackets [] from all lyrics files.
"""

import re
from pathlib import Path

def clean_lyrics_file(filepath: Path):
    """Remove text within brackets from a lyrics file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove text within brackets including the brackets
        cleaned = re.sub(r'\[.*?\]', '', content)
        
        # Clean up any resulting multiple blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == "__main__":
    repo_root = Path(__file__).parent.resolve()
    
    # Find all lyrics files
    lyrics_files = list(repo_root.rglob("LYRICS.txt")) + list(repo_root.rglob("lyrics.txt"))
    
    print(f"Found {len(lyrics_files)} lyrics files")
    
    success_count = 0
    for lyrics_file in lyrics_files:
        print(f"Processing: {lyrics_file.relative_to(repo_root)}")
        if clean_lyrics_file(lyrics_file):
            success_count += 1
    
    print(f"\nProcessed {success_count} of {len(lyrics_files)} files successfully")
