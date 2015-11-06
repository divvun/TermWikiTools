# -*- coding: utf-8 -*-

import unittest

from termwikiimporter import bot


class TestBot(unittest.TestCase):
    def test_bot1(self):
        self.maxDiff = None
        c = [
            u'{{Concept',
            u'|definition_se=ađaiduvvat',
            u'|explanation_se=omd',
            u' 1. it don gal dainna bargguin ađaiduva',
            u'|more_info_se=',
            u'|reviewed_se=No',
            u'|definition_nb=bli fetere',
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe',
            u' 1. du blir nok ikke fet av det arbeidet',
            u'|more_info_nb=',
            u'|reviewed_nb=No',
            u'|sources=',
            u'|category=',
            u'|no picture=No',
            u'}}',
            u'{{Related expression',
            u'|language=nb',
            u'|expression=bli fetere',
            u'|in_header=No',
            u'}}',
            u'{{Related expression',
            u'|language=se',
            u'|expression=ađaiduvvat',
            u'|in_header=No',
            u'}}'
        ]

        want = [
            u'{{Concept',
            u'|definition_se=ađaiduvvat',
            u'|explanation_se=omd 1. it don gal dainna bargguin ađaiduva',
            u'|definition_nb=bli fetere',
            u'|explanation_nb=bli fetere - om husdyr; - ironisk: «bli fet av» noe, ha fordel av noe 1. du blir nok ikke fet av det arbeidet',
            u'}}',
            u'{{Related expression',
            u'|language=nb',
            u'|expression=bli fetere',
            u'|sanctioned=No',
            u'|pos=MWE',
            u'}}',
            u'{{Related expression',
            u'|language=se',
            u'|expression=ađaiduvvat',
            u'|sanctioned=No',
            u'|pos=V',
            u'}}'
        ]

        self.assertEqual(u'\n'.join(want), bot.concept_parser(u'\n'.join(c)))

    def test_bot2(self):
        self.maxDiff = None
        c = (
            u'[[Kategoriija:Concepts]]'
        )

        want = (
            u'[[Kategoriija:Concepts]]'
        )

        self.assertEqual(bot.concept_parser(c), want)

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
            u'|language=nb\n'
            u'|sanctioned=No\n'
            u'|expression=bli fetere\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|sanctioned=No\n'
            u'|expression=ađaiduvvat\n'
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
            u'|pos=MWE\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=se\n'
            u'|expression=ađaiduvvat\n'
            u'|sanctioned=No\n'
            u'|pos=V\n'
            u'}}'
        )

        got = bot.concept_parser(c)
        self.assertEqual(want, got)

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
            u'|pos=N\n'
            u'}}'
        )
        got = bot.concept_parser(c)

        self.assertEqual(want, got)

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
            u'|language=se\n'
            u'|expression=se\n'
            u'|is_typo=Yes\n'
            u'|sanctioned=No\n'
            u'|pos=N/A\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=nb\n'
            u'|expression=se\n'
            u'|sanctioned=No\n'
            u'|pos=N/A\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=fi\n'
            u'|expression=se\n'
            u'|sanctioned=Yes\n'
            u'|pos=N/A\n'
            u'}}\n'
            u'{{Related expression\n'
            u'|language=smn\n'
            u'|expression=se\n'
            u'|status=recommended\n'
            u'|sanctioned=Yes\n'
            u'|pos=N/A\n'
            u'}}'
        )

        got = bot.concept_parser(c)
        self.assertEqual(want, got)

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
        got = bot.concept_parser(want)

        self.assertEqual(want, got)

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
            u'}}'
        ])

        got = bot.concept_parser('\n'.join(concept))

        self.assertAlmostEqual(got, want)

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
|language=nb
|expression=tynne delen av øks
|in_header=No
}}
{{Related expression
|language=se
|expression=ákšodearri
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
|pos=MWE
}}
{{Related expression
|language=se
|expression=ákšodearri
|sanctioned=Yes
|pos=N
}}'''

        got = bot.concept_parser(concept)
        self.assertEqual(want, got)

    def test_set_sanctioned_correctly(self):
        self.maxDiff = None
        concept = u'''{{Concept
|definition_se=boađa lea njuolggadus, man mielde geavaheaddji beassá geavahit dihtora
|explanation_se=Mo beassat sisa dihtorii
|definition_sma=juktie riektiem åadtjodh, man mietie utnije fijhkie datovrem utnedh
|explanation_sma=guktie datovren sïjse fijhkedh
|definition_smj=bessam, gå besa jali oattjo máhttelisvuodav sirddet diedojt - sierraláhká datåvrån/dáhtámasjijnan
|definition_nb=tilgang/adgang, er det å få tak i eller plassere data eller instruksjoner i en av maskinsystemets lagerenheter, aksess
|explanation_nb=(fra lat. egentlig 'adgang') særlig i edb: adgang, mulighet til å overføre informasjon, tilgang
|sources=http://risten.no
}}
{{Related expression
|language=fi
|expression=pääsy
|sanctioned=No
}}
{{Related expression
|language=fi
|expression=väylä
|sanctioned=No
}}
{{Related expression
|language=nb
|expression=adgang
|status=recommended
|sanctioned=No
}}
{{Related expression
|language=nb
|expression=tilgang
|sanctioned=No
}}
{{Related expression
|language=se
|expression=boađa
|sanctioned=No
}}
{{Related expression
|language=smj
|expression=bessam
|status=recommended
|note=Sáme Giellagálldo, dåhkkidum javllamáno 10-11 b. 2013
|sanctioned=No
}}
{{Related expression
|language=sma
|expression=baahtseme
|status=recommended
|sanctioned=No
}}
{{Related expression
|language=sv
|expression=tillgång
|sanctioned=No
}}'''
        want = u'''{{Concept
|definition_se=boađa lea njuolggadus, man mielde geavaheaddji beassá geavahit dihtora
|explanation_se=Mo beassat sisa dihtorii
|definition_sma=juktie riektiem åadtjodh, man mietie utnije fijhkie datovrem utnedh
|explanation_sma=guktie datovren sïjse fijhkedh
|definition_smj=bessam, gå besa jali oattjo máhttelisvuodav sirddet diedojt - sierraláhká datåvrån/dáhtámasjijnan
|definition_nb=tilgang/adgang, er det å få tak i eller plassere data eller instruksjoner i en av maskinsystemets lagerenheter, aksess
|explanation_nb=(fra lat. egentlig 'adgang') særlig i edb: adgang, mulighet til å overføre informasjon, tilgang
|sources=http://risten.no
}}
{{Related expression
|language=fi
|expression=pääsy
|sanctioned=No
|pos=N
}}
{{Related expression
|language=fi
|expression=väylä
|sanctioned=No
|pos=N
}}
{{Related expression
|language=nb
|expression=adgang
|status=recommended
|sanctioned=No
|pos=N
}}
{{Related expression
|language=nb
|expression=tilgang
|sanctioned=No
|pos=N
}}
{{Related expression
|language=se
|expression=boađa
|sanctioned=No
|pos=N
}}
{{Related expression
|language=smj
|expression=bessam
|status=recommended
|note=Sáme Giellagálldo, dåhkkidum javllamáno 10-11 b. 2013
|sanctioned=No
|pos=N
}}
{{Related expression
|language=sma
|expression=baahtseme
|status=recommended
|sanctioned=No
|pos=N
}}
{{Related expression
|language=sv
|expression=tillgång
|sanctioned=No
|pos=N
}}'''

        got = bot.concept_parser(concept)
        self.assertEqual(want, got)

    def test_unchanged_concept_when_no_pos_is_found(self):
        concept = u'''{{Concept
|more_info_se=Erklære seg uvillig : cealkit iežas vuostemielas.
}}
{{Related expression
|language=fi
|expression=haluton
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=nb
|expression=uvillig
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=se
|expression=vuostemielas
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}'''
        want = u'''{{Concept
|more_info_se=Erklære seg uvillig : cealkit iežas vuostemielas.
}}
{{Related expression
|language=fi
|expression=haluton
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=nb
|expression=uvillig
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}
{{Related expression
|language=se
|expression=vuostemielas
|collection=jurdihkalas_tearbmalistu_2011-seg
|sanctioned=Yes
|pos=N/A
}}'''

        got = bot.concept_parser(concept)
        self.assertEqual(want, got)
