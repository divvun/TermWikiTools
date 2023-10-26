# -*- coding: utf-8 -*-

import collections
import os
import unittest

from termwikitools import importer


class TestExcelImporter(unittest.TestCase):
    def test_get_concepts(self):
        self.maxDiff = None
        filename = os.path.join(os.path.dirname(__file__), "excel", "simple.xlsx")
        ei = importer.ExcelImporter(filename)

        concept = {
            "concept": {
                "main_category": "Servodatdieđa",
                "collection": set(),
            },
            "concept_infos": [
                {
                    "explanation": "Dette er forklaringen",
                    "language": "nb",
                },
            ],
            "related_expressions": [
                {
                    "expression": "davvisámegiella",
                    "language": "se",
                    "pos": "N",
                },
                {
                    "expression": "suomi",
                    "language": "fi",
                    "pos": "N",
                },
                {
                    "expression": "norsk",
                    "language": "nb",
                    "pos": "N",
                },
            ],
        }
        concept["concept"]["collection"].add("simple")
        ei.get_concepts()
        got = ei.concepts
        got_concept = got[0]

        self.assertDictEqual(got_concept["concept"], concept["concept"])
        for concept_info in got_concept["concept_infos"]:
            self.assertTrue(concept_info in concept["concept_infos"])
        for related_expression in got_concept["related_expressions"]:
            self.assertTrue(related_expression in concept["related_expressions"])

    def test_collect_expressions_test_splitters(self):
        """Test if legal split chars work as splitters."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter("fakename.xlsx")
        for startline in ["a, b", "a; b", "a\nb", "a/b"]:
            got = ei.collect_expressions(startline)

            self.assertEqual(["a", "b"], got)

    def test_collect_expressions_illegal_chars(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter("fakename.xlsx")
        for x, startline in enumerate("()-~?"):
            got = ei.collect_expressions(startline)

            self.assertEqual([startline], got)

    def test_collect_expressions_illegal_chars_with_newline(self):
        """Check that illegal chars in startline is handled correctly."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter("fakename.xlsx")
        startline = "a-a;\nb=b;\nc?c"
        got = ei.collect_expressions(startline)

        self.assertEqual([startline.replace("\n", " ")], got)

    def test_collect_expressions_multiword_expression(self):
        """Handle multiword expression."""
        counter = collections.defaultdict(int)
        ei = importer.ExcelImporter("fakename.xlsx")
        got = ei.collect_expressions("a b")

        self.assertEqual(["a b"], got)
