# -*- coding: utf-8 -*-
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this file. If not, see <http://www.gnu.org/licenses/>.
#
#   Copyright © 2018 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Test the functions and classes found in dicts2wiki."""

import unittest
from collections import defaultdict
from io import StringIO

from lxml import etree

from termwikiimporter import dicts2wiki


class TestDicts(unittest.TestCase):
    """Test dicts xml to wiki functions."""

    def setUp(self):
        self.dictxml = etree.parse(
            StringIO('''<r id="smenob" xml:lang="sme">
            <e>
                <lg>
                    <l pos="N">njeazzi</l>
                </lg>
                <mg>
                    <tg xml:lang="nob">
                        <re>i negative sammenhenger</re>
                        <t pos="N">ansikt</t>
                        <t pos="N">tryne</t>
                        <t>no pos example</t>
                        <t pos="no text example" />
                        <xg re="Kunne vært tryne">
                            <x src="a">Duohtavuohta časká njeacce vuostá.</x>
                            <xt src="b">Sannheta slår mot ansiktet.</xt>
                        </xg>
                        <xg>
                            <x>Eanet ii ollen dadjat ovdal go nisu čuoččohii ja čorbmadii su njeazzái.</x>
                            <xt>Han rakk ii å si mer før kvinnen reiste seg opp og slo med knyttneven i ansiktet hans.</xt>
                        </xg>
                        <xg>
                            <re />
                            <x>No text in re element</x>
                            <xt>No text in re element</xt>
                        </xg>
                        <xg>
                            <re>No text in x and xt elements</re>
                            <x />
                            <xt />
                        </xg>
                    </tg>
                </mg>
            </e>
        </r>
        '''))  # nopep8
        self.translations = set()
        self.translations.add(
            dicts2wiki.Stem(lemma='ansikt', pos='N', lang='nob'))
        self.translations.add(
            dicts2wiki.Stem(lemma='tryne', pos='N', lang='nob'))

        self.examples = set()
        self.examples.add(
            dicts2wiki.Example(
                orig='Duohtavuohta časká njeacce vuostá.',
                translation='Sannheta slår mot ansiktet.',
                restriction='Kunne vært tryne',
                orig_source='a',
                translation_source='b'))
        self.examples.add(
            dicts2wiki.Example(
                orig=
                'Eanet ii ollen dadjat ovdal go nisu čuoččohii ja čorbmadii su njeazzái.',  # nopep8
                translation=
                'Han rakk ii å si mer før kvinnen reiste seg opp og slo med knyttneven i ansiktet hans.',  # nopep8
                restriction='',
                orig_source='',
                translation_source=''))  # nopep8
        self.examples.add(
            dicts2wiki.Example(
                orig='No text in re element',
                translation='No text in re element',
                restriction='',
                orig_source='',
                translation_source=''))  # nopep8
        self.xmldictextractor = dicts2wiki.XmlDictExtractor(self.dictxml)

    def test_l2stem(self):
        got = self.xmldictextractor.l_or_t2stem(
            self.dictxml.find('.//l'),
            self.xmldictextractor.get_lang(self.dictxml.getroot()))
        want = dicts2wiki.Stem(lemma='njeazzi', lang='sme', pos='N')
        self.assertEqual(got, want)

    def test_t2stem(self):
        got = self.xmldictextractor.l_or_t2stem(
            self.dictxml.find('.//t'),
            self.xmldictextractor.get_lang(self.dictxml.find('.//tg')))
        want = dicts2wiki.Stem(lemma='ansikt', lang='nob', pos='N')
        self.assertEqual(got, want)

    def test_xg2example(self):
        got = self.xmldictextractor.xg2example(self.dictxml.find('.//xg'))
        want = dicts2wiki.Example(
            restriction='Kunne vært tryne',
            orig='Duohtavuohta časká njeacce vuostá.',
            translation='Sannheta slår mot ansiktet.',
            orig_source='a',
            translation_source='b')
        self.assertEqual(got, want)

    def test_tg2translation(self):
        want = dicts2wiki.Translation(
            restriction='i negative sammenhenger',
            translations=self.translations,
            examples=self.examples)
        got = self.xmldictextractor.tg2translation(self.dictxml.find('.//tg'))

        self.assertEqual(got, want)

    def test_e2tuple(self):
        self.maxDiff = None
        want = (dicts2wiki.Stem(lemma='njeazzi', lang='sme', pos='N'), [
            dicts2wiki.Translation(
                restriction='i negative sammenhenger',
                translations=self.translations,
                examples=self.examples)
        ])
        got = self.xmldictextractor.e2tuple(self.dictxml.find('.//e'))

        self.assertTupleEqual(want, got)

    def test_registerstems(self):
        want = defaultdict(list)
        want[dicts2wiki.Stem(lemma='njeazzi', lang='sme', pos='N')]
        want[dicts2wiki.Stem(lemma='ansikt', pos='N', lang='nob')]
        want[dicts2wiki.Stem(lemma='tryne', pos='N', lang='nob')]

        got = defaultdict(list)
        self.xmldictextractor.register_stems(got)

        self.assertDictEqual(got, want)

    def test_r2dict(self):
        self.maxDiff = None
        want = defaultdict(list)
        want[dicts2wiki.Stem(lemma='njeazzi', lang='sme', pos='N')]
        want[dicts2wiki.Stem(lemma='ansikt', pos='N', lang='nob')]
        want[dicts2wiki.Stem(lemma='tryne', pos='N', lang='nob')]

        want[dicts2wiki.Stem(lemma='njeazzi', lang='sme', pos='N')] = \
            [dicts2wiki.Translation(
                restriction='i negative sammenhenger',
                translations=self.translations,
                examples=self.examples)]

        got = defaultdict(list)
        self.xmldictextractor.r2dict(got)

        self.assertDictEqual(got, want)
