# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikiimporter import importer


class TestExpressionInfo(unittest.TestCase):
    def test_str(self):
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
            '|is_typo=No',
            '|has_illegal_char=Yes',
            '|collection=Example coll',
            '|wordclass=N',
            '|sanctioned=Yes',
            '}}']

        self.assertEqual('\n'.join(want), str(e))


class TestConcept(unittest.TestCase):
    def setUp(self):
        self.concept = importer.Concept()

    def add_expression(self):
        uff = {
            'se': ['sámi1', 'sámi2'],
            'nb': ['norsk1']}
        for lang, expressions in uff:
            for expression in expressions:
                self.concept.add_expression(
                    'se', importer.ExpressionInfo(expression=expression,
                                                  is_typo=False,
                                                  has_illegal_char=True,
                                                  collection='Example coll',
                                                  wordclass='N',
                                                  sanctioned=True))

    def test_add_expression(self):
        self.add_expression()
        self.assertEqual(self.concept.expressions['se'], set([('sámi1'), ('sámi2')]))
        self.assertEqual(self.concept.expressions['nb'], set([('norsk1')]))


    def add_concept_info(self):
        self.concept.add_concept_info('definition_se', 'definition1')

    def test_add_concept_info(self):
        self.add_concept_info()

        self.assertEqual(self.concept.concept_info['definition_se'], set(['definition1']))

    def add_page(self):
        self.concept.add_page('8')

    def test_add_page(self):
        self.add_page()

        self.assertEqual(self.concept.pages, set(['8']))

    def test_string(self):
        self.add_concept_info()
        self.add_expression()
        self.add_page()

        concept = (
            '{{Concept\n'
            '|definition_se=definition1\n'
            '}}\n'
        )

        rel1 = (
            '{{Related_expression\n'
            '|language=nb\n'
            '|expression=norsk1\n'
            '|sanctioned=Yes\n'
            '}}'
        )

        rel2 = (
            '{{Related_expression\n'
            '|language=se\n'
            '|expression=sámi2\n'
            '|sanctioned=Yes\n'
            '}}'
        )

        rel3 = (
            '{{Related_expression\n'
            '|language=se\n'
            '|expression=sámi1\n'
            '|sanctioned=Yes\n'
            '}}'
        )

        self.assertTrue(concept in str(self.concept))
        self.assertTrue(rel1 in str(self.concept))
        self.assertTrue(rel2 in str(self.concept))
        self.assertTrue(rel3 in str(self.concept))


