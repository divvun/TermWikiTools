# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikiimporter import importer


class TestExpressionInfo(unittest.TestCase):
    def test_str_is_typo_false(self):
        e = importer.ExpressionInfo(expression='test1',
                                    language='se',
                                    is_typo=False,
                                    has_illegal_char=True,
                                    collection='Example coll',
                                    wordclass='N',
                                    sanctioned=True)
        want = [
            '{{Related_expression',
            '|expression=test1',
            '|language=se',
            '|has_illegal_char=Yes',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}']

        self.assertEqual('\n'.join(want), str(e))

    def test_str_has_illegal_char_is_false(self):
        e = importer.ExpressionInfo(expression='test1',
                                    language='se',
                                    is_typo=True,
                                    has_illegal_char=False,
                                    collection='Example coll',
                                    wordclass='N',
                                    sanctioned=True)
        want = [
            '{{Related_expression',
            '|expression=test1',
            '|language=se',
            '|is_typo=Yes',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}']

        self.assertEqual('\n'.join(want), str(e))


class TestConcept(unittest.TestCase):
    def setUp(self):
        self.concept = importer.Concept('TestCategory')

    def add_expression(self):
        uff = {
            'se': ['sámi1', 'sámi2'],
            'nb': ['norsk1']}
        for lang, expressions in uff.items():
            for expression in expressions:
                self.concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=False,
                                            collection='Example coll',
                                            wordclass='N',
                                            sanctioned=True))

    def add_concept_info(self):
        self.concept.add_concept_info('definition_se', 'definition1')

    def test_add_concept_info(self):
        self.add_concept_info()

        self.assertEqual(self.concept.concept_info['definition_se'],
                         set(['definition1']))

    def add_page(self):
        self.concept.add_page('8')
        self.concept.add_page('9')

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
        self.add_page()

        concept = [
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related_expression',
            '|expression=norsk1',
            '|language=nb',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}',
            '{{Related_expression',
            '|expression=sámi1',
            '|language=se',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}',
            '{{Related_expression',
            '|expression=sámi2',
            '|language=se',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}',
        ]

        self.assertEqual('\n'.join(concept), str(self.concept))


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

        for lang in self.termwiki.expressions.keys():
            self.assertSetEqual(want[lang],
                                self.termwiki.get_expressions_set(lang))

    def test_get_pages_where_concept_probably_exists1(self):
        '''No common expressions'''
        concept = importer.Concept('TestCategory')
        uff = {
            'se': ['sámi1', 'sámi2'],
            'nb': ['norsk1']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection='Example coll',
                                            wordclass='N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists2(self):
        '''Common expressions in one language'''
        concept = importer.Concept('TestCategory')
        uff = {
            'se': ['Brasil', 'sámi2'],
            'nb': ['norsk1', 'norsk2']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection='Example coll',
                                            wordclass='N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists3(self):
        '''Common expressions in two languages'''
        concept = importer.Concept('TestCategory')
        uff = {
            'se': ['bealjoštelefovdna', 'belljosat'],
            'nb': ['norsk1', 'hodetelefoner']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=True,
                                            collection='Example coll',
                                            wordclass='N',
                                            sanctioned=True))

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set(['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                 'Dihtorteknologiija ja diehtoteknihkka:belljosat']))

    def test_pagenames(self):
        '''Check if the property pagenames returns what it is supposed to'''
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

        concept = importer.Concept('TestCategory')
        uff = {
            'fi': ['suomi'],
            'nb': ['norsk'],
            'se': ['davvisámegiella']}
        for lang, expressions in uff.items():
            for expression in expressions:
                concept.add_expression(
                    importer.ExpressionInfo(expression=expression,
                                            language=lang,
                                            is_typo=False,
                                            has_illegal_char=False,
                                            collection='simple',
                                            wordclass='N',
                                            sanctioned=True))
                concept.add_concept_info('explanation_nb', 'Dette er forklaringen')

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
        for startline in ['a, b', 'a; b', 'a\nb', 'a/b']:
            got = ei.collect_expressions(startline, 'se', counter, collection='example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression='a',
                        language='se',
                        is_typo=False,
                        has_illegal_char=False,
                        collection='example',
                        wordclass='N/A',
                        sanctioned=True),
                    importer.ExpressionInfo(
                        expression='b',
                        language='se',
                        is_typo=False,
                        has_illegal_char=False,
                        collection='example',
                        wordclass='N/A',
                        sanctioned=True),
                ], got)

    def test_collect_expressions_illegal_chars(self):
        '''Check that illegal chars in startline is handled correctly'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        for startline in '()-':
            got = ei.collect_expressions(startline, 'se', counter, collection='example')

            self.assertEqual(
                [
                    importer.ExpressionInfo(
                        expression=startline,
                        language='se',
                        is_typo=False,
                        has_illegal_char=True,
                        collection='example',
                        wordclass='N/A',
                        sanctioned=False),
                ], got)

    def test_collect_expressions_multiword_expression(self):
        '''Handle multiword expression'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions('a b', 'se', counter, collection='example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression='a b',
                    language='se',
                    is_typo=False,
                    has_illegal_char=False,
                    collection='example',
                    wordclass='MWE',
                    sanctioned=True),
            ], got)

    def test_collect_expressions_typo(self):
        '''Handle typo expression'''
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter('fakename.xlsx', self.termwiki)
        got = ei.collect_expressions('asdfg', 'se', counter, collection='example')

        self.assertEqual(
            [
                importer.ExpressionInfo(
                    expression='asdfg',
                    language='se',
                    is_typo=True,
                    has_illegal_char=False,
                    collection='example',
                    wordclass='N/A',
                    sanctioned=False),
            ], got)
