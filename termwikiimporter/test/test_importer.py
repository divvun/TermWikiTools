# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikiimporter import importer


class TestExpressionInfo(unittest.TestCase):
    def test_str_is_typo_false(self):
        e = importer.ExpressionInfo(expression=u'test1',
                                    language=u'se',
                                    is_typo=False,
                                    has_illegal_char=True,
                                    collection=u'Example coll',
                                    wordclass=u'N',
                                    sanctioned=True)
        want = [
            u'{{Related_expression',
            u'|expression=test1',
            u'|language=se',
            u'|has_illegal_char=Yes',
            u'|collection=Example coll',
            u'|wordclass=N',
            u'|sanctioned=Yes',
            u'}}']

        self.assertEqual(u'\n'.join(want), str(e))

    def test_str_has_illegal_char_is_false(self):
        e = importer.ExpressionInfo(expression=u'test1',
                                    language=u'se',
                                    is_typo=True,
                                    has_illegal_char=False,
                                    collection=u'Example coll',
                                    wordclass=u'N',
                                    sanctioned=True)
        want = [
            u'{{Related_expression',
            u'|expression=test1',
            u'|language=se',
            u'|is_typo=Yes',
            u'|collection=Example coll',
            u'|wordclass=N',
            u'|sanctioned=Yes',
            u'}}']

        self.assertEqual(u'\n'.join(want), str(e))


