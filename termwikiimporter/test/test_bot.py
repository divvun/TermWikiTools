# -*- coding: utf-8 -*-

import unittest

from termwikiimporter import bot, importer


class TestBot(unittest.TestCase):
    def test_bot1(self):
        """Check that continued lines in Concept is flattened."""
        self.maxDiff = None
        c = [
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
        ]

        want = [
            '{{Concept',
            '|explanation_se=omd 1. it don gal dainna bargguin ađaiduva',
            '|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet',
            '}}',
            '{{Related expression',
            '|expression=ađaiduvvat',
            '|language=se',
            '|sanctioned=No',
            '|pos=V',
            '}}'
        ]

        self.assertEqual('\n'.join(want), bot.concept_parser('\n'.join(c)))

    def test_bot2(self):
        self.maxDiff = None
        c = (
            '[[Kategoriija:Concepts]]'
        )

        want = (
            '[[Kategoriija:Concepts]]'
        )

        self.assertEqual(bot.concept_parser(c), want)

    def test_bot4(self):
        """Check that sanctioned=No is set default."""
        self.maxDiff = None
        c = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '}}\n'
            '{{Related expression\n'
            '|language=se\n'
            '|expression=rotnu\n'
            '|pos=N\n'
            '}}'
        )
        want = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '}}\n'
            '{{Related expression\n'
            '|expression=rotnu\n'
            '|language=se\n'
            '|sanctioned=No\n'
            '|pos=N\n'
            '}}'
        )
        got = bot.concept_parser(c)

        self.assertEqual(want, got)

    def test_bot5(self):
        """Check reviewed_lang=Yes wins over sanctioned=No in lang."""
        self.maxDiff = None
        c = (
            '{{Concept\n'
            '|reviewed_fi=Yes\n'
            '}}\n'
            '{{Related expression\n'
            '|expression=se\n'
            '|language=fi\n'
            '|sanctioned=No\n'
            '}}'
        )

        want = (
            '{{Concept\n'
            '}}\n'
            '{{Related expression\n'
            '|expression=se\n'
            '|language=fi\n'
            '|sanctioned=Yes\n'
            '|pos=N/A\n'
            '}}'
        )

        got = bot.concept_parser(c)
        self.assertEqual(want, got)

    def test_bot6(self):
        """Check that Related concept is parsed correctly."""
        self.maxDiff = None

        concept = [
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related concept',
            '|concept=Boazodoallu:duottarmiessi',
            '|relation=cohyponym',
            '}}'
        ]

        want = '\n'.join(concept)
        got = bot.concept_parser(want)

        self.assertEqual(want, got)

    def test_bot7(self):
        """Check that an exception is raised when expression is not defined."""
        self.maxDiff = None

        concept = [
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}',
            '{{Related expression',
            '|sanctioned=No',
            '}}'
        ]

        want = '\n'.join([
            '{{Concept',
            '|definition_se=definition1',
            '|duplicate_pages=[8], [9]',
            '}}'
        ])

        with self.assertRaises(bot.BotError):
            got = bot.concept_parser('\n'.join(concept))

    def test_bot8(self):
        """Check that empty and unwanted attributes in Concept are removed."""
        concept = '''{{Concept
|definition_se=ákšodearri
|explanation_se=
|more_info_se=
|reviewed_se=Yes
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
|more_info_nb=
|sources=
|category=
|no picture=No
}}
{{Related expression
|language=se
|expression=ákšodearri
|sanctioned=Yes
|pos=N
|expression=ákšodearri
}}'''
        want = '''{{Concept
|definition_se=ákšodearri
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
}}
{{Related expression
|expression=ákšodearri
|language=se
|sanctioned=Yes
|pos=N
}}'''

        got = bot.concept_parser(concept)
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
            '|expression=rotnu\n'
            '|language=se\n'
            '|sanctioned=Yes\n'
            '|pos=N\n'
            '}}'
        )
        got = bot.concept_parser(c)

        self.assertEqual(want, got)

    def test_bot11(self):
        """Check that continued lines in Concept is flattened."""
        self.maxDiff = None
        c = [
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
        ]

        want = [
            '{{Concept',
            '|explanation_se=omd 1. it don gal dainna bargguin ađaiduva',
            '|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet',
            '}}',
            '{{Related expression',
            '|expression=ađaiduvvat',
            '|language=se',
            '|sanctioned=No',
            '|pos=V',
            '}}'
        ]

        self.assertEqual('\n'.join(want), bot.concept_parser('\n'.join(c)))

    def test_bot12(self):
        """Check that sanctioned=Yes in lang when reviewed_lang=Yes in Concept is set."""
        self.maxDiff = None
        c = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '|reviewed_se=Yes\n'
            '}}\n'
            '{{Related expression\n'
            '|language=se\n'
            '|expression=rotnu\n'
            '|pos=N\n'
            '}}'
        )
        want = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '}}\n'
            '{{Related expression\n'
            '|expression=rotnu\n'
            '|language=se\n'
            '|sanctioned=Yes\n'
            '|pos=N\n'
            '}}'
        )
        got = bot.concept_parser(c)

        self.assertEqual(want, got)

    def test_bot13(self):
        """Check that sanctioned=Yes survives reviewed_lang=No in Concept.

        reviewed_lang was set when imported from risten.no, and not used after that.
        sanctioned is actively set by the user later, and should therefore "win" over
        reviewed_lang
        """
        self.maxDiff = None
        c = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '|reviewed_se=Yes\n'
            '}}\n'
            '{{Related expression\n'
            '|language=se\n'
            '|expression=rotnu\n'
            '|pos=N\n'
            '}}'
        )
        want = (
            '{{Concept\n'
            '|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            '}}\n'
            '{{Related expression\n'
            '|expression=rotnu\n'
            '|language=se\n'
            '|sanctioned=Yes\n'
            '|pos=N\n'
            '}}'
        )
        got = bot.concept_parser(c)

        self.assertEqual(want, got)

    def test_bot14(self):
        """Check that empty and unwanted attributes in Related expression are removed."""
        concept = '''{{Concept
|definition_nb=tynne delen av øks
}}
{{Related expression
|language=se
|expression=ákšodearri
|in_header=No
|sanctioned=No
|pos=N
}}'''
        want = '''{{Concept
|definition_nb=tynne delen av øks
}}
{{Related expression
|expression=ákšodearri
|language=se
|sanctioned=No
|pos=N
}}'''

        got = bot.concept_parser(concept)
        self.assertEqual(want, got)

    def test_set_sanctioned_correctly(self):
        self.maxDiff = None
        concept = '''{{Concept
|definition_smj=bessam, gå besa jali oattjo máhttelisvuodav sirddet diedojt - sierraláhká datåvrån/dáhtámasjijnan
}}
{{Related expression
|language=smj
|expression=bessam
|sanctioned=No
}}'''
        want = '''{{Concept
|definition_smj=bessam, gå besa jali oattjo máhttelisvuodav sirddet diedojt - sierraláhká datåvrån/dáhtámasjijnan
}}
{{Related expression
|expression=bessam
|language=smj
|sanctioned=No
|pos=N/A
}}'''

        got = bot.concept_parser(concept)
        self.assertEqual(want, got)
