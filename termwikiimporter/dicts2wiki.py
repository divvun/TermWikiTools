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
import attr
import collections
import datetime
import glob
import os
import sys

from lxml import etree

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

    #def __str__(self):
        #"""
        #Automatically created by attrs.
        #"""
        #return '\n'.join([uff for uff in self.__dict__.iteritems()])


@attr.s
class DictParser(object):
    fromlang = attr.ib()
    tolang = attr.ib()
    filename = attr.ib()

    def dict2wiki(self):
        """Turn a giella dictionary file into wiki."""
        parser = etree.XMLParser(remove_comments=True)
        dictionary_xml = etree.parse(self.filename, parser=parser)

        origlang = dictionary_xml.getroot().get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        if origlang != self.fromlang:
            raise SystemExit('origlang! {} {}'.format(origlang, self.fromlang))

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
            self.handle_lg(lemma_group)
            for meaning_group in entry_xml.iter('mg'):
                self.handle_mg(meaning_group)
        else:
            # TODO: why?
            found['e_no_lg'] += 1

    def handle_lg(self, lemma_group):
        for attr in lemma_group.keys():
            if attr not in ['freq']:
                raise SystemExit('{} tag: {} attr: {}'.format(
                    68, lemma_group.tag, attr))

        for child in lemma_group:
            if child.tag == 'l':
                if 'x' in child.get('pos'):
                    raise UserWarning('X in pos')
                found['l_in_lg'] += 1
                for attr in child.keys():
                    if attr not in [
                            'pos', 'type', 'nr', 'vmax', 'illpl', 'hid', 'r1_par',
                            'tt_auto', 'comma', 'r2_par', 'syn', 'tt', 'syn_or',
                            'src', 'value', 't_type', 're', 'alt_str', 'til_ref',
                            'orig_entry', 'case', 'mod', 'sem_type', 'pg', 'stem',
                            'dialect', 'margo', 'soggi', 'class', 'umlaut', 'vow',
                            'p3p', 'diph', 'context', 'minip', 'num', 'attr',
                            'spec', 'comment', 'paradigme'
                    ]:
                        raise SystemExit('{} tag: {} attr: {} -- {}'.format(
                            74, child.tag, attr, child.text))

                huff = [child.text, self.fromlang]
                for attr in ['pos', 'type', 'nr']:
                    if child.get(attr):
                        huff.append(child.get(attr))
                if lemma_group.get('freq'):
                    huff.append(lemma_group.get('freq'))
                try:
                    self.l2wiki(child.text, GIELLA2TERMWIKI[self.fromlang],
                                child.get('pos').title())
                except AttributeError:
                    print('error in {}'.format(etree.tostring(lemma_group, encoding='unicode')), file=sys.stderr)

            elif child.tag in [
                    'lsub', 'lc', 'analysis', 'mini_paradigm', 'lemma_ref'
            ]:
                pass
            elif child.tag == 'l_ref':
                for attr in child.keys():
                    if attr not in []:
                        raise SystemExit('{} tag: {} attr: {}'.format(
                            91, child.tag, attr))
                print(child.tag, etree.tostring(child, encoding='unicode'), file=sys.stderr)
            else:
                raise SystemExit(102, etree.tostring(child, encoding='unicode'))

    def l2wiki(self, lemma, language, pos):
        stem = Stem(lemma=lemma, lang=language, pos=pos)
        if stem in lemmadict[lemma]:
            found['exists'] += 1
        else:
            lemmadict[lemma].add(stem)
            found['added'] += 1
            found[language] += 1

        #print(stem)

    def handle_mg(self, meaning_group):
        for attr in meaning_group.keys():
            if attr not in ['src', 're', 'id', 'x']:
                # ditch id
                print(etree.tostring(meaning_group, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    108, meaning_group.tag, attr))

        for child in meaning_group:
            if child.tag == 'tg':
                tg_lang = child.get('{http://www.w3.org/XML/1998/namespace}lang')
                if tg_lang != self.tolang:
                    print(tg_lang, self.tolang, file=sys.stderr)

                if tg_lang == self.tolang:
                    self.handle_tg(child)
                else:
                    raise UserWarning(
                        'tg of wrong language. Is {}, should be {}'.format(
                            tg_lang, self.tolang))
            elif child.tag == 're':
                self.handle_re(child)
            else:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(115, child.tag))

    def handle_tg(self, translation_group):
        for attr in translation_group.keys():
            if attr not in [
                    '{http://www.w3.org/XML/1998/namespace}lang', 're', 'check'
            ]:
                # ditch: check
                print(etree.tostring(translation_group, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    136, translation_group.tag, attr))

        for child in translation_group:
            if child.tag not in ['t', 'xg', 're', 'morph_expl']:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(144, child.tag))

            uff = {
                't': self.handle_t,
                'xg': self.handle_tg_xg,
                're': self.handle_tg_re,
                'morph_expl': self.handle_morph,
            }

            uff[child.tag](child)

    def handle_t(self, translation):
        if translation.get('type') == 'expl' or translation.get('t_type') == 'expl':
            # TODO: handle type
            # print('Skip t element: {}'.format(translation.get('type')))
            return

        if not translation.get('pos'):
            raise UserWarning('No pos, translation')
        if translation.text is None:
            raise UserWarning('No translation, translation')

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
                    194, translation.tag, attr))

        for child in translation:
            if child.tag not in []:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(202, child.tag))

        try:
            self.l2wiki(translation.text, GIELLA2TERMWIKI[self.tolang], translation.get('pos').title())
        except AttributeError:
            print('error in {}'.format(etree.tostring(translation, encoding='unicode')), file=sys.stderr)

    def handle_tg_xg(self, example_group):
        for attr in example_group.keys():
            if attr not in ['re']:
                print(etree.tostring(example_group, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    211, example_group.tag, attr))

        for child in example_group:
            if child.tag not in ['x', 'xt', 're']:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(219, child.tag))

    def handle_tg_re(self, restriction):
        for attr in restriction.keys():
            if attr not in ['fra_ref', 'x', 'comment']:
                #
                print(etree.tostring(restriction, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    227, restriction.tag, attr))

        for child in restriction:
            if child.tag not in []:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(235, child.tag))

    def handle_morph(self, morphology):
        for attr in morphology.keys():
            if attr not in []:
                #
                print(etree.tostring(morphology, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    211, morphology.tag, attr))

        for child in morphology:
            if child.tag not in []:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(219, child.tag))

    def handle_re(self, res):
        for attr in res.keys():
            if attr not in []:
                #
                print(etree.tostring(res, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} attr: {}'.format(
                    167, res.tag, attr))

        for child in res:
            if child.tag not in []:
                # ditch:
                print(etree.tostring(child, encoding='unicode'), file=sys.stderr)
                raise SystemExit('line: {} tag: {} '.format(176, child.tag))


def main():
    outdir = datetime.datetime.now().isoformat()
    os.makedirs(outdir)

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
                print(xml_file)
                dictparser = DictParser(filename=xml_file, fromlang=pair[:3], tolang=pair[3:])
                dictparser.dict2wiki()

    for lemma in lemmadict:
        if len(lemmadict[lemma]) > 1:
            for stem in lemmadict[lemma]:
                print('{}: {}'.format(lemma, stem))
            print()

    notlang = ['added', 'exists', 'total', 'e_no_lg', 'l_in_lg']
    for key in notlang:
        print(key, found[key])
    print('Try added', found['added'] + found['exists'])

    for key in found:
        if key not in notlang:
            print(key, found[key])