class TestExcelConcept(unittest.TestCase):
    def test_init_default(self):
        ec = importer.ExcelConcept()

        self.assertTupleEqual(ec.excelinfo,
                              ('', '', 0))

    def test_init_set_variables(self):
        ec = importer.ExcelConcept(filename='filename', worksheet='worksheet',
                                   row=10)

        self.assertTupleEqual(ec.excelinfo,
                              ('filename', 'worksheet', 10))


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
            {'fi': {'kuulokkeet': set(['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna', 'Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    'Brasilia': set(['Geografiija:Brasil', 'Geografiija:Brasilia'])},
             'nb': {'Brasil': set(['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'hodesett': set(['Dihtorteknologiija ja diehtoteknihkka:belljosat']),
                    'hodetelefoner': set(['Dihtorteknologiija ja diehtoteknihkka:belljosat', 'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna'])},
             'se': {'Brasil': set(['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'Brasilia': set(['Geografiija:Brasilia', 'Geografiija:Brasil']),
                    'bealjoštelefovdna': set(['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna']),
                    'belljosat': set(['Dihtorteknologiija ja diehtoteknihkka:belljosat'])}
            }
        )

    def test_page_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.pages,
            {'Dihtorteknologiija ja diehtoteknihkka:belljosat':
                 {'fi': {'kuulokkeet'},
                  'nb': {'hodetelefoner', 'hodesett'},
                  'se': {'belljosat'}},
             'Geografiija:Brasil': {
                 'fi': {'Brasilia'},
                 'nb': {'Brasil'},
                 'se': {'Brasil', 'Brasilia'}},
             'Geografiija:Brasilia': {
                 'fi': {'Brasilia'},
                 'nb': {'Brasil'},
                 'se': {'Brasil', 'Brasilia'}},
             'Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna':
                 {'fi': {'kuulokkeet'},
                  'nb': {'hodetelefoner'},
                  'se': {'bealjoštelefovdna'}}})

    def test_get_expressions_set(self):
        want = collections.defaultdict(set)
        want['fi'].update(set(['kuulokkeet', 'Brasilia']))
        want['nb'].update(set(['hodetelefoner', 'hodesett', 'Brasil']))
        want['se'].update(set(['belljosat', 'Brasil', 'Brasilia', 'bealjoštelefovdna']))

        for lang in self.termwiki.expressions.keys():
            self.assertSetEqual(want[lang],
                                self.termwiki.get_expressions_set(lang))

    def test_get_pages_where_concept_probably_exists1(self):
        '''No common expressions'''
        concept = importer.Concept()
        concept.add_expression('se', 'sámi1')
        concept.add_expression('se', 'sámi2')
        concept.add_expression('nb', 'norsk1')
        concept.add_expression('nb', 'norsk1')

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists2(self):
        '''Common expressions in one language'''
        concept = importer.Concept()
        concept.add_expression('se', 'Brasil')
        concept.add_expression('se', 'sámi2')
        concept.add_expression('nb', 'norsk1')
        concept.add_expression('nb', 'norsk1')

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set())

    def test_get_pages_where_concept_probably_exists2(self):
        '''Common expressions in two languages'''
        concept = importer.Concept()
        concept.add_expression('se', 'bealjoštelefovdna')
        concept.add_expression('se', 'belljosat')
        concept.add_expression('nb', 'norsk1')
        concept.add_expression('nb', 'hodetelefoner')

        self.assertSetEqual(
            self.termwiki.get_pages_where_concept_probably_exists(concept),
            set(['Dihtorteknologiija ja diehtoteknihkka:bealjoštelefovdna',
                 'Dihtorteknologiija ja diehtoteknihkka:belljosat']))


class TestExcelImporter(unittest.TestCase):
    def test_get_concepts(self):
        ei = importer.ExcelImporter()
        lang_column = {'fi': 1, 'nb': 2, 'se': 3}
        worksheets = {'Sheet1': lang_column}
        filename = os.path.join(os.path.dirname(__file__), 'excel',
                                'simple.xlsx')
        fileinfo = {filename: worksheets}

        ec = importer.ExcelConcept(filename=filename, worksheet='Sheet1',
                                   row=2)
        ec.add_expression('fi', 'suomi')
        ec.add_expression('nb', 'norsk')
        ec.add_expression('se', 'davvisámegiella')

        ei.get_concepts(fileinfo)
        got = ei.concepts
        got_concept = got[0]
        self.assertEqual(len(got), 1)
        self.assertDictEqual(got_concept.expressions, ec.expressions)
        self.assertTupleEqual((got_concept.excelinfo),
                              (ec.excelinfo))

    def test_collect_expressions1(self):
        ''', as splitter'''
        ei = importer.ExcelImporter()
        got = ei.collect_expressions('a, b')

        self.assertSetEqual(set(['a', 'b']), got)

    def test_collect_expressions2(self):
        '''; as splitter'''
        ei = importer.ExcelImporter()
        got = ei.collect_expressions('a; b')

        self.assertSetEqual(set(['a', 'b']), got)

    def test_collect_expressions3(self):
        '''\n as splitter'''
        ei = importer.ExcelImporter()
        got = ei.collect_expressions('a\nb')

        self.assertSetEqual(set(['a', 'b']), got)

    def test_collect_expressions4(self):
        '''/ as splitter'''
        ei = importer.ExcelImporter()
        got = ei.collect_expressions('a/ b')

        self.assertSetEqual(set(['a', 'b']), got)

    def test_collect_expressions5(self):
        '''illegal chars'''
        illegal_chars = '()-'
        ei = importer.ExcelImporter()

        for c in illegal_chars:
            with self.assertRaises(importer.ExcelImportException):
                ei.collect_expressions(c)

    def test_collect_expressions6(self):
        '''multiword expression'''
        ei = importer.ExcelImporter()
        got = ei.collect_expressions('a b')

        self.assertSetEqual(set(['a b']), got)
