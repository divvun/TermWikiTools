# -*- coding: utf-8 -*-

import unittest

from termwikiimporter import bot


class TestBot(unittest.TestCase):
    def test_bot1(self):
        self.maxDiff = None
        c = (
            u'{{Concept\n'
            u'|definition_se=ađaiduvvat\n'
            u'|explanation_se=omd\n'
            u' 1. it don gal dainna bargguin ađaiduva\n'
            u'|more_info_se=\n'
            u'|reviewed_se=No\n'
            u'|definition_nb=bli fetere\n'
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe\n'
            u' 1. du blir nok ikke fet av det arbeidet\n'
            u'|more_info_nb=\n'
            u'|reviewed_nb=No\n'
            u'|sources=\n'
            u'|category=\n'
            u'|no picture=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=ađaiduvvat\n'
            u'|in_header=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|expression=bli fetere\n'
            u'|in_header=No\n'
            u'}}'
        )

        want = (
            u'{{Concept\n'
            u'|definition_se=ađaiduvvat\n'
            u'|explanation_se=omd 1. it don gal dainna bargguin ađaiduva\n'
            u'|definition_nb=bli fetere\n'
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|expression=bli fetere\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=ađaiduvvat\n'
            u'|sanctioned=No\n'
            u'}}'
        )

        self.assertEqual(bot.bot(c), want)

    def test_bot2(self):
        self.maxDiff = None
        c = (
            u'[[Kategoriija:Concepts]]'
        )

        want = (
            u'[[Kategoriija:Concepts]]'
        )

        self.assertEqual(bot.bot(c), want)

    def test_bot3(self):
        self.maxDiff = None
        c = (
            u'{{Concept\n'
            u'|definition_se=ađaiduvvat\n'
            u'|explanation_se=omd 1. it don gal dainna bargguin ađaiduva\n'
            u'|more_info_se=\n'
            u'|definition_nb=bli fetere\n'
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet\n'
            u'|more_info_nb=\n'
            u'|sources=\n'
            u'|category=\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|sanctioned=No\n'
            u'|expression=ađaiduvvat\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|sanctioned=No\n'
            u'|expression=bli fetere\n'
            u'}}'
        )

        want = (
            u'{{Concept\n'
            u'|definition_se=ađaiduvvat\n'
            u'|explanation_se=omd 1. it don gal dainna bargguin ađaiduva\n'
            u'|definition_nb=bli fetere\n'
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|expression=bli fetere\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=ađaiduvvat\n'
            u'|sanctioned=No\n'
            u'}}'
        )

        got = bot.bot(c)
        self.assertEqual(got, want)

    def test_bot4(self):
        self.maxDiff = None
        c = (
            u'{{Concept\n'
            u'|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            u'|explanation_se=Njiŋŋálas bohcco gohčodit rotnun leaš dal reiton dahje massán miesis, dahje ii leat oppa leamašge čoavjjis\n'
            u'|reviewed=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=rotnu\n'
            u'|sanctioned=Yes\n'
            u'}}'
        )
        want = (
            u'{{Concept\n'
            u'|definition_se=njiŋŋálas boazu dahje ealga (sarvva) mas ii leat miessi\n'
            u'|explanation_se=Njiŋŋálas bohcco gohčodit rotnun leaš dal reiton dahje massán miesis, dahje ii leat oppa leamašge čoavjjis\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=rotnu\n'
            u'|sanctioned=Yes\n'
            u'}}'
        )
        got = bot.bot(c)

        self.assertEqual(got, want)

    def test_bot5(self):
        self.maxDiff = None
        c = (
            u'{{Concept\n'
            u'|reviewed=No\n'
            u'|reviewed_se=No\n'
            u'|reviewed_nb=No\n'
            u'|reviewed_fi=Yes\n'
            u'|no picture=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|expression=se\n'
            u'|language=se\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|expression=se\n'
            u'|language=nb\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|expression=se\n'
            u'|language=fi\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|expression=se\n'
            u'|language=smn\n'
            u'|status=recommended\n'
            u'|sanctioned=Yes\n'
            u'}}'
        )

        want = (
            u'{{Concept\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=fi\n'
            u'|expression=se\n'
            u'|sanctioned=Yes\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|expression=se\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=se\n'
            u'|sanctioned=No\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=smn\n'
            u'|expression=se\n'
            u'|status=recommended\n'
            u'|sanctioned=Yes\n'
            u'}}'
        )

        got = bot.bot(c)
        self.assertEqual(got, want)

    def test_bot6(self):
        self.maxDiff = None

        concept = [
            u'{{Concept',
            u'|definition_se=definition1',
            u'|duplicate_pages=[8], [9]',
            u'}}',
            u'{{Related concept',
            u'|concept=Boazodoallu:duottarmiessi',
            u'|relation=cohyponym',
            u'}}'
        ]

        want = '\n'.join(concept)
        got = bot.bot(want)

        self.assertEqual(got, want)

    def test_bot7(self):
        self.maxDiff = None

        concept = [
            u'{{Concept',
            u'|definition_se=definition1',
            u'|duplicate_pages=[8], [9]',
            u'}}',
            u'{{Related expression',
            u'|sanctioned=No',
            u'}}'
        ]

        want = '\n'.join([
            u'{{Concept',
            u'|definition_se=definition1',
            u'|duplicate_pages=[8], [9]',
            u'}}',
        ])

        got = bot.bot('\n'.join(concept))

        self.assertEqual(got, want)

    def test_bot8(self):
        concept = u'''{{Concept
|definition_se=ákšodearri
|explanation_se=
|more_info_se=
|reviewed_se=Yes
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
|more_info_nb=
|reviewed_nb=Yes
|sources=
|category=
|no picture=No
}}
{{Related expression
|language=se
|expression=ákšodearri
|in_header=No
}}
{{Related expression
|language=nb
|expression=tynne delen av øks
|in_header=No
}}'''
        want = u'''{{Concept
|definition_se=ákšodearri
|definition_nb=tynne delen av øks
|explanation_nb=Den tynne del av ei øks (den slipes til egg)
}}
{{Related expression
|language=nb
|expression=tynne delen av øks
|sanctioned=Yes
}}
{{Related expression
|language=se
|expression=ákšodearri
|sanctioned=Yes
}}'''

        got = bot.bot(concept)
        self.assertEqual(got, want)
