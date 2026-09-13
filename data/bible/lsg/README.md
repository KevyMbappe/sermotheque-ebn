# Louis Segond 1910 — pinned Bible text

66 books, 1,189 chapters, 31,170 numbered verses. The edition's own numbering is retained,
including Psalm titles that belong to numbered verses. This is a separate reusable text
asset; sermon records remain in `data/catalog/`.

Source: https://ebible.org/Scriptures/fraLSG_usfm.zip (source dated 2026-08-08).
Edition and public-domain notice: https://ebible.org/fraLSG/copyright.htm.
Retrieved 2026-09-10. `manifest.json` records the exact source archive SHA-256.
The original archive contains modern introductions, headings, references and word tags.
The importer retains the numbered Scripture text plus body paragraphs, section headings,
poetry lines, blank divisions and the edition's `\wj` words-of-Jesus spans. Introductions,
parallel references, cross-reference notes and Strong's metadata are excluded. Section
headings and red-letter boundaries are editorial features of this source edition, not part
of the inspired text. Typography and wording are retained; whitespace is normalized.

Reproduce using Python's standard library:

```bash
curl -fL https://ebible.org/Scriptures/fraLSG_usfm.zip -o /tmp/fraLSG_usfm.zip
python3 tools/import_lsg.py /tmp/fraLSG_usfm.zip
```

The importer rejects an archive that differs from the pinned checksum. A new source version
requires an explicit edition review and manifest update. Normal application builds are
fully local and never download a Bible. Each book JSON maps chapter → verse number → text;
its `.structure.json` companion stores ordered reading blocks while retaining verse identity.
`apps/web-poc/scripts/build-bible.mjs` verifies the complete dataset and emits small chapter
files plus per-book sermon indexes. Bad/unsupported references go to the generated
`public/data/bible/reference-issues.json` and are excluded from matching.

OSIS identifiers are interpreted in this LSG edition's numbering. The current catalogue
has no per-reference translation/versification provenance, so automatic remapping from
other editions is deliberately not attempted. Matching means overlap with the recorded
reference, not independently verified exegesis or confirmation of the quoted translation.
