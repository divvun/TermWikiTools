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
"""Make SMW pages from lexc files.

The formats should be:

The format of a Contlex page
{{Continuation lexicon
|Contlex name=JOHTOLAT
|Language=se
|Pos=N
}}

The name of Contlex page:
Contlex:se_N_JOHTOLAT

The format of a Stem page:
{{Stem
|Lemma=johtolat
|Contlex=se N JOHTOLAT
|Comment1=<Freetext part in lexc line>
|Comment2=<The real comment>
}}

The name of a Stem page:
Stem:johtolat se N JOHTOLAT
"""

import glob
import io
import os
import re
import sys
from collections import defaultdict

from termwikiimporter import analyser

WANTED_LEXICONS = {
    'sme': {
        'adpositions': ['Adposition'],
        'adjectives':
        ['ALIT', 'Eahpe_Adjective', 'AdjectivePx', 'AdjectiveNoPx'],
        'adverbs': ['Adverb'],
        'conjunctions': ['CleanConjunction'],
        'interjections': ['Interjection'],
        'nouns':
        ['HyphNouns', 'Eahpe_Noun', 'NounNoPx', 'NounPxKin', 'NounPx'],
        'particles': ['Particles'],
        'subjunctions': ['ConfuseConjunction', 'CleanSubjunction'],
        'verbs': ['Eahpe_Verb', 'Verb'],
    }
}

LEXC_LINE_RE = re.compile(r'''
    (?P<contlex>\S+)            #  any nonspace
    (?P<translation>\s+".*")?   #  optional translation, might be empty
    \s*;\s*                     #  skip space and semicolon
    (?P<comment>!.*)?           #  followed by an optional comment
    $
''', re.VERBOSE | re.UNICODE)

LEXC_CONTENT_RE = re.compile(r'''
    (?P<exclam>^\s*!\s*)?          #  optional comment
    (?P<content>(<.+>)|(.+))?      #  optional content
''', re.VERBOSE | re.UNICODE)


def parse_line(old_match: dict) -> defaultdict:
    """Parse a lexc line.

    Arguments:
        old_match:

    Returns:
        dict of unicode: The entries inside the lexc line expressed as
            a dict
    """
    line_dict = defaultdict(str)

    if old_match.get('exclam'):
        line_dict[u'exclam'] = u'!'

    line_dict[u'contlex'] = old_match.get(u'contlex')
    if old_match.get(u'translation'):
        line_dict[u'translation'] = old_match.get(
            u'translation').strip().replace(u'%¥', u'% ')

    if old_match.get(u'comment'):
        line_dict[u'comment'] = old_match.get(u'comment').strip().replace(
            u'%¥', u'% ')

    line = old_match.get('content')
    if line:
        line = line.replace(u'%¥', u'% ')
        if line.startswith(u'<') and line.endswith(u'>'):
            line_dict[u'upper'] = line
        else:
            lexc_line_match = line.find(u":")

            if lexc_line_match != -1:
                line_dict[u'upper'] = line[:lexc_line_match].strip()
                line_dict[u'divisor'] = u':'
                line_dict[u'lower'] = line[lexc_line_match + 1:].strip()
                if line_dict[u'lower'].endswith('%'):
                    line_dict[u'lower'] = line_dict[u'lower'] + u' '
            else:
                if line.strip():
                    line_dict[u'upper'] = line.strip()

    return line_dict


def handle_line(line: str) -> dict:
    """Parse a valid line.

    Args:
        line: a lexc line
    """
    line = line.replace(u'% ', u'%¥')
    lexc_line_match = LEXC_LINE_RE.search(line)
    if lexc_line_match:
        content = lexc_line_match.groupdict()
        content.update(
            LEXC_CONTENT_RE.match(LEXC_LINE_RE.sub('', line)).groupdict())
        return parse_line(content)

    return {}


def print_stem(line: str, lang: str, stemfile: str) -> None:
    giella2termwiki = {
        'fin': 'fi',
        'nob': 'nb',
        'sma': 'sma',
        'sme': 'se',
        'smj': 'smj',
        'smn': 'smn',
    }

    file2pos = {
        'adjectives': 'A',
        'adpositions': 'Adp',
        'adverbs': 'Adv',
        'conjunctions': 'Cc',
        'interjections': 'Interj',
        'nouns': 'N',
        'particles': 'Pcle',
        'subjunctions': 'CS',
        'verbs': 'V'
    }

    line_dict = handle_line(line)
    if line_dict and not line_dict['exclam']:
        upper = line_dict['upper'].split('+')[0].replace('%', '')
        if analyser.is_known(lang, upper):
            stem = ['{{Stem']
            stem.append('|Lemma={}'.format(upper))
            stem.append('|Contlex={} {} {}'.format(giella2termwiki[lang],
                                                   file2pos[stemfile],
                                                   line_dict['contlex']))
            if line_dict['translation']:
                stem.append('|Comment1={}'.format(line_dict['translation']))
            if line_dict['comment']:
                stem.append('|Comment2={}'.format(line_dict['comment']))
            stem.append('}}')
            print('\n'.join(stem))


def handle_file(lang, stemfile):
    filetemplate = os.path.join(
        os.getenv('GTHOME'), 'langs/{}/src/morphology/stems/{}.lexc')

    with io.open(filetemplate.format(lang, stemfile)) as lexc:
        SKIP = True

        for lexc_line in lexc:
            if lexc_line.startswith('LEXICON'):
                parts = lexc_line.split()
                SKIP = parts[1] not in WANTED_LEXICONS[lang][stemfile]
                continue

            if not SKIP and '+Err' not in lexc_line:
                print_stem(lexc_line.rstrip(), lang, stemfile)


def main():
    for lang in WANTED_LEXICONS:
        for stemfile in WANTED_LEXICONS[lang]:
            handle_file(lang, stemfile)


if __name__ == '__main__':
    main()
