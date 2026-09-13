#!/usr/bin/env python3
"""Import the pinned eBible LSG USFM archive. No network access during app builds.
Usage: python3 tools/import_lsg.py /path/to/fraLSG_usfm.zip
Numbered Scripture text and its reading structure are imported. Introductions, notes,
cross-references and Strong's metadata are excluded.
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
    return ' '.join(item['text'] for item in spans(text))

def spans(text):
    """Return clean inline text while retaining the source edition's words-of-Jesus spans."""
    text = re.sub(r'\\(x|f)\s.*?\\\1\*', '', text)
    text = re.sub(r'\\\+?w\s+([^|]*?)\|[^\\]*\\\+?w\*', r'\1', text)
    parts, red, out = re.split(r'(\\wj\*?|\\(?:qs|it|ord)\*?)\s*', text), False, []
    for part in parts:
        if not part:
            continue
        if part == r'\wj':
            red = True
        elif part == r'\wj*':
            red = False
        elif part.startswith('\\'):
            continue
        else:
            value = ' '.join(part.split())
            if value:
                if out and out[-1]['red'] == red:
                    out[-1]['text'] += ' ' + value
                else:
                    out.append({'text': value, 'red': red})
    if any('\\' in item['text'] or 'strong=' in item['text'] for item in out):
        raise ValueError(f'Unprocessed USFM: {text[:150]}')
    return out

def parse_book(text, structured=False):
    chapters, documents, current, pieces = {}, {}, None, []
    block = None
    def flush():
        if current:
            c, v = current
            value = clean(' '.join(pieces))
            if not value or v in chapters[c]:
                raise ValueError(f'Empty or duplicate verse: {current}')
            chapters[c][v] = value
    def reading_block(kind='paragraph', level=0):
        nonlocal block
        block = {'type': kind, 'level': level, 'content': []}
        documents[chapter].append(block)
        return block
    def add_run(verse, value):
        nonlocal block
        parsed = spans(value)
        if not parsed:
            return
        if block is None or block['type'] == 'heading':
            reading_block()
        block['content'].append({'verse': verse, 'segments': parsed})
    chapter = None
    for line in text.splitlines():
        m = re.match(r'\\(\w+)\s*(.*)', line)
        if not m:
            if line.strip(): raise ValueError('Unexpected continuation')
            continue
        marker, value = m.groups()
        if marker == 'c':
            flush(); current = None; pieces = []
            chapter = int(value.strip()); chapters[chapter] = {}; documents[chapter] = []; block = None
        elif marker == 'v':
            flush()
            v, body = value.split(' ', 1)
            current = (chapter, int(v)); pieces = [body]
            add_run(int(v), body)
        elif chapter and marker in ('p', 'm', 'pi1', 'q1'):
            kind = 'poetry' if marker == 'q1' else 'paragraph'
            level = 1 if marker in ('q1', 'pi1') else 0
            reading_block(kind, level)
            if current and value:
                pieces.append(value); add_run(current[1], value)
        elif chapter and marker == 'b':
            block = None
            documents[chapter].append({'type': 'break'})
        elif chapter and marker in ('s1', 'ms1'):
            heading = clean(value)
            block = None
            if heading:
                documents[chapter].append({'type': 'heading', 'level': 1 if marker == 'ms1' else 2, 'text': heading})
        # Introductions, parallel references and other editorial metadata are excluded.
    flush()
    assert list(chapters) == list(range(1, len(chapters) + 1))
    for c, verses in chapters.items():
        assert list(verses) == list(range(1, len(verses) + 1)), (c, list(verses))
    flat = {str(c): verses for c, verses in chapters.items()}
    if not structured:
        return flat
    return flat, {str(c): blocks for c, blocks in documents.items()}

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
            books[osis] = parse_book(z.read(names[0]).decode('utf-8-sig'), structured=True)
    destination.mkdir(parents=True, exist_ok=True)
    for osis, (chapters, documents) in books.items():
        (destination / f'{osis}.json').write_text(json.dumps(chapters, ensure_ascii=False, indent=2) + '\n')
        (destination / f'{osis}.structure.json').write_text(json.dumps(documents, ensure_ascii=False, indent=2) + '\n')
    manifest = dict(edition='LSG 1910', language='fr', source='https://ebible.org/Scriptures/fraLSG_usfm.zip',
        source_sha256=digest, source_date='2026-08-08', imported='2026-09-10',
        copyright='Public domain', copyright_url='https://ebible.org/fraLSG/copyright.htm',
        structure='usfm-reading-blocks-v1',
        books={b: [len(v) for v in chapters.values()] for b, (chapters, _documents) in books.items()})
    metadata_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(books)} books; {sum(len(c) for c, _ in books.values())} chapters; {sum(sum(map(len,c.values())) for c, _ in books.values())} verses')

if __name__ == '__main__': main(sys.argv[1])
