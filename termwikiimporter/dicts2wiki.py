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
"""Functions to import and export giella xml dicts to the TermWiki."""
import collections
import glob
import inspect
import os
import sys

import attr
from lxml import etree


def lineno():
    """Return the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


GIELLA2TERMWIKI = {
    'eng': 'en',
    'fin': 'fi',
    'fra': 'fr',
    'nob': 'nb',
    'sma': 'sma',
    'sme': 'se',
    'smj': 'smj',
    'smn': 'smn',
    'swe': 'sv',
}


@attr.s(frozen=True)
class Stem(object):
    """Representation of giella l and t dictionary elements."""
    lemma = attr.ib(validator=attr.validators.instance_of(str))
    lang = attr.ib(validator=attr.validators.instance_of(str))
    pos = attr.ib(validator=attr.validators.instance_of(str))

    @property
    def pagename(self):
        return '{} {} {}'.format(self.lemma, self.lang, self.pos)

    @property
    def stempagename(self):
        return '{}:{}'.format(type(self).__name__, self.pagename)

    @property
    def content(self):
        return '{}{}\n|Lemma={}\n|Lang={}\n|Pos={}\n{}'.format(
            '{{',
            type(self).__name__, self.lemma, self.lang, self.pos, '}}')


@attr.s(frozen=True)
class Translation(object):
    """Representation of a giella tg dictionary element."""
    restriction = attr.ib(validator=attr.validators.instance_of(str))
    translations = attr.ib(validator=attr.validators.instance_of(set))
    examples = attr.ib(validator=attr.validators.instance_of(set))


class Example(object):
    """Representation of a giella xg dictionary element."""
    restriction = attr.ib(validator=attr.validators.instance_of(str))
    orig = attr.ib(validator=attr.validators.instance_of(str))
    translation = attr.ib(validator=attr.validators.instance_of(str))
    orig_source = attr.ib(validator=attr.validators.instance_of(str))
    translation_source = attr.ib(validator=attr.validators.instance_of(str))


@attr.s
class XmlDictExtractor(object):
    fromlang = attr.ib()
    tolang = attr.ib()
    dictxml = attr.ib()

    @staticmethod
    def l_or_t2stem(t_element: etree.Element, language: str) -> Stem:
        """Turn either an l or t giella dictionary element into a Stem object."""
        return Stem(
            lemma=t_element.text, lang=language, pos=t_element.get('pos'))

    @staticmethod
    def xg2example(example_group: etree.Element) -> Example:
        """Turn an xg giella dictionary element into an Example object."""
        restriction = example_group.get('re') \
            if example_group.get('re') is not None else ''
        orig_source = example_group.find('.//x[@src]').get('src') \
            if example_group.find('.//x[@src]') is not None else ''
        translation_source = example_group.find('.//xt[@src]').get('src') \
            if example_group.find('.//xt[@src]') is not None else ''

        return Example(
            restriction=restriction,
            orig=example_group.find('.//x').text,
            translation=example_group.find('.//xt').text,
            orig_source=orig_source,
            translation_source=translation_source)

    def tg2translation(self, tg_element: etree.Element) -> Translation:
        """Turn a tg giella dictionary element into a Translation object."""
        restriction = tg_element.find('./re').text \
            if tg_element.find('./re') is not None else ''
        translations = {
            self.l_or_t2stem(t_element, self.get_lang(tg_element))
            for t_element in tg_element.xpath('.//t[@pos]')
        }
        examples = {
            self.xg2example(example_group)
            for example_group in tg_element.iter('xg')
        }

        return Translation(
            restriction=restriction,
            translations=translations,
            examples=examples)

    @staticmethod
    def get_lang(element: etree.Element) -> str:
        """Get the xml:lang attribute of an etree Element."""
        return element.get('{http://www.w3.org/XML/1998/namespace}lang')

    def e2tuple(self, entry: etree.Element) -> tuple:
        """Turn an e giella dictionary element in to a tuple."""
        return (self.l_or_t2stem(entry.find('.//l'), self.fromlang), [
            self.tg2translation(translation_group)
            for translation_group in entry.iter('tg')
            if self.get_lang(translation_group) == self.tolang
        ])

    def register_stems(self, stemdict: collections.defaultdict) -> None:
        """Register all stems found in a giella dictionary file."""
        origlang = self.get_lang(self.dictxml.getroot())

        for stem in self.dictxml.xpath('.//l[@pos]'):
            stemdict[self.l_or_t2stem(stem, origlang)]

        for translation_group in self.dictxml.iter('tg'):
            if self.get_lang(translation_group) == self.tolang:
                for translation in translation_group.iter('t'):
                    stemdict[self.l_or_t2stem(translation, self.tolang)]

    def r2dict(self, stemdict: collections.defaultdict) -> None:
        """Copy a giella dictionary file into a dict."""
        self.register_stems(stemdict)
        for entry_element in self.dictxml.iter('e'):
            entry = self.e2tuple(entry_element)
            stemdict[entry[0]] = entry[1]


def parse_dicts() -> None:
    for pair in [
            'finsme', 'finsmn', 'nobsma', 'nobsme', 'nobsmj', 'nobsmj',
            'smafin', 'smanob', 'smasme', 'smeeng', 'smefin', 'smenob',
            'smesma', 'smesmj', 'smesmn', 'smjnob', 'smjsme', 'smnsme',
            'swesma'
    ]:
        dict_root = os.path.join(
            os.getenv('GTHOME'), 'words/dicts', pair, 'src')
        for xml_file in glob.glob(dict_root + '/*.xml'):
            if not xml_file.endswith('meta.xml') and 'Der_' not in xml_file:
                # TODO: handle Der_ files
                try:
                    print(xml_file)
                    dictparser = DictParser(
                        filename=xml_file, fromlang=pair[:3], tolang=pair[3:])
                    dictparser.dict2wiki()
                except etree.XMLSyntaxError as error:
                    print(
                        'Syntax error in {} '
                        'with the following error:\n{}\n'.format(xml_file, error), file=sys.stderr)


def main() -> None:
    parse_dicts()