class TestConcept(unittest.TestCase):
    def setUp(self):
        self.concept = importer.Concept(u'TestCategory')

    def add_expression(self):
        uff = {
            u'se': [u'sámi1', u'sámi2'],
            u'nb': [u'norsk1']}
        for lang, expressions in uff.items():
            for expression in expressions:
                self.concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=False,
                                            collection=u'Example coll',
                                            wordclass=u'N',
                                            sanctioned=True))

    def add_concept_info(self):
        self.concept.add_concept_info(u'definition_se', u'definition1')

    def test_add_concept_info(self):
        self.add_concept_info()

        self.assertEqual(self.concept.concept_info[u'definition_se'],
                         set([u'definition1']))

    def add_page(self):
        self.concept.add_page(u'8')
        self.concept.add_page(u'9')

    def test_add_page(self):
        self.add_page()

        self.assertEqual(self.concept.pages, set([u'8', u'9']))

    def test_get_expression_set(self):
        self.add_concept_info()
        self.add_expression()
        self.add_page()

        self.assertSetEqual(set([u'sámi1', u'sámi2']),
                            self.concept.get_expressions_set(u'se'))

    def test_string(self):
        self.maxDiff = None
        self.add_concept_info()
        self.add_expression()
        self.add_page()

        concept = [
            u'{{Concept',
            u'|definition_se=definition1',
            u'|duplicate_pages=[8], [9]',
            u'}}',
            u'{{Related_expression',
            u'|expression=norsk1',
            u'|language=nb',
            u'|collection=Example coll',
            u'|wordclass=N',
            u'|sanctioned=Yes',
            u'}}',
            u'{{Related_expression',
            u'|expression=sámi1',
            u'|language=se',
            u'|collection=Example coll',
            u'|wordclass=N',
            u'|sanctioned=Yes',
            u'}}',
            u'{{Related_expression',
            u'|expression=sámi2',
            u'|language=se',
            u'|collection=Example coll',
            u'|wordclass=N',
            u'|sanctioned=Yes',
            u'}}',
        ]

        got = unicode(self.concept)
        self.assertEqual(u'\n'.join(concept), got)

    def test_is_empty1(self):
        '''Both expressions and concept_info are empty'''
        self.assertTrue(self.concept.is_empty)

    def test_is_empty2(self):
        '''concept_info is empty'''
        self.add_expression()
        self.assertFalse(self.concept.is_empty)

    def test_is_empty3(self):
        '''expressions is empty'''
        self.add_concept_info()
        self.assertFalse(self.concept.is_empty)

    def test_is_empty4(self):
        '''Both expressions and concept_info are non-empty'''
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
                u'fi': {
                    u'kuulokkeet': set(
                        [u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                         u'Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    u'Brasilia': set(
                        [u'Geografiija:Brasil', u'Geografiija:Brasilia'])
                },
                u'nb': {
                    u'Brasil': set(
                        [u'Geografiija:Brasilia', u'Geografiija:Brasil']),
                    u'hodesett': set(
                        [u'Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    u'hodetelefoner': set(
                        [u'Dihtorteknologiija ja diehtoteknihkka:belljosat',
                         u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna'])
                },
                u'se': {
                    u'Brasil': set(
                        [u'Geografiija:Brasilia', u'Geografiija:Brasil']),
                    u'Brasilia': set(
                        [u'Geografiija:Brasilia', u'Geografiija:Brasil']),
                    u'bealjoštelefovdna': set(
                        [u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna']),
                    u'belljosat': set(
                        [u'Dihtorteknologiija ja diehtoteknihkka:belljosat'])
                }
            })

    def test_page_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.pages,
            {
                u'Dihtorteknologiija ja diehtoteknihkka:belljosat': {
                    u'fi': {u'kuulokkeet'},
                    u'nb': {u'hodetelefoner', u'hodesett'},
                    u'se': {u'belljosat'}
                },
                u'Geografiija:Brasil': {
                    u'fi': {u'Brasilia'},
                    u'nb': {u'Brasil'},
                    u'se': {u'Brasil', u'Brasilia'}
                },
                u'Geografiija:Brasilia': {
                    u'fi': {u'Brasilia'},
                    u'nb': {u'Brasil'},
                    u'se': {u'Brasil', u'Brasilia'}
                },
                u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna': {
                    u'fi': {u'kuulokkeet'},
                    u'nb': {u'hodetelefoner'},
                    u'se': {u'bealjoštelefovdna'}
                }
            })

    def test_get_expressions_set(self):
        want = collections.defaultdict(set)
        want[u'fi'].update(set([u'kuulokkeet', u'Brasilia']))
        want[u'nb'].update(set([u'hodetelefoner', u'hodesett', u'Brasil']))
        want[u'se'].update(set([u'belljosat', u'Brasil', u'Brasilia',
                               u'bealjoštelefovdna']))

        for lang in self.termwiki.expressions.keys():
            self.assertSetEqual(want[lang],
                                self.termwiki.get_expressions_set(lang))

    def test_get_pages_where_concept_probably_exists1(self):
        '''No common expressions'''
        concept = importer.Concept(u'TestCategory')
        uff = {
            u'se': [u'sámi1', u'sámi2'],
            u'nb': [u'norsk1']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection=u'Example coll',
                                            wordclass=u'N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists2(self):
        '''Common expressions in one language'''
        concept = importer.Concept(u'TestCategory')
        uff = {
            u'se': [u'Brasil', u'sámi2'],
            u'nb': [u'norsk1', u'norsk2']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection=u'Example coll',
                                            wordclass=u'N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists3(self):
        '''Common expressions in two languages'''
        concept = importer.Concept(u'TestCategory')
        uff = {
            u'se': [u'bealjoštelefovdna', u'belljosat'],
            u'nb': [u'norsk1', u'hodetelefoner']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection=u'Example coll',
                                            wordclass=u'N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set([u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                 u'Dihtorteknologiija ja diehtoteknihkka:belljosat']))

    def test_pagenames(self):
        '''Check if the property pagenames returns what it is supposed to'''
        self.assertEqual(self.termwiki.pagenames,
                         [u'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                          u'Dihtorteknologiija ja diehtoteknihkka:belljosat',
                          u'Geografiija:Brasil',
                          u'Geografiija:Brasilia'])


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

        concept = importer.Concept(u'TestCategory')
        uff = {
            u'fi': [u'suomi'],
            u'nb': [u'norsk'],
            u'se': [u'davvisámegiella']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=False,
                                            collection=u'simple',
                                            wordclass=u'N',
                                            sanctioned=True))
                concept.add_concept_info(u'explanation_nb', u'Dette er forklaringen')

        ei.get_concepts()
        got = ei.concepts
        got_concept = got[0]
        self.assertEqual(len(got), 1)
        self.assertDictEqual(got_concept.concept_info, concept.concept_info)
        self.assertEqual(sorted(got_concept.expressions), sorted(concept.expressions))

    def test_collect_expressions_test_splitters(self):
        '''Test if legal split chars work as splitters'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in [u'a, b', u'a; b', u'a\nb', u'a/b']:
            got = ei.collect_expressions(startline, u'se', counter, collection=u'example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression=u'a',
                        language=u'se',
                        is_typo=False,
                        has_illegal_char=False,
                        collection=u'example',
                        wordclass=u'N/A',
                        sanctioned=True),
                    importer.ExpressionInfo(
                        expression=u'b',
                        language=u'se',
                        is_typo=False,
                        has_illegal_char=False,
                        collection=u'example',
                        wordclass=u'N/A',
                        sanctioned=True),
                ], got)

    def test_collect_expressions_illegal_chars(self):
        '''Check that illegal chars in startline is handled correctly'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in u'()-~?':
            got = ei.collect_expressions(startline, u'se', counter, collection=u'example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression=startline,
                        language=u'se',
                        is_typo=False,
                        has_illegal_char=True,
                        collection=u'example',
                        wordclass=u'N/A',
                        sanctioned=False),
                ], got)

    def test_collect_expressions_illegal_chars_with_newline(self):
        '''Check that illegal chars in startline is handled correctly'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        startline = u'a-a;\nb=b;\nc?c'
        got = ei.collect_expressions(startline, u'se', counter, collection=u'example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression=startline.replace(u'\n', u' '),
                    language=u'se',
                    is_typo=False,
                    has_illegal_char=True,
                    collection=u'example',
                    wordclass=u'N/A',
                    sanctioned=False),
            ], got)

    def test_collect_expressions_multiword_expression(self):
        '''Handle multiword expression'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions(u'a b', u'se', counter, collection=u'example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression=u'a b',
                    language=u'se',
                    is_typo=False,
                    has_illegal_char=False,
                    collection=u'example',
                    wordclass=u'MWE',
                    sanctioned=True),
            ], got)

    def test_collect_expressions_typo(self):
        '''Handle typo expression'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions(u'asdfg', u'se', counter, collection=u'example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression=u'asdfg',
                    language=u'se',
                    is_typo=True,
                    has_illegal_char=False,
                    collection=u'example',
                    wordclass=u'N/A',
                    sanctioned=False),
            ], got)
