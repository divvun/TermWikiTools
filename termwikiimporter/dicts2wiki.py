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
        return '{}{}\nLemma={}\nLang={}\nPos={}\n{}'.format(
            '{{',
            type(self).__name__, self.lemma, self.lang, self.pos, '}}')


class TranslationGroup(object):
    def __init__(self, tolang):
        self.tolang = tolang
        self.translation_group = collections.defaultdict(list)

    @property
    def translations(self):
        return '@@'.join(
            [stem.pagename for stem in self.translation_group['t']])

    @property
    def examples(self):
        return '\n'.join([
            self.formatted_example(ex)
            for ex in self.translation_group['examples']
        ])

    @staticmethod
    def formatted_example(ex):
        return '{}\n|Original language={}\n|Translation={}\n{}'.format(
            '{{Example', ex[0], ex[1], '}}')

    def handle_tg(self, translation_element: etree.Element):
        for child in translation_element:
            uff = {
                't': self.handle_t,
                'xg': self.handle_tg_xg,
                're': self.handle_tg_re,
                'morph_expl': self.handle_morph,
            }

            uff[child.tag](child)

    def handle_t(self, translation) -> None:
        if translation.get('type') == 'expl' or translation.get(
                't_type') == 'expl':
            # TODO: handle type
            # print('Skip t element: {}'.format(translation.get('type')))
            return

        if not translation.get('pos'):
            raise UserWarning('No pos, translation')
        if translation.text is None:
            raise UserWarning('No translation, translation')
        if 'x' in translation.get('pos') or 'X' in translation.get('pos'):
            raise UserWarning('X in pos, translation')

        try:
            self.translation_group['t'].append(
                l2wiki(translation.text, GIELLA2TERMWIKI[self.tolang],
                       translation.get('pos').title()))
        else:
            raise UserWarning('translation fails in {}\n{}\n'.format(
                lineno(), etree.tostring(translation, encoding='unicode')))

    def handle_tg_xg(self, example_group: etree.Element) -> None:
        if (example_group.find('x').text is not None
                and example_group.find('xt').text is not None):
            self.translation_group['examples'].append(
                (example_group.find('x').text, example_group.find('xt').text))

    def handle_tg_re(self, restriction):
        pass

    def handle_morph(self, morphology):
        pass


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
                print(lineno(), self.filename, str(uppser), file=sys.stderr)
                print(etree.tostring(entry, encoding='unicode'), file=sys.stderr)

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
        print(
            child.tag,
            etree.tostring(child, encoding='unicode'),
            file=sys.stderr)

    def handle_lg(self, lemma_group: etree.Element) -> dict:
        lg_dict = {}

        for child in lemma_group.iter('l'):
            try:
                self.handle_l(child, lg_dict)
            except AttributeError:
                print(
                    'error in {}'.format(
                        etree.tostring(lemma_group, encoding='unicode')),
                    file=sys.stderr)

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
                except etree.XMLSyntaxError:
                    print('Syntax error in {}'.format(xml_file), file=sys.stderr)


def main() -> None:
    parse_dicts()
    filter_x()
    report_findings()
