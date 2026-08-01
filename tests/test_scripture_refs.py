"""In-body scripture citations → OSIS (decision #56). Offline, deterministic, pure stdlib.

`scripture_refs` is free French text written by the LLM ("Jean 1:1,14", "Genèse 9-10",
"Luc 15 (fils prodigue)"). `parse_reference` / `normalize_refs` turn it into OSIS ids so an
inverted index ("which sermons cite Romains 8?") becomes possible. The rule under test
throughout: never guess — an unrecognised book yields [], it is not invented.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from scripture import BOOKS, normalize_refs, parse_reference  # noqa: E402
from enrichment_store import DERIVED_FIELDS, apply, derive, extract  # noqa: E402


class TestSimpleCitations(unittest.TestCase):
    def test_chapter_and_verse(self):
        self.assertEqual(parse_reference("Jean 3:16"), ["John.3.16"])

    def test_verse_range(self):
        self.assertEqual(parse_reference("Romains 8:28-30"),
                         ["Rom.8.28-Rom.8.30"])

    def test_chapter_only(self):
        self.assertEqual(parse_reference("Romains 8"), ["Rom.8"])

    def test_cross_chapter_range(self):
        self.assertEqual(parse_reference("1 Corinthiens 11:23-12:31"),
                         ["1Cor.11.23-1Cor.12.31"])

    def test_numbered_and_abbreviated_books(self):
        self.assertEqual(parse_reference("1 Timothée 3:14-16"), ["1Tim.3.14-1Tim.3.16"])
        self.assertEqual(parse_reference("2 Tim 4:2"), ["2Tim.4.2"])
        self.assertEqual(parse_reference("1 Jean 4:19"), ["1John.4.19"])

    def test_english_book_names(self):
        self.assertEqual(parse_reference("Romans 8:28"), ["Rom.8.28"])
        self.assertEqual(parse_reference("James 1:2-4"), ["Jas.1.2-Jas.1.4"])


class TestAwkwardShapes(unittest.TestCase):
    """The shapes that make a naive title parser produce silently wrong OSIS."""

    def test_chapter_range_is_not_a_verse(self):
        # "Genèse 9-10" = chapters 9 to 10 — NOT Gen.9.10, which is what a
        # two-numbers-means-chapter-and-verse reading would give.
        self.assertEqual(parse_reference("Genèse 9-10"), ["Gen.9-Gen.10"])
        self.assertEqual(parse_reference("1 Corinthiens 12-14"), ["1Cor.12-1Cor.14"])

    def test_verse_list_becomes_several_ids(self):
        self.assertEqual(parse_reference("Jean 1:1,14"), ["John.1.1", "John.1.14"])

    def test_mixed_list_of_ranges_and_single_verses(self):
        # real string from data/catalog/enrichment.json
        self.assertEqual(
            parse_reference("Lévitique 26:1-2,14-15,29,36,40-45"),
            ["Lev.26.1-Lev.26.2", "Lev.26.14-Lev.26.15", "Lev.26.29", "Lev.26.36",
             "Lev.26.40-Lev.26.45"])

    def test_dot_separator(self):
        self.assertEqual(parse_reference("Josué 1.8"), ["Josh.1.8"])          # real string
        self.assertEqual(parse_reference("Philippiens 2.5-11"), ["Phil.2.5-Phil.2.11"])

    def test_french_ref_vocabulary(self):
        self.assertEqual(parse_reference("Galates Ch. 2 v 11 à 16"), ["Gal.2.11-Gal.2.16"])
        self.assertEqual(parse_reference("Galates chapitre 5 versets 22-23"),
                         ["Gal.5.22-Gal.5.23"])
        self.assertEqual(parse_reference("Genèse 1 et 2"), ["Gen.1", "Gen.2"])

    def test_several_books_in_one_string(self):
        self.assertEqual(parse_reference("Romains 8 et Éphésiens 2"), ["Rom.8", "Eph.2"])

    def test_single_chapter_books_count_verses_not_chapters(self):
        # Jude/Philémon/2-3 Jean/Abdias have one chapter: "Jude 24-25" = verses.
        self.assertEqual(parse_reference("Jude 24-25"), ["Jude.1.24-Jude.1.25"])
        self.assertEqual(parse_reference("Jude 1:12"), ["Jude.1.12"])        # real string
        self.assertEqual(parse_reference("Philémon 6"), ["Phlm.1.6"])

    def test_book_only_allusion_yields_a_book_level_id(self):
        # "Hébreux (référence au sabbat…)" — no chapter given; the book is still indexable.
        self.assertEqual(parse_reference("Apocalypse"), ["Rev"])
        self.assertEqual(parse_reference("Actes des Apôtres"), ["Acts"])
        self.assertEqual(parse_reference("Galates (allusion)"), ["Gal"])


class TestParentheticals(unittest.TestCase):
    def test_gloss_is_stripped_not_parsed(self):
        self.assertEqual(parse_reference("Luc 15 (fils prodigue)"), ["Luke.15"])
        self.assertEqual(parse_reference("Genèse 9-10 (Sem, Cham, Japhet)"), ["Gen.9-Gen.10"])
        self.assertEqual(parse_reference("1 Rois 21 (Akab et Jézabel)"), ["1Kgs.21"])

    def test_a_parenthetical_that_is_itself_a_citation_is_kept(self):
        self.assertEqual(parse_reference("Jean 4:19 (1 Jean 4:19)"),
                         ["John.4.19", "1John.4.19"])

    def test_gloss_numbers_never_leak_into_the_reference(self):
        self.assertEqual(parse_reference("Ésaïe 53 (chant du serviteur, 4e)"), ["Isa.53"])


class TestNegatives(unittest.TestCase):
    """Nothing recognisable → nothing emitted. These are the cases we must NOT guess."""

    def test_no_bible_book(self):
        self.assertEqual(parse_reference("Le sermon sur la montagne"), [])
        self.assertEqual(parse_reference("Confession de foi de 1689, ch. 8"), [])
        self.assertEqual(parse_reference("3:16"), [])

    def test_book_name_inside_another_word_is_not_a_book(self):
        self.assertEqual(parse_reference("Jean-Baptiste"), [])
        self.assertEqual(parse_reference("Saint-Jean 3:16"), [])
        self.assertEqual(parse_reference("Marché de Noël"), [])

    def test_empty_and_non_string_inputs(self):
        for bad in ("", "   ", None, 42, ["Jean 3:16"]):
            self.assertEqual(parse_reference(bad), [])

    def test_unparseable_numeric_segment_is_skipped_not_invented(self):
        # "2  11" (two numbers, no separator) is ambiguous: chapter 2 verse 11? chapters 2 and
        # 11? The segment is dropped rather than guessed — only the book survives.
        self.assertEqual(parse_reference("Galates 2  11"), ["Gal"])


class TestNormalizeRefs(unittest.TestCase):
    def test_order_of_first_appearance_is_preserved(self):
        self.assertEqual(normalize_refs(["Romains 8:28", "Jean 1:14", "Genèse 1"]),
                         ["Rom.8.28", "John.1.14", "Gen.1"])

    def test_duplicates_collapse_across_different_spellings(self):
        self.assertEqual(normalize_refs(["Psaume 23:1", "Psaumes 23:1", "Psalm 23:1"]),
                         ["Ps.23.1"])

    def test_failures_are_dropped_and_the_rest_survives(self):
        self.assertEqual(normalize_refs(["Jean 3:16", "un texte sans référence", "Actes 2"]),
                         ["John.3.16", "Acts.2"])

    def test_empty_input(self):
        self.assertEqual(normalize_refs(None), [])
        self.assertEqual(normalize_refs([]), [])


class TestDerivedFieldWiring(unittest.TestCase):
    def test_writeback_derives_the_osis_field(self):
        rows = [{"id": "sc-1", "topics": []}]
        store = {"sc-1": {"scripture_refs": ["Jean 1:1,14", "Romains 8:28-30"]}}
        out, merged = apply(rows, store)
        self.assertEqual(merged, 1)
        self.assertEqual(out[0]["scripture_refs"], ["Jean 1:1,14", "Romains 8:28-30"])
        self.assertEqual(out[0]["scripture_refs_osis"],
                         ["John.1.1", "John.1.14", "Rom.8.28-Rom.8.30"])

    def test_rows_without_enrichment_do_not_get_the_field(self):
        rows = [{"id": "sc-2", "topics": []}]
        apply(rows, {})
        self.assertNotIn("scripture_refs_osis", rows[0])

    def test_derived_field_is_never_persisted_in_the_store(self):
        # It is re-derived on every build; a stored copy could outlive the normaliser (#56).
        e = {"id": "sc-1", "scripture_refs": ["Jean 3:16"], "scripture_refs_osis": ["STALE"]}
        self.assertNotIn("scripture_refs_osis", extract(e))
        self.assertEqual(derive(e)["scripture_refs_osis"], ["John.3.16"])

    def test_stale_derived_value_is_overwritten_on_rebuild(self):
        rows = [{"id": "sc-1", "scripture_refs_osis": ["STALE"]}]
        apply(rows, {"sc-1": {"scripture_refs": ["Actes 2:38"]}})
        self.assertEqual(rows[0]["scripture_refs_osis"], ["Acts.2.38"])

    def test_derived_fields_are_declared(self):
        self.assertEqual(DERIVED_FIELDS, ("scripture_refs_osis",))


class TestLiveCatalog(unittest.TestCase):
    """The committed dataset must actually satisfy what the parser promises."""

    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT / "data" / "catalog" / "catalog.json")
                              .read_text(encoding="utf-8"))
        cls.enriched = [r for r in cls.rows if r.get("scripture_refs_osis") is not None]

    def test_every_enriched_row_carries_the_derived_field(self):
        with_refs = [r for r in self.rows if r.get("scripture_refs")]
        self.assertTrue(with_refs)
        for r in with_refs:
            self.assertIsInstance(r.get("scripture_refs_osis"), list, r["id"])

    def test_every_emitted_id_is_a_well_formed_osis_id(self):
        import re
        books = set(BOOKS.values())
        pat = re.compile(r"[A-Za-z0-9]+(?:\.\d+){0,2}(?:-[A-Za-z0-9]+(?:\.\d+){0,2})?$")
        for r in self.enriched:
            for osis in r["scripture_refs_osis"]:
                self.assertRegex(osis, pat, f"{r['id']}: {osis}")
                for part in osis.split("-"):
                    self.assertIn(part.split(".")[0], books, f"{r['id']}: {osis}")

    def test_ids_are_deduplicated_within_a_row(self):
        for r in self.enriched:
            ids = r["scripture_refs_osis"]
            self.assertEqual(len(ids), len(set(ids)), r["id"])

    def test_the_field_is_reproducible_from_the_stored_free_text(self):
        # No hand-edits, no drift: the committed value is exactly what the parser produces.
        for r in self.enriched:
            self.assertEqual(r["scripture_refs_osis"],
                             normalize_refs(r.get("scripture_refs")), r["id"])

    def test_body_citations_reach_more_books_than_the_primary_scripture(self):
        # The whole point of the field: 22 books via `scripture_book` on the enriched rows,
        # far more once in-body citations are indexable.
        body = {i.split(".")[0] for r in self.enriched for i in r["scripture_refs_osis"]}
        primary = {r["scripture_book"] for r in self.enriched if r.get("scripture_book")}
        self.assertGreater(len(body), len(primary))
        self.assertGreaterEqual(len(body), 50)


if __name__ == "__main__":
    unittest.main()
