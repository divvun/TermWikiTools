# -*- coding: utf-8 -*-
"""Test the functions and classes found in read_termwiki."""

import collections
import unittest

from termwikiimporter import read_termwiki


class FalseMockAnalyser(object):
    def is_known(self, language, lemma):
        return False


class TrueMockAnalyser(object):
    def is_known(self, language, lemma):
        return True

class TestConcept(unittest.TestCase):
    def test_bot1(self):
        """Check that continued lines in Concept is kept as is."""
        self.maxDiff = None
        content = '\n'.join([
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
            '{{Concept info',
            '|language=nb',
            '|explanation=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe',
            '1. du blir nok ikke fet av det arbeidet',
            '}}',
            '{{Concept info',
            '|language=se',
            '|explanation=omd',
            '1. it don gal dainna bargguin ađaiduva',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ađaiduvvat',
            '|sanctioned=False',
            '|pos=V',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

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
            '{{Concept info',
            '|language=se',
            '|definition=njiŋŋálas',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=rotnu',
            '|pos=N',
            '|sanctioned=False',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_bot6(self):
        """Check that Related concept is parsed correctly."""
        self.maxDiff = None

        content = '\n'.join([
            '{{Related expression',
            '|language=se',
            '|expression=exp',
            '|sanctioned=False',
            '}}',
            '{{Related concept',
            '|concept=Boazodoallu:duottarmiessi',
            '|relation=cohyponym',
            '}}',
            '{{Concept}}',
        ])

        want = content

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_is_expression_set(self):
        """Check Related expressions with empty expressions are deleted."""
        self.maxDiff = None

        content = '\n'.join([
            '{{Concept',
            '|definition_se=definition1',
            '}}',
            '{{Related expression',
            '|language=se',
            '|sanctioned=No',
            '}}'
        ])

        want = '\n'.join([
            '{{Concept info',
            '|language=se',
            '|definition=definition1',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_bot8(self):
        """Check that empty and unwanted attributes in Concept are removed."""
        content = '''{{Concept
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
        want = '\n'.join([
            '{{Concept info',
            '|language=nb',
            '|definition=tynne delen av øks',
            '|explanation=Den tynne del av ei øks (den slipes til egg)',
            '}}',
            '{{Concept info',
            '|language=se',
            '|definition=ákšodearri',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ákšodearri',
            '|sanctioned=True',
            '|pos=N',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_bot10(self):
        """Check that reviewed is removed."""
        self.maxDiff = None
        content = '\n'.join([
            '{{Concept',
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi',
            '|reviewed=No',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=rotnu',
            '|sanctioned=Yes',
            '|pos=N',
            '}}'
        ])
        want = '\n'.join([
            '{{Concept info',
            '|language=se',
            '|definition=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=rotnu',
            '|sanctioned=True',
            '|pos=N',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_remove_is_typo(self):
        """Check that is_typo is removed from Related expression."""
        content = '''{{Concept}}
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

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertFalse('is_typo' in str(concept))

    def test_concept_to_conceptinfo(self):
        """Check that conversion from concept to concept info works."""
        self.maxDiff = None
        content = '\n'.join([
            '{{Concept',
            '|definition_nb=en fullvoksen hun av arten steinkobbe, (en fullvoksen hun-sel av den selen som av samene kalles nuorroš L); en steinkobbe hun som er drektig PAJ',
            '|definition_se=Ollesšattot njiŋŋálas geađgán, PAJ lassediehtu čovjon geađgán',
            '|more_info_nb=Norsk søkeord på risten.no: steinkobbe',
            '|explanation_se=(afzhio L, afčo FR)',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|collection=Collection:njuorjjotearpmat',
            '|sanctioned=No',
            '|pos=N',
            '}}',
        ])

        want = '\n'.join([
            '{{Concept info',
            '|language=nb',
            '|definition=en fullvoksen hun av arten steinkobbe, (en fullvoksen hun-sel av den selen som av samene kalles nuorroš L); en steinkobbe hun som er drektig PAJ',
            '|more_info=Norsk søkeord på risten.no: steinkobbe',
            '}}',
            '{{Concept info',
            '|language=se',
            '|definition=Ollesšattot njiŋŋálas geađgán, PAJ lassediehtu čovjon geađgán',
            '|explanation=(afzhio L, afčo FR)',
            '}}',
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|sanctioned=False',
            '|pos=N',
            '}}',
            '{{Concept',
            '|collection=Collection:njuorjjotearpmat',
            '}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_remove_language_from_concept(self):
        """Check that conversion from concept to concept info works."""
        self.maxDiff = None
        content = '\n'.join([
            '{{Concept',
            '|language=se',
            '}}',
        ])

        want = '{{Concept}}'

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        self.assertEqual(want, str(concept))

    def test_auto_sanction_true(self):
        content = '\n'.join([
            '{{Concept}}',
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|sanctioned=No',
            '|pos=N',
            '}}',
        ])

        want = '\n'.join([
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|sanctioned=True',
            '|pos=N',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        concept.analyser = TrueMockAnalyser()
        concept.auto_sanction('se')

        self.assertEqual(want, str(concept))

    def test_auto_sanction_false(self):
        content = '\n'.join([
            '{{Concept}}',
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|sanctioned=No',
            '|pos=N',
            '}}',
        ])

        want = '\n'.join([
            '{{Related expression',
            '|language=se',
            '|expression=ákču',
            '|sanctioned=False',
            '|pos=N',
            '}}',
            '{{Concept}}',
        ])

        concept = read_termwiki.Concept()
        concept.from_termwiki(content)
        concept.analyser = FalseMockAnalyser()
        concept.auto_sanction('se')

        self.assertEqual(want, str(concept))
