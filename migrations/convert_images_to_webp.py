"""Create a WebP copy (max 800px wide) next to every PNG/JPEG in app/static/images.

Usage:
    python migrations/convert_images_to_webp.py [--dry-run] [--force]

Additive and idempotent: originals and database values are left untouched, and
files that already have an up-to-date .webp are skipped. The app serves the
.webp automatically when it exists (see Exercise.get_by_id).

Requires the `cwebp` tool (macOS: brew install webp, Debian/Ubuntu: apt install webp).
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

IMAGES = Path(__file__).resolve().parent.parent / "app" / "static" / "images"
MAX_WIDTH = 800
QUALITY = 80


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="list what would be converted")
    parser.add_argument("--force", action="store_true", help="reconvert even if the .webp exists")
    args = parser.parse_args()

    if not args.dry_run and not shutil.which("cwebp"):
        sys.exit("cwebp not found. Install it (brew install webp / apt install webp) and run again.")

    sources = sorted(p for p in IMAGES.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    converted = skipped = 0
    before = after = 0

    for source in sources:
        target = source.with_suffix(".webp")
        if target.exists() and not args.force and target.stat().st_mtime >= source.stat().st_mtime:
            skipped += 1
            continue
        if args.dry_run:
            print(f"would convert {source.name}")
            converted += 1
            continue
        # -resize W 0 keeps the aspect ratio; cwebp never upscales with a width above the source
        width = min(MAX_WIDTH, _width(source))
        subprocess.run(
            ["cwebp", "-quiet", "-q", str(QUALITY), "-resize", str(width), "0", str(source), "-o", str(target)],
            check=True,
        )
        before += source.stat().st_size
        after += target.stat().st_size
        converted += 1

    verb = "Would convert" if args.dry_run else "Converted"
    print(f"{verb} {converted} images, skipped {skipped} already done.")
    if after:
        print(f"{before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")


def _width(path):
    """Pixel width from the PNG/JPEG header via `webpinfo`-free probing (PNG only), else MAX_WIDTH."""
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(header[16:20], "big")
    return MAX_WIDTH


if __name__ == "__main__":
    main()
