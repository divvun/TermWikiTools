# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikiimporter import importer


class TestExpressionInfos(unittest.TestCase):
    def setUp(self):
        self.infos = importer.ExpressionInfos()
        self.infos.pos = 'N'

        self.info1 = importer.ExpressionInfo(expression='test1',
                                             language='se',
                                             is_typo='No',
                                             has_illegal_char='Yes',
                                             collection='Example coll',
                                             status='',
                                             note='',
                                             equivalence='',
                                             sanctioned='Yes')

        self.info2 = importer.ExpressionInfo(expression='test1',
                                             language='se',
                                             is_typo='Yes',
                                             has_illegal_char='No',
                                             collection='Example coll',
                                             status='',
                                             note='',
                                             equivalence='',
                                             sanctioned='Yes')

        self.want1 = [
            '{{Related expression',
            '|language=se',
            '|expression=test1',
            '|has_illegal_char=Yes',
            '|collection=Example coll',
            '|sanctioned=Yes',
            '|pos=N',
            '}}']

        self.want2 = [
            '{{Related expression',
            '|language=se',
            '|expression=test1',
            '|is_typo=Yes',
            '|collection=Example coll',
            '|sanctioned=Yes',
            '|pos=N',
            '}}']

    def test_str_is_typo_false(self):
        self.infos.add_expression(self.info1)

        self.assertEqual('\n'.join(self.want1), str(self.infos))

    def test_str_has_illegal_char_is_false(self):
        self.infos.add_expression(self.info2)

        self.assertEqual('\n'.join(self.want2), str(self.infos))

    def test_str_multiple_related_expressions(self):
        self.infos.add_expression(self.info1)
        self.infos.add_expression(self.info2)

        want = []
        want.extend(self.want1)
        want.extend(self.want2)

        print(('\n'.join(want)))
        print((str(self.infos)))
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
        for lang, expressions in list(uff.items()):
            for expression in expressions:
                self.concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo='No',
                                            has_illegal_char='No',
                                            collection='Example coll',
                                            status='',
                                            note='',
                                            equivalence='',
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
            '|collection=Example coll',
            '|sanctioned=Yes',
            '|pos=N',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=sámi1',
            '|collection=Example coll',
            '|sanctioned=Yes',
            '|pos=N',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=sámi2',
            '|collection=Example coll',
            '|sanctioned=Yes',
            '|pos=N',
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


class TermWikiWithTestSource(importer.TermWiki):
    @property
    def term_home(self):
        return os.path.join(os.path.dirname(__file__), 'terms')


