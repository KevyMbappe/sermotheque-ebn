import unittest
from tools.import_lsg import parse_book, clean

class ImportLSGTest(unittest.TestCase):
    def test_verse_text_keeps_poetry_and_discards_editorial_material(self):
        source = r'''\id GEN
\ip Introduction à ne pas importer
\c 1
\s1 Titre éditorial
\v 1 Au \w commencement|strong="H7225"\w*, Dieu créa.
\q1 Suite poétique du verset.
\r Référence éditoriale
\p
\v 2 La terre.\x a \xo 1.2 \xt Jean 1:1\x*
\s1 Autre titre
'''
        self.assertEqual(parse_book(source), {'1': {1:'Au commencement, Dieu créa. Suite poétique du verset.', 2:'La terre.'}})

    def test_nested_word_markup_keeps_scripture_word(self):
        self.assertEqual(clean(r'\qs \+w Pause|strong="H5542"\+w*\qs*'), 'Pause')

    def test_unknown_markup_fails_instead_of_corrupting_text(self):
        with self.assertRaises(ValueError): clean(r'Texte \unknown annotation')
