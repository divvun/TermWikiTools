# -*- coding: utf-8 -*-
"""Test the functions and classes found in read_termwiki."""

import unittest

from termwikitools.read_termwiki import (
    cleanup_termwiki_page,
    termwiki_page_to_dataclass,
)


class FalseMockAnalyser(object):
    def is_known(self, language, lemma):
        return False


class TrueMockAnalyser(object):
    def is_known(self, language, lemma):
        return True


def test_bot1():
    """Check that continued lines in Concept is kept as is."""
    content = iter(
        [
            "{{Concept info",
            "|language=nb",
            "|explanation=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe",
            " 1. du blir nok ikke fet av det arbeidet",
            "}}",
            "{{Concept info",
            "|language=se",
            "|explanation=omd",
            " 1. it don gal dainna bargguin ađaiduva",
            "}}",
            "{{Related expression",
            "|language=se",
            "|expression=ađaiduvvat",
            "|sanctioned=False",
            "|pos=V",
            "}}",
        ]
    )

    want = iter(
        [
            "{{Concept info",
            "|language=nb",
            "|explanation=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe",
            "1. du blir nok ikke fet av det arbeidet",
            "}}",
            "{{Concept info",
            "|language=se",
            "|explanation=omd",
            "1. it don gal dainna bargguin ađaiduva",
            "}}",
            "{{Related expression",
            "|language=se",
            "|expression=ađaiduvvat",
            "|sanctioned=False",
            "|pos=V",
            "}}",
            "{{Concept}}",
        ]
    )

    concept = termwiki_page_to_dataclass(title="Test1", text_iterator=content)

    assert termwiki_page_to_dataclass(
        title="Test1", text_iterator=want
    ) == cleanup_termwiki_page(concept)


def test_bot4():
    """Check that sanctioned=No is set default."""
    content = iter(
        [
            "{{Concept info",
            "|language=se",
            "|definition=njiŋŋálas",
            "}}",
            "{{Related expression",
            "|language=se",
            "|expression=rotnu",
            "|pos=N",
            "}}",
        ]
    )
    want = iter(
        [
            "{{Concept info",
            "|language=se",
            "|definition=njiŋŋálas",
            "}}",
            "{{Related expression",
            "|language=se",
            "|expression=rotnu",
            "|pos=N",
            "|sanctioned=False",
            "}}",
            "{{Concept}}",
        ]
    )

    concept = termwiki_page_to_dataclass(title="Test", text_iterator=content)
    assert termwiki_page_to_dataclass(
        title="Test", text_iterator=want
    ) == cleanup_termwiki_page(concept)

def test_bot6():
    """Check that Related concept is parsed correctly."""

    content = [
            "{{Related expression",
            "|language=se",
            "|expression=exp",
            "|sanctioned=False",
            "}}",
            "{{Related concept",
            "|concept=Boazodoallu:duottarmiessi",
            "|relation=cohyponym",
            "}}",
            "{{Concept}}",
        ]
    

    concept = termwiki_page_to_dataclass(title="Test", text_iterator=iter(content))
    assert concept.related_concepts is not None
    assert len(concept.related_concepts) == 1
    assert concept.related_concepts[0].concept == content[6].split("|concept=")[1]
    assert concept.related_concepts[0].relation == content[7].split("|relation=")[1]


class TestCleanupExpression(unittest.TestCase):
    def test_cleanup_expression_normalizes_se_characters(self):
        related_expression = read_termwiki.RelatedExpression(
            note=None,
            pos=None,
            source=None,
            inflection=None,
            country=None,
            dialect=None,
            status=None,
            expression="Èéíïēīĵĺōūḥḷṃṇṿạẹọụÿⓑⓓⓖ·ṛü’ ",
            language="se",
        )

        cleaned_expression = read_termwiki.cleanup_expression(related_expression)

        self.assertEqual(
            cleaned_expression["expression"], "Eeiieijlouhlmrvaeouybdg ru' "
        )

    def test_cleanup_expression_normalizes_sms_apostrophes(self):
        related_expression = read_termwiki.RelatedExpression(
            note=None,
            pos=None,
            source=None,
            inflection=None,
            country=None,
            dialect=None,
            status=None,
            expression="\u2019\u0027\u2032\u00b4\u0301",
            language="sms",
        )

        cleaned_expression = read_termwiki.cleanup_expression(related_expression)

        self.assertEqual(
            cleaned_expression["expression"], "\u02bc\u02bc\u02b9\u02b9\u02b9"
        )

    def test_cleanup_expression_uppercases_initial_latin_character(self):
        related_expression = read_termwiki.RelatedExpression(
            note=None,
            pos=None,
            source=None,
            inflection=None,
            country=None,
            dialect=None,
            status=None,
            expression="rosa canina",
            language="lat",
        )

        cleaned_expression = read_termwiki.cleanup_expression(related_expression)

        self.assertEqual(cleaned_expression["expression"], "Rosa canina")
