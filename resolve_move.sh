#!/bin/bash
# Abort any in-progress rebase and resolve the move cleanly

cd /Users/carl/projects/music

# Abort rebase if in progress
git rebase --abort 2>/dev/null || true

# Pull the latest changes
git pull

# Now do the move properly
git mv Dedicated/Line Deeply/Line 2>/dev/null || true

# Stage all changes
git add -A

# Commit
git commit -m "Move Line from Dedicated to Deeply album" || echo "Nothing to commit or already committed"

# Push
git push

echo "Done!"
