#!/usr/bin/env python3
"""
Minimal Markdown → styled HTML → PDF converter (pure stdlib + headless Chrome).
Handles the constructs used in our docs: h1/h2, blockquotes, tables, lists,
bold/italic/code/links. Renders UTF-8 (French accents) and emoji correctly.

Usage:  python3 tools/md_to_pdf.py docs/SYNTHESE.md docs/SYNTHESE.pdf
"""
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 17mm 16mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1f2937;
       font-size: 10.5pt; line-height: 1.5; }
h1 { color: #7c2d12; font-size: 22pt; margin: 0 0 2pt; }
h2 { color: #7c2d12; font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1.5px solid #e7d9c9;
     padding-bottom: 3pt; }
em { color: #6b7280; }
a { color: #7c2d12; text-decoration: none; }
strong { color: #111827; }
code { background: #f3efe9; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
blockquote { margin: 8pt 0; padding: 7pt 12pt; background: #faf6f0;
             border-left: 3px solid #c2956a; border-radius: 3px; }
ul { margin: 4pt 0; padding-left: 18pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10pt; }
th { background: #7c2d12; color: #fff; text-align: left; padding: 5pt 8pt; }
td { border-bottom: 1px solid #e5e7eb; padding: 5pt 8pt; vertical-align: top; }
tr:nth-child(even) td { background: #faf7f3; }
"""


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def render(md):
    out, i, lines = [], 0, md.splitlines()
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue
        elif ln.lstrip().startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                out.append(f"<li>{inline(lines[i].lstrip()[2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table>")
            for r, cells in enumerate(rows):
                if r == 1 and all(set(c) <= set("-: ") for c in cells):
                    continue  # separator row
                tag = "th" if r == 0 else "td"
                out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            out.append("</table>")
            continue
        else:
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(out)}</body></html>"


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    htmlc = render(src.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        hp = Path(tmp) / "doc.html"
        hp.write_text(htmlc, encoding="utf-8")
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions", "--no-pdf-header-footer",
               f"--user-data-dir={tmp}/profile", f"--print-to-pdf={dst}", f"file://{hp}"]
        # Headless Chrome sometimes writes the PDF but hangs on exit — cap it and move on.
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            pass
    if not dst.exists() or dst.stat().st_size == 0:
        raise SystemExit("PDF was not produced")
    print(f"Wrote {dst} ({dst.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
