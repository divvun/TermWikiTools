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
#   Copyright © 2024 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Search dump."""

import collections
import json

import click

from termwikitools import bot

# For hver av artiklene i inputfila, så vil jeg:
# 1. Sjekke om termene i artikkelen finnes i søkeindeksen
# 2. Hvis det finnes ett treff, vis hvilken info fra artikkelen i inputfila
#    som legges til treffartikkelen.


# To modi: For hver av artiklene i inputfila, så vil jeg:
# 1. Sjekke om termene i artikkelen finnes i søkeindeksen
# modus 1: skriv ut titlene på treffartiklene
# modus 2: for artkikler med treff, 1. velg hvilken tittel man vil
# flette inputartikkelen i, 2. erstatt den valgte inputartikkelen med
# den flettede artikkelen.
def make_search_index():
    """Make a search index."""
    dump_handler = bot.DumpHandler()
    search_index = collections.defaultdict(list)
    for _, termwiki_page in dump_handler.termwiki_pages:
        for related_expression in termwiki_page.related_expressions:
            search_index[related_expression.expression].append(termwiki_page)
    return search_index


def get_searches(infile):
    with click.open_file(infile, "r") as f:
        my_json = json.load(f)
        for concept in my_json["concepts"]:
            for related_expression in concept["related_expressions"]:
                yield related_expression["expression"], related_expression[
                    "language"
                ], concept["title"]


@click.command()
@click.option("--infile", help="Input file")
# @click.option("--outfile", default="termwiki.tsv", help="Output file")
# @click.argument("search_language", type=click.Choice(list(LANGUAGES.keys())), nargs=1)
# @click.argument("searches", nargs=-1)
def main(infile):
    """Search dump."""
    # termwiki_language = LANGUAGES[search_language]
    search_index = make_search_index()

    search_terms = get_searches(infile)
    # old_to_new_langs = {v: k for k, v in LANGUAGES.items()}
    # search_terms = sorted(
    #     {
    #         search.lower().strip().replace(")", "").replace(")", "").replace(":", "")
    #         for search in searches
    #         # for search in c_search.split()
    #     }
    # )
    found_pages = [
        (search, search_index[search[0]])
        for search in search_terms
        if search[0] in search_index
    ]

    for result in found_pages:
        print(result[0])
        print("\n".join({page.title for page in result[1]}))
        print()
    print(f"Found {len(set({result[0][2] for result in found_pages}))} pages")
    # results = [
    #     {
    #         language: (
    #             f'{", ".join(termwiki_page.get_terms(language))}'
    #             f" {termwiki_page.get_definition(language)}"
    #         ).strip()
    #         for termwiki_page in termwiki_pages
    #         for language in termwiki_page.get_languages()
    #     }
    #     for termwiki_pages in [
    #         search_index[search] for search in search_terms if search in search_index
    #     ]
    # ]
    # langs = sorted(
    #     {
    #         lang
    #         for result in results
    #         for lang in result.keys()
    #         if lang != termwiki_language
    #     }
    # )
    # langs.insert(0, termwiki_language)

    # click.echo(f"Writing to {outfile}")
    # with click.open_file(outfile, "w") as f:
    #     print("\t".join(old_to_new_langs.get(old) for old in langs), file=f)
    #     print(
    #         "\n".join(
    #             [
    #                 "\t".join([result.get(lang, "") for lang in langs])
    #                 for result in results
    #             ]
    #         ),
    #         file=f,
    #     )
