# -*- coding: utf-8 -*-

import collections
import os
import unittest
import sys

from termwikiimporter import importer


class TestExpressionInfos(unittest.TestCase):
    def setUp(self):
        self.infos = importer.ExpressionInfos()
        self.infos.pos = 'N'

        self.info1 = importer.ExpressionInfo(expression='test1',
                                             language='se',
                                             collection='Example coll',
                                             status='',
                                             note='',
                                             source='',
                                             sanctioned='Yes')

        self.info2 = importer.ExpressionInfo(expression='test2',
                                             language='se',
                                             collection='Example coll',
                                             status='',
                                             note='',
                                             source='',
                                             sanctioned='Yes')

        self.want1 = [
            '{{Related expression',
            '|language=se',
            '|expression=test1',
            '|pos=N',
            '|sanctioned=Yes',
            '|collection=Example coll',
            '}}']

        self.want2 = [
            '{{Related expression',
            '|language=se',
            '|expression=test2',
            '|pos=N',
            '|sanctioned=Yes',
            '|collection=Example coll',
            '}}']

    def test_str_multiple_related_expressions(self):
        self.infos.add_expression(self.info1)
        self.infos.add_expression(self.info2)

        want = []
        want.extend(self.want1)
        want.extend(self.want2)

        #print(('\n'.join(want)))
        #print((str(self.infos)))
        self.assertEqual('\n'.join(want), str(self.infos))

    def test_pos_default(self):
        infos = importer.ExpressionInfos()

        self.assertEqual(infos.pos, 'N/A')

    def test_pos_set(self):
        infos = importer.ExpressionInfos()
        infos.pos = 'N'

        self.assertEqual(infos.pos, 'N')

    def test_pos_set_conflicting(self):
        infos = importer.ExpressionInfos()
        infos.pos = 'N'

        with self.assertRaises(importer.ExpressionError):
            infos.pos = 'ABBR'

    def test_pos_set_illegal(self):
        infos = importer.ExpressionInfos()

        with self.assertRaises(importer.ExpressionError):
            infos.pos = 'bogus'

    def test_pos_set_mwe(self):
        infos = importer.ExpressionInfos()
        infos.pos = 'N'

        infos.pos = 'MWE'

        self.assertEqual(infos.pos, 'N')

    def test_pos_set_na(self):
        infos = importer.ExpressionInfos()
        infos.pos = 'N'

        infos.pos = 'N/A'

        self.assertEqual(infos.pos, 'N')


class TestRelatedConceptInfo(unittest.TestCase):
    def test_related_concept_str(self):
        rc = importer.RelatedConceptInfo(concept='Boazodoallu:duottarmiessi',
                                         relation='cohyponym')
        want = [
            '{{Related concept',
            '|concept=Boazodoallu:duottarmiessi',
            '|relation=cohyponym',
            '}}']

        self.assertEqual('\n'.join(want), str(rc))


