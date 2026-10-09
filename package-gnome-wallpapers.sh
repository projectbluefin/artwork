#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-dist/gnome}"
echo "Packaging Bluefin GNOME wallpapers into ${DEST}..."
rm -rf "${DEST}"
mkdir -p "${DEST}/gnome-background-properties"

# 1. Monthly wallpapers 01-12
for i in $(seq -w 1 12); do
    if [ "$i" = "11" ]; then
        cp -p "wallpapers/11-bluefin/11-bluefin-day.svg" "${DEST}/"
        cp -p "wallpapers/11-bluefin/11-bluefin-night.svg" "${DEST}/"
    else
        cp -p "wallpapers/${i}-bluefin/${i}-bluefin-day.jxl" "${DEST}/"
        cp -p "wallpapers/${i}-bluefin/${i}-bluefin-night.jxl" "${DEST}/"
    fi
    # Normalize internal XML file path to ~/.local/share/backgrounds/bluefin/<file>
    sed -E \
        -e 's|~/\.local/share/backgrounds/bluefin/[^/<]+/(.*\.jxl)|~/.local/share/backgrounds/bluefin/\1|g' \
        -e 's|~/\.local/share/backgrounds/bluefin/[^/<]+/(.*\.svg)|~/.local/share/backgrounds/bluefin/\1|g' \
        "wallpapers/${i}-bluefin/${i}-bluefin.xml" > "${DEST}/${i}-bluefin.xml"
done

# 2. Chicken wallpaper
cp -p "wallpapers/chicken/chicken.jxl" "${DEST}/"

# 3. XE collection
for xe in clouds foothills red_tulip space_needle sunset; do
    xe_hyphen="${xe//_/-}"
    cp -p "wallpapers/xe-${xe_hyphen}/xe-${xe_hyphen}.jxl" "${DEST}/xe_${xe}.jxl"
done

# 4. GNOME Background Properties
for f in wallpapers/gnome-background-properties/*.xml; do
    cp -p "$f" "${DEST}/gnome-background-properties/"
done


echo "Packaging complete. Total files in ${DEST}: $(find "${DEST}" -type f | wc -l)"
