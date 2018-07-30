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
lemmadict = collections.defaultdict(set)
found = collections.defaultdict(int)


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
            type(self).__name__,
            self.lemma,
            self.lang,
            self.pos,
            '}}')


class TranslationGroup(object):
    wanted_attributes = {
        'tg': ['{http://www.w3.org/XML/1998/namespace}lang', 're', 'check'],
        'xg': ['re'],
        're': ['fra_ref', 'x', 'comment'],
        'morph_expl': [],
    }
    wanted_children = {
        'tg': ['t', 'xg', 're', 'morph_expl'],
        'xg': ['x', 'xt', 're'],
        're': [],
        'morph_expl': [],
    }

    def __init__(self, tolang):
        self.tolang = tolang
        self.translation_group = collections.defaultdict(list)

    @property
    def translations(self):
        return '@@'.join([stem.pagename
                          for stem in self.translation_group['t']])

    @property
    def examples(self):
        return '\n'.join([self.formatted_example(ex)
                          for ex in self.translation_group['examples']])

    @staticmethod
    def formatted_example(ex):
        return '{}\n|Original language={}\n|Translation={}\n{}'.format(
            '{{Example', ex[0], ex[1], '}}')

    def has_wanted_attributes(self, element: etree.Element):
        for attr in element.keys():
            if attr not in self.wanted_attributes[element.tag]:
                print(etree.tostring(element, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    lineno(), element.tag, attr))

    def has_wanted_children(self, element: etree.Element):
        for child in element:
            if child.tag not in self.wanted_children[element.tag]:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(lineno(), child.tag))

    def handle_tg(self, translation_element: etree.Element):
        self.has_wanted_attributes(translation_element)
        self.has_wanted_children(translation_element)
        for child in translation_element:
            uff = {
                't': self.handle_t,
                'xg': self.handle_tg_xg,
                're': self.handle_tg_re,
                'morph_expl': self.handle_morph,
            }

            uff[child.tag](child)

    def handle_t(self, translation) -> None:
        if translation.get('type') == 'expl' or translation.get('t_type') == 'expl':
            # TODO: handle type
            # print('Skip t element: {}'.format(translation.get('type')))
            return

        if not translation.get('pos'):
            raise UserWarning('No pos, translation')
        if translation.text is None:
            raise UserWarning('No translation, translation')
        if 'x' in translation.get('pos') or 'X' in translation.get('pos'):
            raise UserWarning('X in pos, translation')

        for attr in translation.keys():
            if attr not in [
                    'alt_str',
                    'attr',
                    'case',
                    'class',
                    'comment',
                    'context',
                    'country',
                    'dial',
                    'dialect',
                    'diph',
                    'expl',
                    'freq',
                    'gen_only',
                    'grammar',
                    'hid',
                    'href',
                    'illpl',
                    'l_par',
                    'margo',
                    'minip',
                    'mod',
                    'mwe',
                    'nr',
                    'num',
                    'p3p',
                    'pers',
                    'pg',
                    'pos',
                    'r_par',
                    're',
                    'reg',
                    'sem_type',
                    'soggi',
                    'spec',
                    'src',
                    'stat',
                    'stem',
                    'syn',
                    'syn_dash',
                    't_tld',
                    't_type',
                    'type',
                    'umlaut',
                    'value',
                    'var',
                    'vow',
                    'wf',
                    'x',
                    'xxx',
            ]:
                #
                print(etree.tostring(translation, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    lineno(), translation.tag, attr))

        for child in translation:
            if child.tag not in []:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(lineno(), child.tag))

        try:
            self.translation_group['t'].append(l2wiki(
                translation.text,
                GIELLA2TERMWIKI[self.tolang],
                translation.get('pos').title()))
        except AttributeError:
            print('error in {}'.format(etree.tostring(translation, encoding='unicode')), file=sys.stderr)

    def handle_tg_xg(self, example_group: etree.Element) -> None:
        self.has_wanted_attributes(example_group)
        for child in example_group:
            self.has_wanted_children(example_group)

        if (example_group.find('x').text is not None and
            example_group.find('xt').text is not None):
            self.translation_group['examples'].append(
                (example_group.find('x').text,
                example_group.find('xt').text))

    def handle_tg_re(self, restriction):
        self.has_wanted_attributes(restriction)

        for child in restriction:
            self.has_wanted_children(restriction)

    def handle_morph(self, morphology):
        self.has_wanted_attributes(morphology)

        for child in morphology:
            self.has_wanted_children(morphology)


