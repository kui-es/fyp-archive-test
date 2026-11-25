"""
build.py  -  builds the Final Year Projects web page.

WHAT IT DOES
    1. Looks at every PDF in the "reports" folder.
    2. Reads the cover page of each PDF to get: project ID, title and year.
    3. Finds the "Abstract" page and copies the abstract text.
    4. Fills in template.html and writes the finished page to index.html.

HOW TO RUN IT   (in the VS Code terminal, inside this folder)
    python build.py

You only need to run it again when you add, remove or replace a report.
"""

import csv
import html
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote

from pypdf import PdfReader

# --------------------------------------------------------------------------
# SETTINGS  -  safe to change
# --------------------------------------------------------------------------
PAGE_TITLE = "B.Sc. Mechatronic Engineering Final Year Projects"
REPORTS_FOLDER = "reports"      # where the PDF files are kept
TEMPLATE_FILE = "template.html"  # the design of the page
OVERRIDES_FILE = "overrides.csv"  # manual corrections (see README)
OUTPUT_FILE = "index.html"      # the finished page (created by this script)
PAGES_TO_SEARCH = 14            # the abstract is looked for in the first 14 pages

# --------------------------------------------------------------------------
# Folder paths. HERE = the folder that contains this script.
# --------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Patterns used to recognise things in the PDF text
# --------------------------------------------------------------------------
# Project ID such as  FYP-19-8  or  FYP 20-24  or  FYP–07–09
ID_PATTERN = re.compile(r"\bFYP\s*[-–—]?\s*(\d+)\s*[-–—]\s*(\d+)\b", re.IGNORECASE)

# A year such as 2024
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")

# Lines on the cover page that belong to the university heading (not the title)
HEADING_LINE = re.compile(r"university|college of|school of|faculty|department of|institute", re.IGNORECASE)

# A line made only of rule characters, e.g. ________  or ————
RULE_LINE = re.compile(r"^[\s_\-–—─=.*]{4,}$")

# The word "Abstract" on a line by itself (so the Table of Contents line
# "Abstract . . . . II" does not match)
ABSTRACT_HEADING = re.compile(r"^\s*(?:\d+\.?\s*)?abstract\s*:?\s*$", re.IGNORECASE)

# Headings that mean "the abstract has ended"
STOP_HEADING = re.compile(
    r"^\s*(?:table of contents|contents|list of (?:figures|tables|abbreviations|acronyms|symbols)"
    r"|acknowledge?ments?|declaration|dedication|preface|abbreviations|nomenclature"
    r"|keywords?\b.*|(?:chapter\s+(?:1|one)\b.*)|(?:1\.?\s+)?introduction)\s*$",
    re.IGNORECASE,
)

# Dot leaders as in a table of contents:  Introduction . . . . . 1
DOT_LEADERS = re.compile(r"(?:\.\s){4,}")

