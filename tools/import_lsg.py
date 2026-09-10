#!/usr/bin/env python3
"""Import the pinned eBible LSG USFM archive. No network access during app builds.
Usage: python3 tools/import_lsg.py /path/to/fraLSG_usfm.zip
Only Scripture verses are imported; introductions, headings, notes and Strong's tags are excluded.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
USFM = 'GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()
OSIS = 'Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'.split()

def clean(text):
    text = re.sub(r'\\(x|f)\s.*?\\\1\*', '', text)
    text = re.sub(r'\\\+?w\s+([^|]*?)\|[^\\]*\\\+?w\*', r'\1', text)
    text = re.sub(r'\\(?:wj|qs|it|ord)\*?\s?', '', text)
    if '\\' in text or 'strong=' in text:
        raise ValueError(f'Unprocessed USFM: {text[:150]}')
    return ' '.join(text.split())

def parse_book(text):
    chapters, current, pieces = {}, None, []
    def flush():
        if current:
            c, v = current
            value = clean(' '.join(pieces))
            if not value or v in chapters[c]:
                raise ValueError(f'Empty or duplicate verse: {current}')
            chapters[c][v] = value
    chapter = None
    for line in text.splitlines():
        m = re.match(r'\\(\w+)\s*(.*)', line)
        if not m:
            if line.strip(): raise ValueError('Unexpected continuation')
            continue
        marker, value = m.groups()
        if marker == 'c':
            flush(); current = None; pieces = []
            chapter = int(value.strip()); chapters[chapter] = {}
        elif marker == 'v':
            flush()
            v, body = value.split(' ', 1)
            current = (chapter, int(v)); pieces = [body]
        elif marker in ('q1', 'p', 'm', 'b', 'pi1') and current:
            pieces.append(value)
        # Everything else is editorial front matter, a heading or cross-reference.
    flush()
    assert list(chapters) == list(range(1, len(chapters) + 1))
    for c, verses in chapters.items():
        assert list(verses) == list(range(1, len(verses) + 1)), (c, list(verses))
    return {str(c): verses for c, verses in chapters.items()}

def main(path):
    archive = Path(path)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    destination = ROOT / 'data/bible/lsg'
    metadata_path = destination / 'manifest.json'
    if metadata_path.exists():
        expected = json.loads(metadata_path.read_text())['source_sha256']
        if digest != expected: raise ValueError('Source checksum changed; review the edition before importing')
    books = {}
    with zipfile.ZipFile(archive) as z:
        for code, osis in zip(USFM, OSIS):
            names = [n for n in z.namelist() if n.endswith(f'-{code}fraLSG.usfm')]
            assert len(names) == 1, code
            books[osis] = parse_book(z.read(names[0]).decode('utf-8-sig'))
    destination.mkdir(parents=True, exist_ok=True)
    for osis, chapters in books.items():
        (destination / f'{osis}.json').write_text(json.dumps(chapters, ensure_ascii=False, indent=2) + '\n')
    manifest = dict(edition='LSG 1910', language='fr', source='https://ebible.org/Scriptures/fraLSG_usfm.zip',
        source_sha256=digest, source_date='2026-08-08', imported='2026-09-10',
        copyright='Public domain', copyright_url='https://ebible.org/fraLSG/copyright.htm',
        books={b: [len(v) for v in chapters.values()] for b, chapters in books.items()})
    metadata_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(books)} books; {sum(len(c) for c in books.values())} chapters; {sum(sum(map(len,c.values())) for c in books.values())} verses')

if __name__ == '__main__': main(sys.argv[1])