@attr.s
class DictParser(object):
    fromlang = attr.ib()
    tolang = attr.ib()
    filename = attr.ib()

    wanted_attributes = {
        'lg': ['freq'],
        'l': ['alt_str', 'attr', 'case', 'class', 'comma', 'comment', 'context', 'dialect', 'diph', 'hid', 'illpl', 'margo', 'minip', 'mod', 'nr', 'num', 'orig_entry', 'p3p', 'paradigme', 'pg', 'pos', 'r1_par', 'r2_par', 're', 'sem_type', 'soggi', 'spec', 'src', 'stem', 'syn', 'syn_or', 't_type', 'til_ref', 'tt', 'tt_auto', 'type', 'umlaut', 'value', 'vmax', 'vow',],
        'l_ref': [],
        'mg': ['src', 're', 'id', 'x'],
        'tg': ['{http://www.w3.org/XML/1998/namespace}lang', 're', 'check'],
        're': ['x', 'comment'],
    }
    wanted_children = {
        'lg': ['l', 'lsub', 'lc', 'analysis', 'mini_paradigm', 'lemma_ref', 'l_ref'],
        'l': [],
        'l_ref': [],
        'mg': ['tg', 're'],
        'tg': ['t', 'xg', 're'],
        're': [],
    }

    def has_wanted_attributes(self, element: etree.Element):
        for attr in element.keys():
            if attr not in self.wanted_attributes[element.tag]:
                print(etree.tostring(element, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    lineno(), element.tag, attr))

    def has_wanted_children(self, element: etree.Element):
        for child in element:
            if child.tag not in self.wanted_children[element.tag]:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(lineno(), child.tag))

    def dict2wiki(self):
        """Turn a giella dictionary file into wiki."""
        parser = etree.XMLParser(remove_comments=True)
        dictionary_xml = etree.parse(self.filename, parser=parser)

        origlang = dictionary_xml.getroot().get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        if origlang != self.fromlang:
            raise SystemExit('origlang! {} {}'.format(lineno(), origlang, self.fromlang))

        for entry in dictionary_xml.iter('e'):
            found['total'] += 1
            try:
                self.expression2text(entry)
            except UserWarning as uppser:
                print(str(uppser), file=sys.stderr)
                print(etree.tostring(entry, encoding='unicode'), file=sys.stderr)

    def expression2text(self, entry_xml: etree.Element) -> None:
        """Turn an dictionary xml entry into wiki exportable dict.

        Args:
            entry_xml: An dictionary entry xml element.
        """
        lemma_group = entry_xml.find('lg')
        if lemma_group is not None:
            lg = self.handle_lg(lemma_group)
            for meaning_group in entry_xml.iter('mg'):
                self.handle_mg(meaning_group, lg)
        else:
            # TODO: why?
            found['e_no_lg'] += 1

    def handle_l(self, child: etree.Element, lg_dict):
        self.has_wanted_attributes(child)
        self.has_wanted_children(child)

        if 'x' in child.get('pos') or 'X' in child.get('pos'):
            raise UserWarning('X in pos')

        found['l_in_lg'] += 1
        lg_dict['stem'] = l2wiki(child.text, GIELLA2TERMWIKI[self.fromlang], child.get('pos').title())

    def handle_lref(self, child: etree.Element):
        self.has_wanted_attributes(child)
        self.has_wanted_children(child)
        print(child.tag, etree.tostring(child, encoding='unicode'), file=sys.stderr)

    def handle_lg(self, lemma_group: etree.Element) -> dict:
        self.has_wanted_attributes(lemma_group)
        self.has_wanted_children(lemma_group)

        lg_dict = {}

        for child in lemma_group.iter('l'):
            try:
                self.handle_l(child, lg_dict)
            except AttributeError:
                print('error in {}'.format(etree.tostring(lemma_group, encoding='unicode')), file=sys.stderr)

        for child in lemma_group.iter('l_ref'):
            self.handle_lref(child)

        return lg_dict

    def handle_tg(self, child: etree.Element, lg):
        self.has_wanted_attributes(child)
        self.has_wanted_children(child)

        tg_lang = child.get('{http://www.w3.org/XML/1998/namespace}lang')
        if tg_lang != self.tolang:
            raise UserWarning(
                'tg of wrong language. Is {}, should be {}'.format(
                    tg_lang, self.tolang))
        else:
            tg = TranslationGroup(self.tolang)
            tg.handle_tg(child)
            print('{}\n|Stempage={}\n|Translation stem={}\n{}'.format(
                '{{Dictionary', lg['stem'].pagename, tg.translations,
                '}}'))
            print(tg.examples)
            print()

    def handle_mg(self, meaning_group: etree.Element, lg: dict):
        self.has_wanted_attributes(meaning_group)
        self.has_wanted_children(meaning_group)

        for child in meaning_group.iter('tg'):
            self.handle_tg(child, lg)

        for child in meaning_group.iter('re'):
            self.handle_re(child)

    def handle_re(self, res):
        self.has_wanted_attributes(res)
        self.has_wanted_children(res)


def l2wiki(lemma: str, language: str, pos: str) -> Stem:
    stem = Stem(lemma=lemma, lang=language, pos=pos)
    if stem in lemmadict[lemma]:
        found['exists'] += 1
    else:
        lemmadict[lemma].add(stem)
        found['added'] += 1
        found[language] += 1

    return stem


def filter_x() -> None:
    for lemma in lemmadict:
        foundx = False
        stemstrs = []
        for stem in lemmadict[lemma]:
            if 'X' in stem.pos:
                foundx = True
            stemstrs.append(str(stem))

        if foundx:
            print('\n'.join(stemstrs))
            print()


def report_findings():
    notlang = ['added', 'exists', 'total', 'e_no_lg', 'l_in_lg']
    for key in notlang:
        print(key, found[key])
    print('Try added', found['added'] + found['exists'])

    for key in found:
        if key not in notlang:
            print(key, found[key])


def parse_dicts():
    for pair in [
        'finsme',
        'finsmn',
        'nobsma',
        'nobsme',
        'nobsmj',
        'nobsmj',
        'smafin',
        'smanob',
        'smasme',
        'smeeng',
        'smefin',
        'smenob',
        'smesma',
        'smesmj',
        'smesmn',
        'smjnob',
        'smjsme',
        'smnsme',
        'swesma'
    ]:
        dict_root = os.path.join(
            os.getenv('GTHOME'), 'words/dicts', pair, 'src')
        for xml_file in glob.glob(dict_root + '/*.xml'):
            if not xml_file.endswith('meta.xml') and 'Der_' not in xml_file:
                # TODO: handle Der_ files
                print(xml_file)
                dictparser = DictParser(filename=xml_file, fromlang=pair[:3], tolang=pair[3:])
                dictparser.dict2wiki()


def main():
    parse_dicts()
    filter_x()
    report_findings()
