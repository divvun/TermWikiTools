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

from lxml import etree


def expression2text(entry_lang: str, entry_xml: etree.Element) -> dict:
    """Turn an dictionary xml entry into wiki exportable dict.

    Args:
        entry_xml: An dictionary entry xml element.
        entry_lang: The language of the entry.

    Returns:
        A dict with a title and text element.
    """
    entry = {
        'title': '{}:{}'.format(entry_lang,
                                entry_xml.find('./lg/l').text)
    }

    entry['text'] = '\n'.join([
        '{}{}'.format('{', entry_xml.tag),
        '|pos={}'.format(entry_xml.find('./lg/l').get('pos')),
        '}',
        '\n'.join([
            mg2text(entry_lang, pair[0], pair[1])
            for pair in enumerate(entry_xml.iter('mg'), start=1)
        ])
    ])

    return entry


def mg2text(from_lang: str, number: int, meaning_xml: etree.Element) -> str:
    """Turn a meaning group element into a list wiki strings.

    Args:
        meaning_xml: A meaning group xml element.

    Returns:
        A meaning group converted to a list of strings
    """
    mg_id = 'mg_{0:08}'.format(number)
    return '\n'.join([
        '{}{}'.format('{', meaning_xml.tag),
        '|id={}'.format(mg_id),
        '}',
        '\n'.join([tg2text(mg_id, from_lang, tg_number, tg)
                   for tg_number, tg in enumerate(meaning_xml.iter('tg'),
                                                  start=1)])
        ])


def tg2text(parent, from_lang: str, number: int,
            translation_xml: etree.Element) -> str:
    """Turn a translation group element into a list of wiki strings.

    Args:
        translation_xml: An translation group xml element.

    Returns:
        A translation group converted to a string.
    """
    tg_lang = translation_xml.get('{http://www.w3.org/XML/1998/namespace}lang')
    tg_id = 'tg_{0:08}'.format(number)
    return '\n'.join([
        '{}{}'.format('{', translation_xml.tag),
        '|lang={}'.format(tg_lang), '|pos={}'.format(
            translation_xml.find('./t').get('pos')), '|lemmas={}'.format(
                ';'.join([lemma.text for lemma in translation_xml.iter('t')])),
        '|id={}'.format(tg_id), '|parent={}'.format(parent), '}',
        '\n'.join([
            xg2text(tg_id, from_lang,
                    tg_lang, xg)
            for xg in translation_xml.iter('xg')
            ])
        ])


def xg2text(parent, from_lang: str, to_lang: str,
            example_xml: etree.Element) -> str:
    """Turn an explanation group element into a list of wiki strings.

    Args:
        example_xml: An example group xml element.

    Returns:
        An example group turned into a string.
    """
    return '\n'.join([
        '{}{}'.format('{', example_xml.tag), '|parent={}'.format(parent),
        '|{}={}'.format(from_lang,
                        example_xml.find('./x').text), '|{}={}'.format(
                            to_lang,
                            example_xml.find('./xt').text), '}'
    ])
