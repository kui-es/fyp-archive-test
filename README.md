# B.Sc. Mechatronic Engineering – Final Year Projects page

A simple website that lists past final year projects by year. Click a project to read its abstract and download the full report.

**How it works in one sentence:** you put the PDF reports in the `reports` folder, run one Python command, and it writes the finished page (`index.html`) for you.

---

## 1. Where are the reports stored?

**In the `reports` folder, next to the page. Not in Google Drive.**

The page and the PDFs travel together as one folder, and the download button simply points to `reports/FYP-19-8.pdf`. This is better than Google Drive here because:

- Drive links depend on sharing settings, can ask visitors to sign in, and sometimes show a "virus scan" screen for big files.
- If your Google account changes, every link would break.
- Everything stays on the department's own server, which is what you want for an official archive.

You only need space for the PDFs (about 4–10 MB each, so even 300 reports is only a few GB).

---

## 2. What each file is

```
fyp-archive/
├── build.py            the program that builds the page
├── compress_reports.py makes the PDF reports smaller
├── template.html       the design of the page
├── overrides.csv       your manual corrections
├── requirements.txt    the add-ons Python needs (pypdf and pillow)
├── .gitignore          tells GitHub which folders not to upload
├── README.md           this guide
├── index.html          the finished page  (created by build.py)
├── incoming/           your ORIGINAL PDFs (stays on your computer only)
└── reports/            the smaller PDFs shown on the website
    ├── FYP-19-8.pdf
    └── ...
```

**`build.py`** – the engine. When you run it, it does four things:
1. Opens every PDF in `reports/`.
2. Reads the cover page to get the project ID (`FYP-19-8`), the title and the year (the year written in the date at the bottom of the cover, e.g. "January 2024").
3. Finds the page with the heading "Abstract" and copies the text under it, tidying up words that were split across lines.
4. Pours all of that into `template.html` and saves the result as `index.html`.

It also prints a summary table in the terminal and a **"PLEASE CHECK"** list if it could not find something.

You will rarely edit this file. The only part you might change is the block at the top called `SETTINGS`, for example `PAGE_TITLE`.

**`compress_reports.py`** – shrinks the reports before they go online. Most of a report's size is pictures, so this script re-saves only the pictures at a smaller size. The text is untouched, so the abstract can still be read and the PDF can still be searched. On your two real samples it cut a 4.2 MB report to 1.9 MB and a 10.2 MB report to 4.8 MB. It **never changes your originals**: it reads them from `incoming/` and writes the smaller copies into `reports/`. If it cannot make a file smaller, or its safety check fails, it simply copies the original. The two numbers at the top (`MAX_PICTURE_SIDE`, `JPEG_QUALITY`) control how hard it squeezes.

**`.gitignore`** – a short list telling GitHub not to upload the `incoming/` folder. Your big originals stay on your computer, which keeps the website under GitHub's 1 GB limit.

**`template.html`** – the look of the page. It is written in HTML (the structure) and CSS (the colours and spacing). The words in double curly brackets, like `{{PAGE_TITLE}}`, are blanks that `build.py` fills in. Things you may want to change here:
- The colours: the five lines under `/* Colours */` at the top.
- The sentence under the title ("Browse past final year projects…").
- The small line "Department of Mechatronic Engineering".
- The artwork: the gears and the workers in the left-hand column are drawn in the file itself (the `<aside class="rail">` block). They turn slowly on screen, and the column disappears on narrow screens such as phones. To remove it, delete everything from `<aside` to `</aside>`. The yellow and black stripe under the banner is the `hazard` line in the CSS.

**`overrides.csv`** – a spreadsheet-like file for fixing mistakes (see section 5). Empty at first.

**`requirements.txt`** – a shopping list for Python: `pypdf` reads and writes PDF files, and `pillow` handles the pictures inside them.

**`index.html`** – the finished page. **Never edit it by hand**: the next time you run `build.py` it is rewritten from scratch and your changes would be lost. Change `template.html` instead.

**`incoming/`** – where you drop the original PDFs. It is created the first time you run `compress_reports.py`.

**`reports/`** – the PDFs that the website uses. Name each file after its project ID, for example `FYP-23-5.pdf`. The name is not what the page uses (it reads the ID from the cover), but matching names make the folder easy to manage and make the downloads tidy.

---

## 3. One-time setup (about five minutes)

