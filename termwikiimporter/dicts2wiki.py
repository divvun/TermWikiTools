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
LEMMADICT = collections.defaultdict(set)
FOUND = collections.defaultdict(int)


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
class DictParser(object):
    fromlang = attr.ib()
    tolang = attr.ib()
    filename = attr.ib()

    def dict2wiki(self):
        """Turn a giella dictionary file into wiki."""
        parser = etree.XMLParser(remove_comments=True, dtd_validation=True)
        dictionary_xml = etree.parse(self.filename, parser=parser)

        origlang = dictionary_xml.getroot().get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        if origlang != self.fromlang:
            raise SystemExit('{} origlang! {} {}'.format(
                lineno(), origlang, self.fromlang))

        for entry in dictionary_xml.iter('e'):
            FOUND['total'] += 1
            try:
                self.expression2text(entry)
            except UserWarning as uppser:
                print('{}:\nError: {}\nElement:\n{}'.format(
                    self.filename, str(uppser),
                    etree.tostring(entry, encoding='unicode')),
                    file=sys.stderr)

    def expression2text(self, entry_xml: etree.Element) -> None:
        """Turn an dictionary xml entry into wiki exportable dict.

        Args:
            entry_xml: An dictionary entry xml element.
        """
        lemma_group = entry_xml.find('lg')
        if lemma_group is not None:
            lg_dict = self.handle_lg(lemma_group)
            for meaning_group in entry_xml.iter('mg'):
                self.handle_mg(meaning_group, lg_dict)
        else:
            # TODO: why?
            FOUND['e_no_lg'] += 1

    def handle_l(self, child: etree.Element, lg_dict):
        FOUND['l_in_lg'] += 1
        lg_dict['stem'] = l2wiki(child.text, GIELLA2TERMWIKI[self.fromlang],
                                 child.get('pos').title())

    def handle_lref(self, child: etree.Element):
        # TODO: Handle properly
        pass
        # print(child.tag, etree.tostring(child, encoding='unicode'), file=sys.stderr)

    def handle_lg(self, lemma_group: etree.Element) -> dict:
        lg_dict = {}

        for child in lemma_group.iter('l'):
            self.handle_l(child, lg_dict)

        for child in lemma_group.iter('l_ref'):
            self.handle_lref(child)

        return lg_dict

    def handle_tg(self, child: etree.Element, lg_dict):
        tg_lang = child.get('{http://www.w3.org/XML/1998/namespace}lang')
        if tg_lang == self.tolang:
            # Do not care about entries not in self.tolang
            translation_group = TranslationGroup(self.tolang)
            translation_group.handle_tg(child)
            print('{}\n|Stempage={}\n|Translation stem={}\n{}'.format(
                '{{Dictionary', lg_dict['stem'].pagename,
                translation_group.translations, '}}'))
            print(translation_group.examples)
            print()

    def handle_mg(self, meaning_group: etree.Element, lg_dict: dict):
        for child in meaning_group.iter('tg'):
            self.handle_tg(child, lg_dict)

        for child in meaning_group.iter('re'):
            self.handle_re(child)

    def handle_re(self, res):
        pass


def l_or_t2stem(t_element: etree.Element, language: str) -> Stem:
    """Turn either an l or t giella dictionary element into a Stem object."""
    return Stem(
            lemma=t_element.text,
            lang=language,
            pos=t_element.get('pos'))


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


def tg2translation(tg_element: etree.Element) -> Translation:
    """Turn a tg giella dictionary element into a Translation object."""
    restriction = tg_element.find('./re').text \
        if tg_element.find('./re') is not None else ''
    translations = {l_or_t2stem(t_element, get_lang(tg_element))
                    for t_element in tg_element.xpath('.//t[@pos]')}
    examples = {xg2example(example_group)
                for example_group in tg_element.iter('xg')}

    return Translation(
        restriction=restriction,
        translations=translations,
        examples=examples)


def get_lang(element: etree.Element) -> str:
    """Get the xml:lang attribute of an etree Element."""
    return element.get('{http://www.w3.org/XML/1998/namespace}lang')


def e2dict(entry: etree.Element, fromlang: str, tolang: str) -> tuple:
    """Turn an e giella dictionary element in to a tuple."""
    return (
        l_or_t2stem(entry.find('.//l'), fromlang),
        [tg2translation(translation_group)
         for translation_group in entry.iter('tg')
         if get_lang(translation_group) == tolang])


def l2wiki(lemma: str, language: str, pos: str) -> Stem:
    stem = Stem(lemma=lemma, lang=language, pos=pos)
    if stem in LEMMADICT[lemma]:
        FOUND['exists'] += 1
    else:
        LEMMADICT[lemma].add(stem)
        FOUND['added'] += 1
        FOUND[language] += 1

    return stem


def filter_x() -> None:
    for lemma in LEMMADICT:
        foundx = False
        stemstrs = []
        for stem in LEMMADICT[lemma]:
            if 'X' in stem.pos:
                foundx = True
            stemstrs.append(str(stem))

        if foundx:
            print('\n'.join(stemstrs))
            print()


def report_findings() -> None:
    notlang = ['added', 'exists', 'total', 'e_no_lg', 'l_in_lg']
    for key in notlang:
        print(key, FOUND[key])
    print('Try added', FOUND['added'] + FOUND['exists'])

    for key in FOUND:
        if key not in notlang:
            print(key, FOUND[key])


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
    filter_x()
    report_findings()
