import unittest
from tools.import_lsg import parse_book, clean, spans

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

    def test_reading_structure_keeps_headings_paragraphs_poetry_and_red_letters(self):
        source = r'''\id MAT
\c 1
\s1 Une section
\p
\v 1 Avant. \wj Parole de Jésus.\wj* Après.
\q1
\v 2 Une ligne poétique.
'''
        flat, document = parse_book(source, structured=True)
        self.assertEqual(flat['1'][1], 'Avant. Parole de Jésus. Après.')
        self.assertEqual([block['type'] for block in document['1']],
                         ['heading', 'paragraph', 'poetry'])
        self.assertEqual(document['1'][0]['text'], 'Une section')
        self.assertEqual(document['1'][1]['content'][0]['segments'], [
            {'text': 'Avant.', 'red': False},
            {'text': 'Parole de Jésus.', 'red': True},
            {'text': 'Après.', 'red': False},
        ])

    def test_inline_structure_discards_notes_and_word_metadata(self):
        value = (r'Jésus dit: \wj \+w Venez|strong="G2064"\+w*.\wj* '
                 r'\x a \xo 1.2 \xt Jean 1:1\x* Ensuite.')
        self.assertEqual(spans(value), [
            {'text': 'Jésus dit:', 'red': False},
            {'text': 'Venez.', 'red': True},
            {'text': 'Ensuite.', 'red': False},
        ])
