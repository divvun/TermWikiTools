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
#   Copyright © 2019 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Set part of speech if possible."""
import os
import re

import hfst

from termwikiimporter import dicts2wiki


def parse_dicts():
    """Parse dicts to look for part of speech."""
    expressiondict = {}
    for dictxml, _ in dicts2wiki.valid_xmldict():
        current_lang = dictxml.getroot().get('id')[:3]
        if not expressiondict.get(current_lang):
            expressiondict[current_lang] = {}
        for lemma_element in dictxml.iter('l'):
            pos = lemma_element.get('pos')
            if not expressiondict[current_lang].get(pos):
                expressiondict[current_lang][pos] = set()
            expressiondict[current_lang][pos].add(lemma_element.text.strip())

    return expressiondict


def get_analyser(lang):
    """Make a hfst analyser."""
    path = f'/usr/share/giella/{lang}/analyser-gt-desc.hfstol'
    if os.path.isfile(path):
        return hfst.HfstInputStream(path).read()
    else:
        raise SystemExit(f'{path} does not exist')


def has_good_analysis(analysis, language):
    """Check if the analysis string has a valid part of speech."""
    if language != 'nob' and (analysis.endswith('+N+Sg+Nom')
                              or analysis.endswith('+N+Pl+Nom')
                              or analysis.endswith('+N+NomAg+Sg+Nom')
                              or analysis.endswith('+V+Der/minen+Sg+Nom')):
        return 'N'
    elif language == 'nob' and analysis.endswith('+V+Ing'):
        return 'N'
    elif analysis.endswith('+V+Inf'):
        return 'V'
    elif analysis.endswith('+Adv'):
        return 'Adv'
    elif analysis.endswith('A+Sg+Nom') or analysis.endswith('A+Attr'):
        return 'A'
    elif language == 'fin' and analysis.endswith('+V+Act+InfA+Sg+Lat'):
        return 'V'
    else:
        parts = analysis.split('+')
        if len(parts) > 4 and parts[-1] == 'Indef' and parts[
                -2] == 'Sg' and parts[-4] == 'N':
            return 'N'

    return None


def remove_compound_marks(analysises):
    """Remove compound marks from all analysises."""
    no_nynorsk = [
        analysis for analysis in analysises if 'Nynorsk' not in analysis
    ]
    no_cmp = list({analysis for analysis in no_nynorsk if '#' not in analysis})
    if no_cmp:
        return no_cmp

    return list({CMPS.sub('', analysis) for analysis in no_nynorsk})


def remove_acc_and_gen(no_cmps):
    """Fjern to typer analyser for å gjøre det enklere og finne pos."""
    no_acc_gens = [
        no_cmp for no_cmp in no_cmps
        if not no_cmp.endswith(('+Sg+Acc', '+Sg+Gen'))
    ]
    if not no_acc_gens:
        return no_cmps

    if all([no_acc_gen.endswith('+Sg+Nom') for no_acc_gen in no_acc_gens]):
        return [no_acc_gens[0]]

    return no_acc_gens


def set_pos(expression):
    """Set pos if possible."""
    if expression.get('language') and expression.get('pos') is None:
        this_lang = LANG2LANG[expression['language']]
        this_exp = expression['expression']

        if this_lang in EXP:
            pos_from_dict = list({
                pos
                for pos in EXP[this_lang] if this_exp in EXP[this_lang][pos]
            })
            if len(pos_from_dict) == 1:
                return pos_from_dict[0]

        if this_lang in ANALYSERS:
            analysis = ANALYSERS[this_lang].lookup(this_exp)
            if analysis:
                reduced = remove_acc_and_gen(
                    remove_compound_marks(
                        [ATTS.sub('', pair[0]) for pair in analysis]))

                if reduced is None:
                    raise SystemExit('Found None')

                if len(reduced) == 1:
                    found_pos = has_good_analysis(reduced[0], this_lang)
                    if found_pos is not None:
                        return found_pos

                if len(reduced) > 1:
                    if [
                            analysis for analysis in reduced
                            if analysis.endswith('+N+Sg+Gen+Allegro')
                    ]:
                        return 'N'

                    if [
                            analysis for analysis in reduced
                            if analysis.endswith('+Der/NomAg+N+Sg+Nom')
                    ]:
                        return 'N'

                    if [
                            analysis for analysis in reduced
                            if analysis.endswith('+Der/NomAct+N+Sg+Nom')
                    ]:
                        return 'N'

    return None


LANG2LANG = {
    'nb': 'nob',
    'fi': 'fin',
    'smn': 'smn',
    'se': 'sme',
    'sma': 'sma',
    'smj': 'smj',
    'en': 'eng',
    'sms': 'sms',
    'sv': 'swe',
    'nn': 'nno',
    'lat': 'lat'
}

ATTS = re.compile(r'@[^@]+@')
CMPS = re.compile(r'\+[^#]+#')
ANALYSERS = {
    lang: get_analyser(lang)
    for lang in ['fin', 'nob', 'sma', 'sme', 'smj', 'smn', 'sms']
}
EXP = parse_dicts()
