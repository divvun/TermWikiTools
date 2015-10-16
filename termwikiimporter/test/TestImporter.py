# -*- coding: utf-8 -*-

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
