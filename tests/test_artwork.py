"""Decode/render every artwork asset and check GNOME wallpaper resources."""

from collections import Counter
from datetime import datetime
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_PREFIX = "~/.local/share/backgrounds/bluefin/"


def artwork_paths():
    for directory in ("assets", "books", "wallpapers"):
        folder = ROOT / directory
        if not folder.is_dir():
            raise AssertionError(f"Missing artwork directory: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.relative_to(ROOT).as_posix() != (
                "assets/raster/gifs/bluefin-moment/warning.txt"
            ):
                yield path


def run(*command):
    result = subprocess.run(
        [str(arg) for arg in command],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    if result.returncode:
        raise AssertionError(f"{' '.join(map(str, command))}:\n{result.stderr}")


def validate_artwork(path):
    suffix = path.suffix.lower()
    if suffix == ".xml":
        validate_wallpaper_structure(path)
    elif suffix == ".svg":
        root = ET.parse(path).getroot()
        if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
            raise AssertionError(f"{path}: not an SVG root")
        if "viewBox" in root.attrib:
            box = [float(value) for value in re.split(r"[\s,]+", root.attrib["viewBox"].strip())]
            if len(box) != 4 or not all(map(math.isfinite, box)) or min(box[2:]) <= 0:
                raise AssertionError(f"{path}: invalid SVG viewBox")
        elif not {"width", "height"} <= root.attrib.keys():
            raise AssertionError(f"{path}: missing SVG dimensions")
        for dimension in ("width", "height"):
            if dimension not in root.attrib:
                continue
            size = re.fullmatch(
                r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(?:px|mm|cm|in|pt|pc|em|ex|%)?",
                root.attrib[dimension].strip(),
            )
            if not size or not math.isfinite(float(size[1])) or float(size[1]) <= 0:
                raise AssertionError(f"{path}: invalid SVG {dimension}")
        for element in root.iter():
            for attribute, value in element.attrib.items():
                references = re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", value)
                if attribute in ("href", "{http://www.w3.org/1999/xlink}href"):
                    references.append(value)
                for reference in references:
                    url = urlsplit(reference)
                    if not url.scheme and not url.netloc and url.path:
                        resource = path.parent / unquote(url.path)
                        if not resource.is_file():
                            raise AssertionError(f"{path}: missing SVG resource {reference}")
        with tempfile.TemporaryDirectory() as directory:
            run("rsvg-convert", "--width", "32", "--height", "32", "--output", Path(directory) / "image.png", path)
    elif suffix in (".png", ".mp4"):
        run("ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-i", path, "-f", "null", "-")
    elif suffix == ".jxl":
        with tempfile.TemporaryDirectory() as directory:
            run("djxl", path, Path(directory) / "image.ppm", "--quiet")
    elif suffix == ".pdf":
        with tempfile.TemporaryDirectory() as directory:
            run("pdftoppm", "-scale-to", "32", "-png", path, Path(directory) / "page")
    else:
        raise AssertionError(f"{path}: unhandled artwork format {suffix!r}")


def validate_wallpaper_structure(path):
    root = ET.parse(path).getroot()
    if root.tag == "background":
        start = root.find("starttime")
        if start is None:
            raise AssertionError(f"{path}: missing slideshow starttime")
        datetime(*(int(start.findtext(field, "")) for field in (
            "year", "month", "day", "hour", "minute", "second"
        )))
        slides = [element for element in root if element.tag != "starttime"]
        if not slides:
            raise AssertionError(f"{path}: empty slideshow")
        for slide in slides:
            tags = {"file"} if slide.tag == "static" else {"from", "to"}
            if slide.tag not in ("static", "transition") or not tags <= {e.tag for e in slide}:
                raise AssertionError(f"{path}: invalid slideshow entry")
            duration = float(slide.findtext("duration", ""))
            if not math.isfinite(duration) or duration <= 0:
                raise AssertionError(f"{path}: invalid slideshow duration")
    elif root.tag == "wallpapers":
        wallpapers = root.findall("wallpaper")
        if not wallpapers:
            raise AssertionError(f"{path}: empty wallpaper catalog")
        for wallpaper in wallpapers:
            if not wallpaper.findtext("name") or not wallpaper.findtext("filename"):
                raise AssertionError(f"{path}: missing wallpaper name or filename")
    else:
        raise AssertionError(f"{path}: not GNOME wallpaper XML")
    return root


def validate_wallpaper(path, resource_root):
    root = validate_wallpaper_structure(path)
    for element in root.iter():
        if element.tag not in ("file", "from", "to", "filename", "filename-dark"):
            continue
        reference = (element.text or "").strip()
        if not reference.startswith(BACKGROUND_PREFIX):
            raise AssertionError(f"{path}: unsupported wallpaper resource {reference!r}")
        resource = resource_root / reference.removeprefix(BACKGROUND_PREFIX)
        if not resource.is_file():
            raise AssertionError(f"{path}: missing wallpaper resource {reference}")

class ArtworkTests(unittest.TestCase):
    def test_artwork(self):
        """A malformed or undecodable asset must fail with its filename."""
        paths = list(artwork_paths())
        self.assertTrue(paths, "No artwork discovered")
        print("\nArtwork inventory:", dict(sorted(Counter(path.suffix for path in paths).items())), flush=True)
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                validate_artwork(path)

    def test_wallpaper_references(self):
        """GNOME catalogs and slideshows must point to installed resources."""
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "gnome"
            run("bash", ROOT / "package-gnome-wallpapers.sh", package)
            # Monthly source XML is transformed by the packaging script.
            for path in sorted(package.rglob("*.xml")):
                with self.subTest(package=path.relative_to(package)):
                    validate_wallpaper(path, package)
            for path in sorted((ROOT / "wallpapers").glob("*/gnome/gnome-background-properties/*.xml")):
                with self.subTest(source=path.relative_to(ROOT)):
                    validate_wallpaper(path, ROOT / "wallpapers")

    def test_corrupted_assets_fail(self):
        """Isolated invalid or truncated assets must be rejected by format checks."""
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            corruptions = {
                "corrupt.svg": "<svg xmlns='http://www.w3.org/2000/svg'><path d='M'</svg>",
                "missing_viewbox.svg": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
                "missing_ref.svg": "<svg xmlns='http://www.w3.org/2000/svg'><use href='missing.png'/></svg>",
                "corrupt.xml": "<background><starttime><year>2020</year></starttime></background>",
                "corrupt.png": "not a png image content",
                "corrupt.jxl": "not a jxl image content",
                "corrupt.mp4": "not an mp4 video content",
                "corrupt.pdf": "not a pdf document content",
            }
            for name, content in corruptions.items():
                target = temp_dir / name
                target.write_text(content) if isinstance(content, str) else target.write_bytes(content)
                with self.subTest(corrupt=name):
                    with self.assertRaises(Exception):
                        validate_artwork(target)

if __name__ == "__main__":
    unittest.main()
