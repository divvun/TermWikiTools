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

from lxml import etree
from parameterized import parameterized

from termwikiimporter import dicts2wiki


class TestDicts(unittest.TestCase):
    """Test dicts xml to wiki functions."""

    @parameterized.expand([
        ('''
    <e>
        <lg>
            <l pos="N">gorálašvuohta</l>
        </lg>
        <mg>
            <tg xml:lang="nob">
                <t pos="N">relativitet</t>
            </tg>
        </mg>
    </e>
        ''', {
            'title':
            'sme:gorálašvuohta',
            'text':
            '''{e
|pos=N
}
{mg
|id=mg_00000001
}
{tg
|lang=nob
|pos=N
|lemmas=relativitet
|id=tg_00000001
|parent=mg_00000001
}
'''
        }),
        ('''
    <e>
        <lg>
            <l pos="N">bisnesalmmái</l>
        </lg>
        <mg>
            <tg xml:lang="nob">
                <t pos="N">bisnismann</t>
                <xg>
                    <x>Doppe ledje bisnesalbmát dreassain ja šlipsa vel.</x>
                    <xt>Der var det bisnismenn med dress og med slips også.</xt>
                </xg>
            </tg>
        </mg>
    </e>
            ''', {
            'title':
            'sme:bisnesalmmái',
            'text':
            '''{e
|pos=N
}
{mg
|id=mg_00000001
}
{tg
|lang=nob
|pos=N
|lemmas=bisnismann
|id=tg_00000001
|parent=mg_00000001
}
{xg
|parent=tg_00000001
|sme=Doppe ledje bisnesalbmát dreassain ja šlipsa vel.
|nob=Der var det bisnismenn med dress og med slips også.
}'''
        }),
    ])
    def test_conversion(self, xml_str, wiki_str):
        """Check that xml is converted to a dict."""
        self.assertDictEqual(
            dicts2wiki.expression2text('sme', etree.fromstring(xml_str)),
            wiki_str)

    def test_xg2text(self):
        """Test explanation group conversion."""
        explanation_group = etree.fromstring('''
            <xg>
                <x>Doppe ledje bisnesalbmát dreassain ja šlipsa vel.</x>
                <xt>Der var det bisnismenn med dress og med slips også.</xt>
            </xg>
        ''')
        want_xg = '''{xg
|parent=tg_00000001
|sme=Doppe ledje bisnesalbmát dreassain ja šlipsa vel.
|nob=Der var det bisnismenn med dress og med slips også.
}'''
        self.assertEqual(
            dicts2wiki.xg2text('tg_00000001', 'sme', 'nob', explanation_group),
            want_xg)

    def test_tg2text(self):
        """Test translation group conversion."""
        translation_group = etree.fromstring('''
            <tg xml:lang="nob">
                <t pos="N">bisnismann</t>
                <xg>
                    <x>Doppe ledje bisnesalbmát dreassain ja šlipsa vel.</x>
                    <xt>Der var det bisnismenn med dress og med slips også.</xt>
                </xg>
            </tg>
        ''')
        want = '''{tg
|lang=nob
|pos=N
|lemmas=bisnismann
|id=tg_00000001
|parent=mg_00000001
}
{xg
|parent=tg_00000001
|sme=Doppe ledje bisnesalbmát dreassain ja šlipsa vel.
|nob=Der var det bisnismenn med dress og med slips også.
}'''
        got = dicts2wiki.tg2text('mg_00000001', 'sme', 1, translation_group)
        self.assertEqual(got, want)

    def test_mg2text(self):
        """Test meaning group conversion."""
        meaning_group = etree.fromstring('''
        <mg>
            <tg xml:lang="nob">
                <t pos="N">bisnismann</t>
                <xg>
                    <x>Doppe ledje bisnesalbmát dreassain ja šlipsa vel.</x>
                    <xt>Der var det bisnismenn med dress og med slips også.</xt>
                </xg>
            </tg>
        </mg>
        ''')
        want = '''{mg
|id=mg_00000001
}
{tg
|lang=nob
|pos=N
|lemmas=bisnismann
|id=tg_00000001
|parent=mg_00000001
}
{xg
|parent=tg_00000001
|sme=Doppe ledje bisnesalbmát dreassain ja šlipsa vel.
|nob=Der var det bisnismenn med dress og med slips også.
}'''
        got = dicts2wiki.mg2text('sme', 1, meaning_group)
        self.assertEqual(got, want)
