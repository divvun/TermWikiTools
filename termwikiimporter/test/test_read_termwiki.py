# -*- coding: utf-8 -*-
"""Test the functions and classes found in read_termwiki."""

import collections
import unittest

from termwikiimporter import read_termwiki


class TestBot(unittest.TestCase):
    def test_bot1(self):
        """Check that continued lines in Concept is kept as is."""
        self.maxDiff = None
        concept = '\n'.join([
            '{{Concept',
            '|explanation_se=omd',
            ' 1. it don gal dainna bargguin ađaiduva',
            '|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe',
            ' 1. du blir nok ikke fet av det arbeidet',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ađaiduvvat',
            '|sanctioned=No',
            '|pos=V',
            '}}'
        ])

        want = '\n'.join([
            '{{Concept',
            '|explanation_se=omd',
            ' 1. it don gal dainna bargguin ađaiduva',
            '|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe',
            ' 1. du blir nok ikke fet av det arbeidet',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ađaiduvvat',
            '|sanctioned=No',
            '|pos=V',
            '}}'
        ])

        self.assertEqual(want, read_termwiki.handle_page(concept))

    def test_bot2(self):
        """Check that ValueError is raised when hitting invalid content."""
        self.maxDiff = None
        concept = (
            '[[Kategoriija:Concepts]]'
        )

        with self.assertRaises(ValueError):
            read_termwiki.handle_page(concept)

    def test_stivren(self):
        """Check that pages containing STIVREN is preserved."""
        self.maxDiff = None
        concept = '#STIVREN [[Page]]'

        self.assertEqual(read_termwiki.handle_page(concept), concept)

    def test_omdirigering(self):
        """Check that pages containing OMDIRIGERING is preserved."""
        self.maxDiff = None
        concept = '#OMDIRIGERING [[Page]]'

        self.assertEqual(read_termwiki.handle_page(concept), concept)

    def test_bot4(self):
        """Check that sanctioned=No is set default."""
        self.maxDiff = None
        content = '\n'.join([
            '{{Concept',
            '|definition_se=njiŋŋálas',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=rotnu',
            '|pos=N',
            '}}'
        ])
        want = '\n'.join([
            '{{Concept',
            '|definition_se=njiŋŋálas',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=rotnu',
            '|pos=N',
            '|sanctioned=No',
            '}}'
        ])
        got = read_termwiki.handle_page(content)

        self.assertEqual(want, got)

    def test_bot6(self):
        """Check that Related concept is parsed correctly."""
        self.maxDiff = None

        concept = [
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=exp',
            '|sanctioned=No',
            '}}',
            '{{Related concept',
            '|concept=Boazodoallu:duottarmiessi',
            '|relation=cohyponym',
            '}}'
        ]

        want = '\n'.join(concept)
        got = read_termwiki.handle_page(want)

        self.assertEqual(want, got)

    def test_is_expression_set(self):
        """Check Related expressions with empty expressions are deleted."""
        self.maxDiff = None

        concept = '\n'.join([
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related expression',
            '|language=se',
            '|sanctioned=No',
            '}}'
        ])

        want = '\n'.join([
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
        ])

        self.assertEqual(want, read_termwiki.handle_page(concept))

    def test_bot8(self):
        """Check that empty and unwanted attributes in Concept are removed."""
        concept = '''{{Concept
|definition_se=ákšodearri
|explanation_se=
|more_info_se=
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
|more_info_nb=
|sources=
|category=
}}
{{Related expression
|language=se
|expression=ákšodearri
|sanctioned=Yes
|pos=N
}}'''
        want = '''{{Concept
|definition_se=ákšodearri
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
}}
{{Related expression
|language=se
|expression=ákšodearri
|sanctioned=Yes
|pos=N
}}'''

        got = read_termwiki.handle_page(concept)
        self.assertEqual(want, got)

    def test_bot10(self):
        """Check that reviewed is removed."""
        self.maxDiff = None
        c = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '|reviewed=No\n'
            '}}\n'
            '{{Related expression\n'
            '|language=se\n'
            '|expression=rotnu\n'
            '|sanctioned=Yes\n'
            '|pos=N\n'
            '}}'
        )
        want = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '}}\n'
            '{{Related expression\n'
            '|language=se\n'
            '|expression=rotnu\n'
            '|sanctioned=Yes\n'
            '|pos=N\n'
            '}}'
        )
        got = read_termwiki.handle_page(c)

        self.assertEqual(want, got)


class TestReadTermwiki(unittest.TestCase):
    """Test the functions in read_termwiki."""

    def test_remove_is_typo(self):
        """Check that is_typo is removed from Related expression."""
        contains_is_typo = '''{{Concept}}
{{Related expression
|language=fi
|expression=aksiaalivarasto
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=nb
|expression=aksiallager
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=se
|expression=aksiálláger
|is_typo=Yes
|sanctioned=Yes
|pos=N/A
}}
'''

        got = read_termwiki.term_to_string(
            read_termwiki.parse_termwiki_concept(
                contains_is_typo))
        self.assertFalse('is_typo' in got)
