# -*- coding: utf-8 -*-

import os
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

        self.assertEqual(bot.bot(c), want)

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
        print(want)
        print(got)
        self.assertEqual(got, want)
