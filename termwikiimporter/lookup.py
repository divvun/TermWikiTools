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
"""Lookup which articles belongs to an expression."""
from collections import defaultdict

from termwikiimporter import bot

DUMPHANDLER = bot.DumpHandler()
LOOKUP_DICT = defaultdict(set)

for title, concept in DUMPHANDLER.concepts:
    for expression in concept.related_expressions:
        LOOKUP_DICT[(expression['expression'],
                     expression['language'])].add(title)


def lookup(expr, language):
    """Check if an expression of the given language exists in termwiki."""
    return LOOKUP_DICT.get((expr, language), set())