class TestTermwiki(unittest.TestCase):
    def setUp(self):
        self.termwiki = TermWikiWithTestSource()
        self.termwiki.get_expressions()
        self.termwiki.get_pages()

    def test_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.expressions,
            {
                'fi': {
                    'kuulokkeet': set(
                        ['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                         'Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    'Brasilia': set(
                        ['Geografiija:Brasil', 'Geografiija:Brasilia'])
                },
                'nb': {
                    'Brasil': set(
                        ['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'hodesett': set(
                        ['Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    'hodetelefoner': set(
                        ['Dihtorteknologiija ja diehtoteknihkka:belljosat',
                         'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna'])
                },
                'se': {
                    'Brasil': set(
                        ['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'Brasilia': set(
                        ['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'bealjoštelefovdna': set(
                        ['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna']),
                    'belljosat': set(
                        ['Dihtorteknologiija ja diehtoteknihkka:belljosat'])
                }
            })

    def test_page_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.pages,
            {
                'Dihtorteknologiija ja diehtoteknihkka:belljosat': {
                    'fi': {'kuulokkeet'},
                    'nb': {'hodetelefoner', 'hodesett'},
                    'se': {'belljosat'}
                },
                'Geografiija:Brasil': {
                    'fi': {'Brasilia'},
                    'nb': {'Brasil'},
                    'se': {'Brasil', 'Brasilia'}
                },
                'Geografiija:Brasilia': {
                    'fi': {'Brasilia'},
                    'nb': {'Brasil'},
                    'se': {'Brasil', 'Brasilia'}
                },
                'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna': {
                    'fi': {'kuulokkeet'},
                    'nb': {'hodetelefoner'},
                    'se': {'bealjoštelefovdna'}
                }
            })

    def test_get_expressions_set(self):
        want = collections.defaultdict(set)
        want['fi'].update(set(['kuulokkeet', 'Brasilia']))
        want['nb'].update(set(['hodetelefoner', 'hodesett', 'Brasil']))
        want['se'].update(set(['belljosat', 'Brasil', 'Brasilia',
                               'bealjoštelefovdna']))

        for lang in list(self.termwiki.expressions.keys()):
            self.assertSetEqual(want[lang],
                                self.termwiki.get_expressions_set(lang))

    def test_get_pages_where_concept_probably_exists1(self):
        """No common expressions."""
        concept = importer.Concept(main_category='TestCategory')
        uff = {
            'se': ['sámi1', 'sámi2'],
            'nb': ['norsk1']}
        for lang, expressions in list(uff.items()):
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo='No',
                                            has_illegal_char='Yes',
                                            collection='Example coll',
                                            status='',
                                            note='',
                                            equivalence='',
                                            sanctioned='Yes'))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists2(self):
        """Common expressions in one language."""
        concept = importer.Concept(main_category='TestCategory')
        uff = {
            'se': ['Brasil', 'sámi2'],
            'nb': ['norsk1', 'norsk2']}
        for lang, expressions in list(uff.items()):
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo='No',
                                            has_illegal_char='Yes',
                                            collection='Example coll',
                                            status='',
                                            note='',
                                            equivalence='',
                                            sanctioned='Yes'))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists3(self):
        """Common expressions in two languages."""
        concept = importer.Concept(main_category='TestCategory')
        uff = {
            'se': ['bealjoštelefovdna', 'belljosat'],
            'nb': ['norsk1', 'hodetelefoner']}
        for lang, expressions in list(uff.items()):
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo='No',
                                            has_illegal_char='Yes',
                                            collection='Example coll',
                                            status='',
                                            note='',
                                            equivalence='',
                                            sanctioned='Yes'))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set(['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                 'Dihtorteknologiija ja diehtoteknihkka:belljosat']))

    def test_pagenames(self):
        """Check if the property pagenames returns what it is supposed to."""
        self.assertEqual(self.termwiki.pagenames,
                         ['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                          'Dihtorteknologiija ja diehtoteknihkka:belljosat',
                          'Geografiija:Brasil',
                          'Geografiija:Brasilia'])


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

        concept = importer.Concept(main_category='TestCategory')
        uff = {
            'fi': ['suomi'],
            'nb': ['norsk'],
            'se': ['davvisámegiella']}
        for lang, expressions in list(uff.items()):
            for expression in expressions:
                concept.expression_infos.pos = 'N'
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo='No',
                                            has_illegal_char='No',
                                            collection='simple',
                                            status='',
                                            note='',
                                            equivalence='',
                                            sanctioned='Yes'))
                concept.add_concept_info('explanation_nb', 'Dette er forklaringen')

        ei.get_concepts()
        got = ei.concepts
        got_concept = got[0]
        self.assertEqual(len(got), 1)
        self.assertDictEqual(got_concept.concept_info, concept.concept_info)
        self.assertEqual(sorted(got_concept.expression_infos.expressions),
                         sorted(concept.expression_infos.expressions))
        self.assertEqual(got_concept.expression_infos.pos,
                         concept.expression_infos.pos)

    def test_collect_expressions_test_splitters(self):
        """Test if legal split chars work as splitters."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in ['a, b', 'a; b', 'a\nb', 'a/b']:
            got = ei.collect_expressions(startline, 'se', counter, collection='example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression='a',
                        language='se',
                        is_typo='No',
                        has_illegal_char='No',
                        collection='example',
                        status='',
                        note='',
                        equivalence='',
                        sanctioned='Yes'),
                    importer.ExpressionInfo(
                        expression='b',
                        language='se',
                        is_typo='No',
                        has_illegal_char='No',
                        collection='example',
                        status='',
                        note='',
                        equivalence='',
                        sanctioned='Yes'),
                ], got)

    def test_collect_expressions_illegal_chars(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in '()-~?':
            got = ei.collect_expressions(startline, 'se', counter, collection='example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression=startline,
                        language='se',
                        is_typo='No',
                        has_illegal_char='Yes',
                        collection='example',
                        status='',
                        note='',
                        equivalence='',
                        sanctioned='No'),
                ], got)

    def test_collect_expressions_illegal_chars_with_newline(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        startline = 'a-a;\nb=b;\nc?c'
        got = ei.collect_expressions(startline, 'se', counter, collection='example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression=startline.replace('\n', ' '),
                    language='se',
                    is_typo='No',
                    has_illegal_char='Yes',
                    collection='example',
                    status='',
                    note='',
                    equivalence='',
                    sanctioned='No'),
            ], got)

    def test_collect_expressions_multiword_expression(self):
        """Handle multiword expression."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions('a b', 'se', counter, collection='example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression='a b',
                    language='se',
                    is_typo='No',
                    has_illegal_char='No',
                    collection='example',
                    status='',
                    note='',
                    equivalence='',
                    sanctioned='Yes'),
            ], got)

    def test_collect_expressions_typo(self):
        """Handle typo expression."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions('asdfg', 'se', counter, collection='example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression='asdfg',
                    language='se',
                    is_typo='Yes',
                    has_illegal_char='No',
                    collection='example',
                    status='',
                    note='',
                    equivalence='',
                    sanctioned='No'),
            ], got)
