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
from io import StringIO

from lxml import etree
from parameterized import parameterized

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
                        <xg re="Kunne vært tryne">
                            <x src="a">Duohtavuohta časká njeacce vuostá.</x>
                            <xt src="b">Sannheta slår mot ansiktet.</xt>
                        </xg>
                        <xg>
                            <x>Eanet ii ollen dadjat ovdal go nisu čuoččohii ja čorbmadii su njeazzái.</x>
                            <xt>Han rakk ii å si mer før kvinnen reiste seg opp og slo med knyttneven i ansiktet hans.</xt>
                        </xg>
                    </tg>
                </mg>
            </e>
        </r>
        '''))  # nopep8
        self.translations = set()
        self.translations.add(
            dicts2wiki.Stem(
                lemma='ansikt',
                pos='N',
                lang='nob'))
        self.translations.add(
            dicts2wiki.Stem(
                lemma='tryne',
                pos='N',
                lang='nob'))

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
                orig='Eanet ii ollen dadjat ovdal go nisu čuoččohii ja čorbmadii su njeazzái.',  # nopep8
                translation='Han rakk ii å si mer før kvinnen reiste seg opp og slo med knyttneven i ansiktet hans.',  # nopep8
                restriction='',
                orig_source='',
                translation_source=''))  # nopep8


        self.assertEqual(got, want)

        self.assertEqual(got, want)