# A line that is only a page number (I, ii, 12 ...)
PAGE_NUMBER_LINE = re.compile(r"^\s*(?:[ivxlcdm]+|\d{1,3})\s*$", re.IGNORECASE)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def tidy(text):
    """Convert odd characters (ligatures such as 'fi', non-breaking spaces) to normal ones."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "")  # soft hyphen
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def page_text(reader, index):
    """Text of one page, keeping the layout (blank lines and indents show paragraphs)."""
    try:
        return tidy(reader.pages[index].extract_text(extraction_mode="layout"))
    except Exception:
        return ""


def clean_lines(text):
    return [line.rstrip() for line in text.splitlines()]


def normalise_id(xx, yy):
    return "FYP-%s-%s" % (xx, yy)


# --------------------------------------------------------------------------
# 1. Cover page: ID, title, year
# --------------------------------------------------------------------------
def read_cover(cover_text):
    """Return (id, title, year) from the text of page 1. Missing items are None."""
    lines = [l.strip() for l in clean_lines(cover_text) if l.strip()]

    id_index, project_id = None, None
    for i, line in enumerate(lines):
        match = ID_PATTERN.search(line)
        if match:
            id_index, project_id = i, normalise_id(match.group(1), match.group(2))
            break

    # Title = the lines just above the ID, after the university heading
    title = None
    if id_index is not None:
        title_lines = []
        for line in reversed(lines[:id_index]):
            if HEADING_LINE.search(line) or RULE_LINE.match(line):
                break
            title_lines.insert(0, line)
        title = " ".join(title_lines).strip() or None

    # Year = the last year written on the cover (the date is at the bottom)
    search_area = lines[id_index + 1:] if id_index is not None else lines
    years = YEAR_PATTERN.findall(" ".join(search_area)) or YEAR_PATTERN.findall(" ".join(lines))
    year = int(years[-1]) if years else None

    return project_id, title, year


# --------------------------------------------------------------------------
# 2. Abstract
# --------------------------------------------------------------------------
def line_key(line):
    """Used to spot running headers/footers: the line without page numbers."""
    line = re.sub(r"\b(?:[ivxlcdm]+|\d+)\b", "", line.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", line).strip().lower()


def find_repeated_lines(page_texts):
    """Lines that appear on 3+ pages are running headers or footers - we ignore them."""
    counts = {}
    for text in page_texts:
        for key in {line_key(l) for l in clean_lines(text) if l.strip()}:
            if len(key) > 3:
                counts[key] = counts.get(key, 0) + 1
    return {key for key, n in counts.items() if n >= 3}


def hyphen_vocabulary(reader, max_pages=60):
    """Words with a hyphen that appear inside a line somewhere in the report, e.g. 'dual-axis'.
    Used to decide whether 'dual-' at the end of a line should keep its hyphen."""
    words = set()
    for i in range(min(len(reader.pages), max_pages)):
        try:
            text = tidy(reader.pages[i].extract_text())
        except Exception:
            continue
        for word in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)+", text):
            words.add(word.lower())
    return words


def join_lines(lines, reader):
    """Join the lines of one paragraph into a single string, repairing words that
    were split with a hyphen at the end of a line."""
    vocab = None
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
            continue
        if out.endswith("-") and line[:1].islower():
            if vocab is None:
                vocab = hyphen_vocabulary(reader)
            left = re.search(r"([A-Za-z]+)-$", out)
            right = re.match(r"[A-Za-z]+", line)
            if left and right and (left.group(1) + "-" + right.group(0)).lower() in vocab:
                out = out + line          # real hyphenated word: keep the hyphen
            else:
                out = out[:-1] + line     # word split by the typesetter: remove the hyphen
        else:
            out = out + " " + line
    return re.sub(r"\s+", " ", out).strip()


def read_abstract(reader):
    """Return the abstract as a list of paragraphs (strings), or [] if not found."""
    count = min(len(reader.pages), PAGES_TO_SEARCH)
    texts = [page_text(reader, i) for i in range(count)]
    repeated = find_repeated_lines(texts)

    # Find the page that has the heading "Abstract" on its own line
    start_page, start_line = None, None
    for p in range(1, count):  # skip the cover page
        lines = clean_lines(texts[p])
        for j, line in enumerate(lines):
            if ABSTRACT_HEADING.match(line):
                start_page, start_line = p, j
                break
        if start_page is not None:
            break
    if start_page is None:
        return []

    collected = []  # list of lines (with their original indentation); None = blank line
    for p in range(start_page, count):
        lines = clean_lines(texts[p])
        body = lines[start_line + 1:] if p == start_page else lines
        page_lines = []
        for line in body:
            stripped = line.strip()
            is_heading = bool(STOP_HEADING.match(stripped)) or bool(DOT_LEADERS.search(stripped))
            if stripped and not is_heading and (PAGE_NUMBER_LINE.match(stripped) or line_key(stripped) in repeated):
                continue
            page_lines.append(line if stripped else None)

        # blank space at the top or bottom of a page does not mean a new paragraph
        while page_lines and page_lines[0] is None:
            page_lines.pop(0)
        while page_lines and page_lines[-1] is None:
            page_lines.pop()

        # Does this page begin with a new section heading? Then the abstract already ended.
        first_text = next((l for l in page_lines if l is not None), None)
        if p != start_page and (first_text is None or STOP_HEADING.match(first_text.strip())
                                or DOT_LEADERS.search(first_text)):
            break

        ended = False
        for line in page_lines:
            if line is not None and (STOP_HEADING.match(line.strip()) or DOT_LEADERS.search(line)):
                ended = True
                break
            collected.append(line)
        if ended:
            break
        if p - start_page >= 3:  # an abstract is never longer than a few pages
            break

    # Split into paragraphs: a blank line or an indented line starts a new paragraph
    body_lines = [l for l in collected if l is not None]
    if not body_lines:
        return []
    base_indent = min(len(l) - len(l.lstrip()) for l in body_lines)
    paragraphs, current = [], []
    previous_blank = False
    for line in collected:
        if line is None:
            previous_blank = True
            continue
        indent = len(line) - len(line.lstrip())
        if current and (previous_blank or indent >= base_indent + 3):
            paragraphs.append(current)
            current = []
        current.append(line)
        previous_blank = False
    if current:
        paragraphs.append(current)

    result = [join_lines(p, reader) for p in paragraphs]
    return [p for p in result if p]


# --------------------------------------------------------------------------
# 3. Manual corrections (overrides.csv)
# --------------------------------------------------------------------------
def read_overrides():
    path = HERE / OVERRIDES_FILE
    overrides = {}
    if not path.exists():
        return overrides
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [line for line in f if line.strip() and not line.lstrip().startswith("#")]
    for row in csv.DictReader(rows):
        name = (row.get("file") or "").strip()
        if name:
            overrides[name.lower()] = {k: (v or "").strip() for k, v in row.items() if k != "file"}
    return overrides


# --------------------------------------------------------------------------
# 4. Put it all together
# --------------------------------------------------------------------------
def human_size(num_bytes):
    return "%.1f MB" % (num_bytes / 1_000_000) if num_bytes >= 1_000_000 else "%d KB" % max(1, round(num_bytes / 1000))


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|]+', "", text)
    return re.sub(r"\s+", " ", text).strip()[:110]


def collect_projects():
    folder = HERE / REPORTS_FOLDER
    pdfs = sorted(folder.glob("*.pdf"), key=lambda p: p.name.lower())
    overrides = read_overrides()
    projects, warnings = [], []

    for pdf in pdfs:
        problems = []
        try:
            reader = PdfReader(str(pdf))
            project_id, title, year = read_cover(page_text(reader, 0))
            abstract = read_abstract(reader)
        except Exception as error:  # damaged or password-protected file
            warnings.append("%s: could not be read (%s)" % (pdf.name, error))
            continue

        fix = overrides.get(pdf.name.lower(), {})
        if fix.get("id"):
            m = ID_PATTERN.search(fix["id"])
            project_id = normalise_id(m.group(1), m.group(2)) if m else fix["id"]
        if fix.get("title"):
            title = fix["title"]
        if fix.get("year"):
            year = int(fix["year"])
        if fix.get("abstract"):
            abstract = [p.strip() for p in fix["abstract"].split("||") if p.strip()]

        if not project_id:
            m = ID_PATTERN.search(pdf.stem)  # try the file name instead
            if m:
                project_id = normalise_id(m.group(1), m.group(2))
            else:
                problems.append("project ID not found")
        if not title:
            title = pdf.stem
            problems.append("title not found")
        if not year:
            problems.append("year not found")
        if not abstract:
            problems.append("abstract not found")

        sort_key = (0, 0)
        if project_id:
            m = ID_PATTERN.search(project_id)
            if m:
                sort_key = (int(m.group(1)), int(m.group(2)))

        projects.append({
            "file": pdf.name, "id": project_id or "FYP-?", "title": title, "year": year,
            "abstract": abstract, "size": pdf.stat().st_size, "sort": sort_key, "problems": problems,
        })
        for problem in problems:
            warnings.append("%s: %s" % (pdf.name, problem))

    # the same ID used twice is probably a mistake
    seen = {}
    for p in projects:
        if p["id"] != "FYP-?":
            seen.setdefault(p["id"], []).append(p["file"])
    for project_id, files in seen.items():
        if len(files) > 1:
            warnings.append("%s is used by more than one file: %s" % (project_id, ", ".join(files)))

    return projects, warnings


def render_project(p):
    e = html.escape
    href = REPORTS_FOLDER + "/" + quote(p["file"])
    nice_name = safe_filename("%s - %s" % (p["id"], p["title"])) + ".pdf"
    if p["abstract"]:
        abstract_html = "\n".join("<p>%s</p>" % e(par) for par in p["abstract"])
    else:
        abstract_html = '<p class="missing">The abstract could not be read from this report.</p>'
    return (
        '<li class="project">\n'
        '  <details>\n'
        '    <summary><span class="fyp-id">%s</span><span class="fyp-title">%s</span></summary>\n'
        '    <div class="detail">\n'
        '      <h4>Abstract</h4>\n'
        '      %s\n'
        '      <a class="download" href="%s" download="%s">Download project report <span>PDF, %s</span></a>\n'
        '    </div>\n'
        '  </details>\n'
        '</li>'
    ) % (e(p["id"]), e(p["title"]), abstract_html, e(href, quote=True), e(nice_name, quote=True), human_size(p["size"]))


def build_page(projects):
    by_year = {}
    for p in projects:
        by_year.setdefault(p["year"], []).append(p)

    def year_order(y):  # newest first; unknown year last
        return (y is None, -(y or 0))

    sections = []
    for year in sorted(by_year, key=year_order):
        items = sorted(by_year[year], key=lambda p: (p["sort"], p["file"]))
        label = str(year) if year else "Year not known"
        n = len(items)
        sections.append(
            '<section class="year" id="y%s">\n'
            '  <h2>%s <small>%d project%s</small></h2>\n'
            '  <ol>\n%s\n  </ol>\n'
            '</section>' % (year or "unknown", html.escape(label), n, "" if n == 1 else "s",
                            "\n".join(render_project(p) for p in items))
        )

    template = (HERE / TEMPLATE_FILE).read_text(encoding="utf-8")
    page = (template
            .replace("{{PAGE_TITLE}}", html.escape(PAGE_TITLE))
            .replace("{{PROJECT_COUNT}}", str(len(projects)))
            .replace("{{UPDATED}}", date.today().strftime("%d %B %Y").lstrip("0"))
            .replace("{{YEARS}}", "\n".join(sections)))
    (HERE / OUTPUT_FILE).write_text(page, encoding="utf-8")


def main():
    if not (HERE / REPORTS_FOLDER).is_dir():
        sys.exit('The folder "%s" was not found next to build.py.' % REPORTS_FOLDER)
    if not (HERE / TEMPLATE_FILE).is_file():
        sys.exit('The file "%s" was not found next to build.py.' % TEMPLATE_FILE)

    projects, warnings = collect_projects()
    if not projects:
        sys.exit('No PDF files were found in the "%s" folder.' % REPORTS_FOLDER)

    build_page(projects)

    # A short summary so you can check the results at a glance
    print("\n%-14s %-6s %-9s %s" % ("ID", "Year", "Abstract", "Title"))
    print("-" * 78)
    for p in sorted(projects, key=lambda p: (-(p["year"] or 0), p["sort"])):
        words = sum(len(par.split()) for par in p["abstract"])
        print("%-14s %-6s %-9s %s" % (p["id"], p["year"] or "?", ("%d words" % words) if words else "MISSING", p["title"][:48]))
    print("\n%d projects written to %s" % (len(projects), OUTPUT_FILE))
    if warnings:
        print("\nPLEASE CHECK:")
        for w in warnings:
            print("  - " + w)
        print('Fix these by adding a row to "%s" (see README.md).' % OVERRIDES_FILE)
    else:
        print("No problems found.")


if __name__ == "__main__":
    main()
