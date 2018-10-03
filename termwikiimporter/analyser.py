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
"""Module to analyse lemmas sent to it."""
import os

from corpustools import util

WIKI_TO_FST = {
    'se': 'sme',
    'fi': 'fin',
    'nb': 'nob',
    'nn': 'nob',
}

RUNNER = util.ExternalCommandRunner()


COMMAND_TEMPLATE = 'hfst-lookup --quiet {}'.format(
    os.path.join(
        os.getenv('GTHOME'), 'langs/{}/src/analyser-gt-norm.hfstol'))


def is_known(language, lemma):
    """Check if the given lemma in the given language is known."""
    if language in WIKI_TO_FST:
        language = WIKI_TO_FST[language]
    command = COMMAND_TEMPLATE.format(language).split()
    RUNNER.run(command, to_stdin=bytes(lemma, encoding='utf8'))
    return b'?' not in RUNNER.stdout


def analysis(language, lemma):
    """Check if the given lemma in the given language is known."""
    if language in WIKI_TO_FST:
        language = WIKI_TO_FST[language]
    command = COMMAND_TEMPLATE.format(language).split()
    RUNNER.run(command, to_stdin=bytes(lemma, encoding='utf8'))
    return RUNNER.stdout.decode('utf8')