class TestConcept(unittest.TestCase):
    def setUp(self):
        self.concept = importer.Concept(main_category='TestCategory')
        self.concept.expression_infos.pos = 'N'

    def add_expression(self):
        uff = {
            'se': ['sámi1', 'sámi2'],
            'nb': ['norsk1']}
        for lang, expressions in sorted(list(uff.items())):
            for expression in expressions:
                self.concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            collection='Example coll',
                                            status='',
                                            note='',
                                            source='',
                                            sanctioned='Yes'))

    def add_concept_info(self):
        self.concept.add_concept_info('definition_se', 'definition1')

    def test_add_concept_info(self):
        self.add_concept_info()

        self.assertEqual(self.concept.concept_info['definition_se'],
                         set(['definition1']))

    def add_page(self):
        self.concept.add_page('8')
        self.concept.add_page('9')

    def add_related_concept(self):
        self.concept.add_related_concept(
            importer.RelatedConceptInfo(concept='Boazodoallu:duottarmiessi',
                                        relation='cohyponym'))

    def test_add_page(self):
        self.add_page()

        self.assertEqual(self.concept.pages, set(['8', '9']))

    def test_get_expression_set(self):
        self.add_concept_info()
        self.add_expression()
        self.add_page()

        self.assertSetEqual(set(['sámi1', 'sámi2']),
                            self.concept.get_expressions_set('se'))

    def test_string(self):
        self.maxDiff = None
        self.add_concept_info()
        self.add_expression()
        self.add_related_concept()
        self.add_page()

        concept = [
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related expression',
            '|language=nb',
            '|expression=norsk1',
            '|pos=N',
            '|sanctioned=Yes',
            '|collection=Example coll',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=sámi1',
            '|pos=N',
            '|sanctioned=Yes',
            '|collection=Example coll',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=sámi2',
            '|pos=N',
            '|sanctioned=Yes',
            '|collection=Example coll',
            '}}',
            '{{Related concept',
            '|concept=Boazodoallu:duottarmiessi',
            '|relation=cohyponym',
            '}}'
        ]

        got = str(self.concept)
        self.assertEqual('\n'.join(concept), got)

    def test_is_empty1(self):
        """Both expressions and concept_info are empty."""
        self.assertTrue(self.concept.is_empty)

    def test_is_empty2(self):
        """concept_info is empty."""
        self.add_expression()
        self.assertFalse(self.concept.is_empty)

    def test_is_empty3(self):
        """expressions is empty."""
        self.add_concept_info()
        self.assertFalse(self.concept.is_empty)

    def test_is_empty4(self):
        """Both expressions and concept_info are non-empty."""
        self.add_concept_info()
        self.add_expression()
        self.assertFalse(self.concept.is_empty)


class TestExcelImporter(unittest.TestCase):
    def setUp(self):
        self.termwiki = TermWikiWithTestSource()
        self.termwiki.get_expressions()
        self.termwiki.get_pages()

    def test_get_concepts(self):
        self.maxDiff = None
        filename = os.path.join(os.path.dirname(__file__), 'excel',
                                'simple.xlsx')
        ei = importer.ExcelImporter(filename, self.termwiki)

        concept = {
            'concept': {
                'main_category': 'Servodatdieđa',
                'collection': set(),
            },
            'concept_infos': [
                {
                    'explanation': 'Dette er forklaringen',
                    'language': 'nb',
                },
            ],
            'related_expressions': [
                {
                    'expression': 'davvisámegiella',
                    'language': 'se',
                    'pos': 'N',
                },
                {
                    'expression': 'suomi',
                    'language': 'fi',
                    'pos': 'N',
                },
                {
                    'expression': 'norsk',
                    'language': 'nb',
                    'pos': 'N',
                },
            ]
        }
        concept['concept']['collection'].add('simple')
        ei.get_concepts()
        got = ei.concepts
        got_concept = got[0]

        self.assertDictEqual(got_concept['concept'], concept['concept'])
        for concept_info in got_concept['concept_infos']:
            self.assertTrue(concept_info in concept['concept_infos'])
        for related_expression in got_concept['related_expressions']:
            self.assertTrue(
                related_expression in concept['related_expressions'])

    def test_collect_expressions_test_splitters(self):
        """Test if legal split chars work as splitters."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in ['a, b', 'a; b', 'a\nb', 'a/b']:
            got = ei.collect_expressions(startline)

            self.assertEqual(['a','b'], got)

    def test_collect_expressions_illegal_chars(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for x, startline in enumerate('()-~?'):
            got = ei.collect_expressions(startline)

            self.assertEqual([startline], got)

    def test_collect_expressions_illegal_chars_with_newline(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        startline = 'a-a;\nb=b;\nc?c'
        got = ei.collect_expressions(startline)

        self.assertEqual([startline.replace('\n', ' ')], got)

    def test_collect_expressions_multiword_expression(self):
        """Handle multiword expression."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions('a b')

        self.assertEqual(['a b'], got)