1. In VS Code choose **File → Open Folder** and open the `fyp-archive` folder.
2. Open the terminal: **Terminal → New Terminal**.
3. Install the add-ons (only once):
   ```
   python -m pip install -r requirements.txt
   ```
   If `python` is not recognised on Windows, use `py` instead (`py -m pip install -r requirements.txt`). Do the same for the commands below.

---

## 4. Everyday routine: adding a new year's projects

1. Rename each new PDF to its ID (`FYP-24-3.pdf`) and put it in the `incoming/` folder (create the folder if it is not there).
2. In the VS Code terminal run these two commands, one after the other:
   ```
   python compress_reports.py
   python build.py
   ```
   The first makes smaller copies in `reports/`. The second builds the page.
3. Read the table it prints. Each project should show an ID, a year and an abstract word count (a normal abstract is 100–300 words). If there is a **PLEASE CHECK** list, see section 5.
4. Preview the page (next section).
5. Copy `index.html` and the `reports` folder to the server.

**To remove a project:** delete its PDF from `reports/` (and from `incoming/`) and run `python build.py` again.
**To replace a report:** put the new PDF in `incoming/` with the same file name, then run both commands again.
**If you already have small PDFs** and don't want them compressed, you can put them straight into `reports/` and just run `python build.py`.

### Previewing on your computer (the "pretend IP address")

Your computer already has a built-in address that points to itself: **`127.0.0.1`** (also called `localhost`). It behaves exactly like a server's IP address, so it is perfect for testing.

In the terminal, inside the `fyp-archive` folder, run:
```
python -m http.server 8000
```
Then open a browser and go to **http://127.0.0.1:8000**. Press `Ctrl + C` in the terminal to stop.

(To test from a phone on the same Wi-Fi, run `python -m http.server 8000 --bind 0.0.0.0` and visit `http://YOUR-COMPUTER'S-IP:8000`. Windows may ask you to allow it through the firewall.)

---

## 5. When the page gets something wrong

Typical causes: the cover page is laid out differently, the report is a scan (a picture of pages, so there is no text to read), or the abstract is not under a heading called "Abstract".

Open `overrides.csv` in VS Code and add one line per fix. The columns are `file, id, title, year, abstract`. Fill in only what you want to change and leave the other cells empty:

```
file,id,title,year,abstract
FYP-12-4.pdf,,,2023,
FYP-15-2.pdf,,A Better Title,,"First paragraph of the abstract.||Second paragraph."
```

- Put `||` between paragraphs of an abstract.
- Lines beginning with `#` are comments and are ignored.
- If an abstract contains a comma, keep the whole abstract inside double quotes as shown.

Run `python build.py` again and check the table.

**About the year:** the page uses the year on the cover page. If you would rather group by academic year, put the year you want in the `year` column.

---

## 6. Putting it on the real server

Ask ICT for just this:

> A web server (Apache, Nginx or IIS) on the dedicated IP address, serving a single folder of **static files**, plus a way for me to copy files into that folder (SFTP or a shared folder).

The site needs **no database, no PHP and no Python on the server**. Python is only used on your own computer to create `index.html`. Copy these two things into the server folder and nothing else:

- `index.html`
- the `reports` folder

---

## 7. Test reports – delete before going live

`reports/` currently has 12 reports:
- `FYP-19-8.pdf` and `FYP-20-24.pdf` are the real samples you gave me.
- The other ten are **fictional**, made only for testing (they say so at the bottom of every page). Before the page goes public, delete those ten PDFs and run `python build.py`.

---

## 8. Understanding build.py a little (for learning)

The file is divided into numbered sections with comments. Some ideas used in it:

- **Regular expressions** (`re.compile(...)`) are search patterns. For example `FYP\s*-?\s*(\d+)\s*-\s*(\d+)` means "the letters FYP, an optional dash or space, a number, a dash, another number". That one pattern finds both `FYP-19-8` and `FYP 20-24`.
- **A list of lines** is what we get when we read a page of a PDF. Most of the code is deciding which lines belong to the abstract: it starts after the line that says only "Abstract", and stops at a heading such as "Table of Contents".
- **A dictionary** (`{"id": ..., "title": ...}`) holds the facts about each project, and the page is then built by looping over them, grouped by year.

Good beginner exercises: change `PAGE_TITLE`, change a colour in `template.html`, then run `python build.py` and refresh the browser.
