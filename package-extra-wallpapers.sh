#!/usr/bin/env bash
# Package the Bluefin extra wallpapers into the GNOME tarball consumed by
# the projectbluefin/tap `bluefin-wallpapers-extra` cask.
# Layout: images/<files> + gnome-background-properties/<wp>.xml
set -euo pipefail

DEST="${1:-dist/extra}"
WALLPAPERS=(dusk prey huntress tenacious-pterosaur leaf-collector duality eyes lazy-days)

rm -rf "${DEST}"
mkdir -p "${DEST}/gnome/images" "${DEST}/gnome/gnome-background-properties"

for wp in "${WALLPAPERS[@]}"; do
    src="wallpapers/${wp}"
    found=0
    for f in "${src}"/*.svg "${src}"/*.jxl "${src}"/*.xml; do
        [ -f "$f" ] || continue
        cp -p "$f" "${DEST}/gnome/images/"
        found=1
    done
    [ "$found" -eq 1 ] || { echo "No images for ${wp}" >&2; exit 1; }
    cp -p "${src}"/gnome/gnome-background-properties/*.xml "${DEST}/gnome/gnome-background-properties/"
done

# Every file referenced by the properties must ship in the tarball; the cask
# links images/<name>[-day|-night].* into backgrounds/bluefin/<name>/.
for props in "${DEST}"/gnome/gnome-background-properties/*.xml; do
    target=$(sed -n 's|.*<filename>~/.local/share/backgrounds/bluefin/[^/]*/\([^<]*\)</filename>.*|\1|p' "$props")
    [ -f "${DEST}/gnome/images/${target}" ] || { echo "${props} references missing ${target}" >&2; exit 1; }
done

tar --zstd -C "${DEST}/gnome" -cf "${DEST}/bluefin-wallpapers-extra-gnome.tar.zstd" images gnome-background-properties
echo "Packaged $(find "${DEST}/gnome" -type f | wc -l) files into ${DEST}/bluefin-wallpapers-extra-gnome.tar.zstd"
