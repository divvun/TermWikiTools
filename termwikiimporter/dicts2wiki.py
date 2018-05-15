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

import glob
import os

from lxml import etree

GIELLA2TERMWIKI = {
    'fin': 'fi',
    'nob': 'nb',
    'sma': 'sma',
    'sme': 'se',
    'smj': 'smj',
    'smn': 'smn',
    'swe': 'sv',
}


def dict2wiki(dictionary_xml: etree.ElementTree):
    """Turn a giella dictionary file into wiki.

    Args:
        dictfile: name of the dictionary file.
    """
    origlang = dictionary_xml.getroot().get(
        '{http://www.w3.org/XML/1998/namespace}lang')
    for entry in dictionary_xml.iter('e'):
        expression2text(GIELLA2TERMWIKI[origlang], entry)


def expression2text(entry_lang: str, entry_xml: etree.Element) -> None:
    """Turn an dictionary xml entry into wiki exportable dict.

    Args:
        entry_xml: An dictionary entry xml element.
        entry_lang: The language of the entry.

    Returns:
        A dict with a title and text element.
    """
    lemma_group = entry_xml.find('lg')
    if lemma_group is not None:
        handle_lg(lemma_group, entry_lang)
        for meaning_group in entry_xml.iter('mg'):
            handle_mg(meaning_group)


def handle_lg(lemma_group, entry_lang):
    for attr in lemma_group.keys():
        if attr not in ['freq']:
            raise SystemExit('{} tag: {} attr: {}'.format(
                68, lemma_group.tag, attr))

    for child in lemma_group:
        if child.tag == 'l':
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

            huff = [child.text, entry_lang]
            for attr in ['pos', 'type', 'nr']:
                if child.get(attr):
                    huff.append(child.get(attr))
            if lemma_group.get('freq'):
                huff.append(lemma_group.get('freq'))

            #print(', '.join(huff))

        elif child.tag in [
                'lsub', 'lc', 'analysis', 'mini_paradigm', 'lemma_ref'
        ]:
            pass
        elif child.tag == 'l_ref':
            for attr in child.keys():
                if attr not in []:
                    raise SystemExit('{} tag: {} attr: {}'.format(
                        91, child.tag, attr))
            print(child.tag)
        else:
            raise SystemExit(102, etree.tostring(child, encoding='unicode'))


def handle_mg(meaning_group):
    for attr in meaning_group.keys():
        if attr not in ['src', 're', 'id', 'x']:
            # ditch id
            print(etree.tostring(meaning_group, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                108, meaning_group.tag, attr))

    for child in meaning_group:
        if child.tag not in ['tg', 're']:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(115, child.tag))
        elif child.tag == 'tg':
            handle_tg(child)
        elif child.tag == 're':
            handle_re(child)
        else:
            raise SystemExit(128)


def handle_tg(translation_group):
    for attr in translation_group.keys():
        if attr not in [
                '{http://www.w3.org/XML/1998/namespace}lang', 're', 'check'
        ]:
            # ditch: check
            print(etree.tostring(translation_group, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                136, translation_group.tag, attr))

    for child in translation_group:
        if child.tag not in ['t', 'xg', 're', 'morph_expl']:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(144, child.tag))

        uff = {
            't': handle_t,
            'xg': handle_tg_xg,
            're': handle_tg_re,
            'morph_expl': handle_morph,
            'l': handle_tg_l,
        }

        uff[child.tag](child)


def handle_re(res):
    for attr in res.keys():
        if attr not in []:
            #
            print(etree.tostring(res, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                167, res.tag, attr))

    for child in res:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(176, child.tag))


def handle_t(translation):
    for attr in translation.keys():
        if attr not in [
                'pos', 'freq', 'nr', 'wf', 'l_par', 'syn_dash', 't_tld', 'mwe',
                'attr', 'r_par', 'syn', 're', 'xxx', 'stem', 'pg', 'dialect',
                'hid', 'margo', 'soggi', 'type', 'case', 'src', 'num', 'illpl',
                'class', 'context', 'minip', 'p3p', 'vow', 'umlaut', 'diph',
                'mod', 'pers', 'alt_str', 'dial', 'href', 'stat', 'value',
                't_type', 'spec', 'var', 'sem_type', 'reg', 'country',
                'comment', 'x', 'gen_only'
        ]:
            #
            print(etree.tostring(translation, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                194, translation.tag, attr))

    for child in translation:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(202, child.tag))


def handle_tg_xg(example_group):
    for attr in example_group.keys():
        if attr not in ['re']:
            #
            print(etree.tostring(example_group, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                211, example_group.tag, attr))

    for child in example_group:
        if child.tag not in ['x', 'xt', 're']:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(219, child.tag))


def handle_tg_re(restriction):
    for attr in restriction.keys():
        if attr not in ['fra_ref', 'x', 'comment']:
            #
            print(etree.tostring(restriction, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                227, restriction.tag, attr))

    for child in restriction:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(235, child.tag))


def handle_morph(morphology):
    for attr in morphology.keys():
        if attr not in []:
            #
            print(etree.tostring(morphology, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                211, morphology.tag, attr))

    for child in morphology:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(219, child.tag))


def handle_tg_l(lemma):
    for attr in lemma.keys():
        if attr not in ['pos']:
            #
            print(etree.tostring(lemma, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                259, lemma.tag, attr))

    for child in lemma:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(267, child.tag))


def main():
    parser = etree.XMLParser(remove_comments=True)
    for pair in [
            'finsme', 'finsmn', 'nobsma', 'nobsme', 'nobsmj', 'nobsmj',
            'smafin', 'smanob', 'smasme', 'smeeng', 'smefin', 'smenob',
            'smesma', 'smesmj', 'smesmn', 'smjnob', 'smjsme', 'smnsme',
            'swesma'
    ]:
        dict_root = os.path.join(
            os.getenv('GTHOME'), 'words/dicts', pair, 'src')
        for xml_file in glob.glob(dict_root + '/*.xml'):
            if not xml_file.endswith('meta.xml'):
                print(xml_file)
                dict2wiki(etree.parse(xml_file, parser=parser))
