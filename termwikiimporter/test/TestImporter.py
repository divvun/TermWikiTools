# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikiimporter import importer


class TestConcept(unittest.TestCase):
    def setUp(self):
        self.concept = importer.Concept()

    def add_expression(self):
        self.concept.add_expression('se', 'sámi1')
        self.concept.add_expression('se', 'sámi2')
        self.concept.add_expression('nb', 'norsk1')
        self.concept.add_expression('nb', 'norsk1')

    def test_add_expression(self):
        self.add_expression()
        self.assertEqual(self.concept.expressions['se'], set(['sámi1', 'sámi2']))
        self.assertEqual(self.concept.expressions['nb'], set(['norsk1']))


    def add_concept_info(self):
        self.concept.add_concept_info('definition_se', 'definition1')

    def test_add_concept_info(self):
        self.add_concept_info()

        self.assertEqual(self.concept.concept_info['definition_se'], set(['definition1']))

    def add_idref(self):
        self.concept.add_idref('8')

    def test_add_idref(self):
        self.add_idref()

        self.assertEqual(self.concept.idref, set(['8']))

    def test_string(self):
        self.add_concept_info()
        self.add_expression()
        self.add_idref()

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

        self.assertTupleEqual((ec.filename, ec.worksheet, ec.row),
                              ('', '', 0))

    def test_init_set_variables(self):
        ec = importer.ExcelConcept(filename='filename', worksheet='worksheet',
                                   row=10)

        self.assertTupleEqual((ec.filename, ec.worksheet, ec.row),
                              ('filename', 'worksheet', 10))


class TermWikiWithTestSource(importer.TermWiki):
    @property
    def term_home(self):
        return os.path.join(os.path.dirname(__file__), 'terms')


class TestTermwiki(unittest.TestCase):
    def setUp(self):
        self.termwiki = TermWikiWithTestSource()
        self.termwiki.get_expressions()
        self.termwiki.get_idrefs()

    def test_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.expressions,
            {'fi': {'kuulokkeet': set(['206', '100830']),
                    'Brasilia': set(['101148', '101149'])},
             'nb': {'Brasil': set(['101149', '101148']),
                    'hodesett': set(['100830']),
                    'hodetelefoner': set(['100830', '206'])},
             'se': {'Brasil': set(['101149', '101148']),
                    'Brasilia': set(['101149', '101148']),
                    'bealjoštelefovdna': set(['206']),
                    'belljosat': set(['100830'])}
            }
        )

    def test_idref_expressions(self):
        self.maxDiff = None
        self.assertDictEqual(
            self.termwiki.idrefs,
            {'100830': {'fi': {'kuulokkeet'},
                        'nb': {'hodetelefoner', 'hodesett'},
                        'se': {'belljosat'}},
             '101148': {'fi': {'Brasilia'},
                        'nb': {'Brasil'},
                        'se': {'Brasil', 'Brasilia'}},
             '101149': {'fi': {'Brasilia'},
                        'nb': {'Brasil'},
                        'se': {'Brasil', 'Brasilia'}},
             '206': {'fi': {'kuulokkeet'},
                    'nb': {'hodetelefoner'},
                    'se': {'bealjoštelefovdna'}}})

    def test_get_expressions_set(self):
        want = collections.defaultdict(set)
        want['fi'].update(set(['kuulokkeet', 'Brasilia']))
        want['nb'].update(set(['hodetelefoner', 'hodesett', 'Brasil']))
        want['se'].update(set(['belljosat', 'Brasil', 'Brasilia', 'bealjoštelefovdna']))

        got = collections.defaultdict(set)
        for lang in self.termwiki.expressions.keys():
            got[lang].update(self.termwiki.expressions[lang])

        self.assertDictEqual(got, want)

