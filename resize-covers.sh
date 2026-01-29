#!/bin/bash
# Resize all cover images to 800x800 max while maintaining aspect ratio

echo "Resizing cover images to 800x800..."

find . -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" \) | grep -iE "cover" | while read img; do
    # Get current dimensions
    width=$(sips -g pixelWidth "$img" | grep pixelWidth | awk '{print $2}')
    height=$(sips -g pixelHeight "$img" | grep pixelHeight | awk '{print $2}')
    
    # Check if resizing is needed
    if [ "$width" -gt 800 ] || [ "$height" -gt 800 ]; then
        echo "Resizing: $img (${width}x${height} -> 800x800)"
        # Resize maintaining aspect ratio, max dimension 800
        sips --resampleHeightWidthMax 800 "$img" --out "$img" > /dev/null 2>&1
    else
        echo "Skipping: $img (${width}x${height} already ≤ 800x800)"
    fi
done

echo ""
echo "Before and After sizes:"
find . -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" \) | grep -iE "cover" | xargs ls -lh | awk '{print $5, $9}'

echo ""
echo "Total size:"
du -ch $(find . -type f \( -iname "*.jpg" -o -iname "*.png" -o -iname "*.jpeg" \) | grep -iE "cover") | tail -1

echo ""
echo "Done!"
