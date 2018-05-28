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

import datetime
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


def dict2wiki(dictionary_xml: etree.ElementTree, outdir):
    """Turn a giella dictionary file into wiki.

    Args:
        dictfile: name of the dictionary file.
    """
    origlang = dictionary_xml.getroot().get(
        '{http://www.w3.org/XML/1998/namespace}lang')
    for entry in dictionary_xml.iter('e'):
        try:
            expression2text(GIELLA2TERMWIKI[origlang], entry, outdir)
        except UserWarning as uppser:
            print(str(uppser))
            print(etree.tostring(entry, encoding='unicode'))


def expression2text(entry_lang: str, entry_xml: etree.Element, outdir) -> None:
    """Turn an dictionary xml entry into wiki exportable dict.

    Args:
        entry_xml: An dictionary entry xml element.
        entry_lang: The language of the entry.

    Returns:
        A dict with a title and text element.
    """
    lemma_group = entry_xml.find('lg')
    if lemma_group is not None:
        handle_lg(lemma_group, entry_lang, outdir)
        for meaning_group in entry_xml.iter('mg'):
            handle_mg(meaning_group, outdir)


giella2termwiki = {
    'fin': 'fi',
    'nob': 'nb',
    'sma': 'sma',
    'sme': 'se',
    'smj': 'smj',
    'smn': 'smn',
}


def l2wiki(lemma, lang, pos, outdir):
    with open('{}/Stem:{} {} {}'.format(outdir, lemma.replace('/', '\\'), lang, pos), 'w') as lemma:
        print('|Lemma={}'.format(lemma), file=lemma)
        print('|Lang={}'.format(lang), file=lemma)
        print('|Pos={}'.format(pos), file=lemma)


def handle_lg(lemma_group, entry_lang, outdir):
    if entry_lang is None:
        raise UserWarning('Lemmagroup, no lang')
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
            try:
                l2wiki(child.text, entry_lang, child.get('pos').title(), outdir)
            except AttributeError:
                print('error in {}'.format(etree.tostring(lemma_group, encoding='unicode')))

        elif child.tag in [
                'lsub', 'lc', 'analysis', 'mini_paradigm', 'lemma_ref'
        ]:
            pass
        elif child.tag == 'l_ref':
            for attr in child.keys():
                if attr not in []:
                    raise SystemExit('{} tag: {} attr: {}'.format(
                        91, child.tag, attr))
            print(child.tag, etree.tostring(child, encoding='unicode'))
        else:
            raise SystemExit(102, etree.tostring(child, encoding='unicode'))


def handle_mg(meaning_group, outdir):
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
            handle_tg(child, outdir)
        elif child.tag == 're':
            handle_re(child)
        else:
            raise SystemExit(128)


def handle_tg(translation_group, outdir):
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
        }

        uff[child.tag](child, translation_group.get('{http://www.w3.org/XML/1998/namespace}lang'), outdir)


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


def handle_t(translation, translation_lang, outdir):
    if translation.get('type') == 'expl' or translation.get('t_type') == 'expl':
        # TODO: handle type
        # print('Skip t element: {}'.format(translation.get('type')))
        return

    if translation_lang is None:
        #Gi advarsel og ikke skriv ut om tg xml:lang ikke er samme som til språk i xml-fila sitt navn …
        raise UserWarning('No lang, translation')
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
            print(etree.tostring(translation, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                194, translation.tag, attr))

    for child in translation:
        if child.tag not in []:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(202, child.tag))

    try:
        l2wiki(translation.text, translation_lang, translation.get('pos').title(), outdir)
    except AttributeError:
        print('error in {}'.format(etree.tostring(translation, encoding='unicode')))



def handle_tg_xg(example_group, translation_lang, outdir):
    for attr in example_group.keys():
        if attr not in ['re']:
            print(etree.tostring(example_group, encoding='unicode'))
            raise SystemExit('line: {} tag: {} attr: {}'.format(
                211, example_group.tag, attr))

    for child in example_group:
        if child.tag not in ['x', 'xt', 're']:
            # ditch:
            print(etree.tostring(child, encoding='unicode'))
            raise SystemExit('line: {} tag: {} '.format(219, child.tag))


def handle_tg_re(restriction, translation_lang, outdir):
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


def handle_morph(morphology, translation_lang, outdir):
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


def main():
    outdir = datetime.datetime.now().isoformat()
    os.makedirs(outdir)

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
            if not xml_file.endswith('meta.xml') and not 'Der_' in xml_file:
                # TODO: handle Der_ files
                print(xml_file)
                dict2wiki(etree.parse(xml_file, parser=parser), outdir)
