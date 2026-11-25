"""
compress_reports.py  -  makes the PDF reports smaller before they go on the website.

WHY
    Most of a report's size comes from the pictures (photos, drawings, scans).
    This script shrinks only the pictures. The text stays exactly as it is,
    so the abstract can still be read by build.py and readers can still search the PDF.

HOW TO USE
    1. Put the ORIGINAL report PDFs in the folder called  incoming
       (the script creates it the first time you run it).
    2. Run:    python compress_reports.py
    3. The smaller copies appear in the  reports  folder.
    4. Then run:    python build.py

YOUR ORIGINALS ARE NEVER CHANGED. They stay safely in "incoming".
(That folder is not uploaded to GitHub - see the .gitignore file.)

EXTRA PACKAGE NEEDED (once):    python -m pip install -r requirements.txt
"""

import io
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from PIL import Image

# --------------------------------------------------------------------------
# SETTINGS  -  safe to change
# --------------------------------------------------------------------------
INPUT_FOLDER = "incoming"    # originals go here
OUTPUT_FOLDER = "reports"    # smaller copies are written here
MAX_PICTURE_SIDE = 1600      # longest side of a picture, in pixels (about 245 dpi on a page)
JPEG_QUALITY = 70            # 1-100. Lower = smaller file but fuzzier pictures
SKIP_SMALL_PICTURES = 60_000  # leave pictures smaller than this (in bytes) alone
MIN_SAVING = 0.05            # if we save less than 5%, just keep the original

HERE = Path(__file__).resolve().parent


def size_text(num_bytes):
    """12345678 -> '12.3 MB',  45000 -> '45 KB'"""
    if num_bytes >= 1_000_000:
        return "%.1f MB" % (num_bytes / 1_000_000)
    return "%d KB" % max(1, round(num_bytes / 1000))


def shrink_pictures(writer):
    """Re-save every large picture in the PDF at a lower size and quality."""
    changed = 0
    for page in writer.pages:
        try:
            images = list(page.images)
        except Exception:
            continue
        for image in images:
            try:
                original_bytes = len(image.data)
                if original_bytes < SKIP_SMALL_PICTURES:
                    continue
                picture = image.image
                if picture.mode == "RGBA":
                    # only touch it if nothing in it is actually transparent
                    if picture.getchannel("A").getextrema() != (255, 255):
                        continue
                    picture = picture.convert("RGB")
                if picture.mode not in ("RGB", "L"):
                    continue  # unusual pictures: leave alone (safe)
                if max(picture.size) > MAX_PICTURE_SIDE:
                    picture.thumbnail((MAX_PICTURE_SIDE, MAX_PICTURE_SIDE), Image.LANCZOS)
                # test the new size before using it
                test = io.BytesIO()
                picture.save(test, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                if test.tell() >= original_bytes:
                    continue  # no gain, keep the original picture
                image.replace(picture, quality=JPEG_QUALITY)
                changed += 1
            except Exception:
                continue  # any problem with one picture: leave that picture as it was
    return changed


def same_text(original_path, new_path, pages=5):
    """Safety check: the first pages must contain the same text and the page count must match."""
    a, b = PdfReader(str(original_path)), PdfReader(str(new_path))
    if len(a.pages) != len(b.pages):
        return False
    for i in range(min(pages, len(a.pages))):
        if (a.pages[i].extract_text() or "").split() != (b.pages[i].extract_text() or "").split():
            return False
    return True


def compress_one(source, target):
    """Returns a short message describing what happened."""
    before = source.stat().st_size
    temp = target.with_suffix(".tmp")
    try:
        writer = PdfWriter(clone_from=str(source))
        pictures = shrink_pictures(writer)
        for page in writer.pages:
            page.compress_content_streams()
        try:   # newer versions of pypdf use these option names
            writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
        except TypeError:   # older versions
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        with open(temp, "wb") as f:
            writer.write(f)

        after = temp.stat().st_size
        if after > before * (1 - MIN_SAVING):
            temp.unlink()
            shutil.copy2(source, target)
            return "kept original (%s) - not worth shrinking" % size_text(before)
        if not same_text(source, temp):
            temp.unlink()
            shutil.copy2(source, target)
            return "kept original (%s) - the check failed, so nothing was changed" % size_text(before)

        temp.replace(target)
        return "%s -> %s  (%d%% smaller, %d pictures shrunk)" % (
            size_text(before), size_text(after), round(100 * (1 - after / before)), pictures)
    except Exception as error:
        if temp.exists():
            temp.unlink()
        shutil.copy2(source, target)
        return "kept original - could not compress (%s)" % error


def main():
    source_folder = HERE / INPUT_FOLDER
    target_folder = HERE / OUTPUT_FOLDER
    if not source_folder.is_dir():
        source_folder.mkdir()
        print('I created an empty folder called "%s".' % INPUT_FOLDER)
        print("Put your original report PDFs in it, then run this script again.")
        return
    target_folder.mkdir(exist_ok=True)

    pdfs = sorted(source_folder.glob("*.pdf"), key=lambda p: p.name.lower())
    if not pdfs:
        sys.exit('No PDF files found in the "%s" folder.' % INPUT_FOLDER)

    total_before = total_after = 0
    for pdf in pdfs:
        target = target_folder / pdf.name
        print("%-28s" % pdf.name, end=" ", flush=True)
        print(compress_one(pdf, target))
        total_before += pdf.stat().st_size
        total_after += target.stat().st_size

    print("\nAll done: %s -> %s" % (size_text(total_before), size_text(total_after)))
    print('Smaller copies are in "%s". Now run:  python build.py' % OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
