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
from dataclasses import asdict

import click

from termwikitools import bot, read_termwiki
from termwikitools.handler_common import LANGUAGES

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
def make_search_index() -> dict[str, list[read_termwiki.TermWikiPage]]:
    """Make a search index."""
    dump_handler = bot.DumpHandler()
    search_index = collections.defaultdict(list)
    for _, termwiki_page in dump_handler.termwiki_pages:
        for related_expression in termwiki_page.related_expressions:
            search_index[related_expression.expression].append(termwiki_page)
    return search_index


def find_matching_term_articles(
    search_index: dict[str, list[read_termwiki.TermWikiPage]],
    json_concept: dict,
    collection: str | None,
) -> list[read_termwiki.TermWikiPage]:
    """Find matching term articles to the json_concept.

    Args:
        search_index: The search index.
        json_concept: The json concept.

    Returns:
        A list of tuples with search term, term language and list of matching
        termwiki pages.
    """
    matching_term_articles = (
        term_article
        for search_term in [
            related_expression["expression"]
            for related_expression in json_concept["related_expressions"]
        ]
        if search_term in search_index
        for term_article in search_index[search_term]
    )

    if collection is None:
        return list(matching_term_articles)

    return [
        term_article
        for term_article in matching_term_articles
        if term_article.concept is not None
        and term_article.concept.collection is not None
        and collection in term_article.concept.collection
    ]


@click.group()
def main():
    pass


@main.command()
@click.option("--outfile", default="termwiki.tsv", help="Output file")
@click.argument("search_language", type=click.Choice(list(LANGUAGES.keys())), nargs=1)
@click.argument("searches", nargs=-1)
def search(search_language, searches, outfile):
    """Search dump."""
    termwiki_language = LANGUAGES[search_language]
    search_index = make_search_index()

    old_to_new_langs = {v: k for k, v in LANGUAGES.items()}
    search_terms = sorted(
        {
            search.lower().strip().replace(")", "").replace(")", "").replace(":", "")
            for c_search in searches
            for search in c_search.split()
        }
    )
    results = [
        {
            language: (
                f'{", ".join(termwiki_page.get_terms(language))}'
                f" {termwiki_page.get_definition(language)}"
            ).strip()
            for termwiki_page in termwiki_pages
            for language in termwiki_page.get_languages()
        }
        for termwiki_pages in [
            search_index[search] for search in search_terms if search in search_index
        ]
    ]
    langs = sorted(
        {
            lang
            for result in results
            for lang in result.keys()
            if lang != termwiki_language
        }
    )
    langs.insert(0, termwiki_language)

    click.echo(f"Writing to {outfile}")
    with click.open_file(outfile, "w") as f:
        print("\t".join(old_to_new_langs.get(old) for old in langs), file=f)
        print(
            "\n".join(
                [
                    "\t".join([result.get(lang, "") for lang in langs])
                    for result in results
                ]
            ),
            file=f,
        )


def merge_concepts(import_concept, dump_concept):
    """Merge two concepts."""
    merge_collections(import_concept, dump_concept)
    merge_concept_infos(import_concept, dump_concept)

    chosen_pos = define_partofspeech(import_concept, dump_concept)

    set_dump_pos(dump_concept, chosen_pos)

    merge_related_expressions(import_concept, dump_concept, chosen_pos)

    return asdict(
        read_termwiki.cleanup_termwiki_page(
            read_termwiki.TERMWIKI_PAGE_SCHEMA.load(dump_concept)
        )
    )


def merge_related_expressions(import_concept, dump_concept, chosen_pos):
    dump_expressions = [
        related_expression["expression"]
        for related_expression in dump_concept["related_expressions"]
    ]
    for related_expression in import_concept["related_expressions"]:
        if related_expression["expression"] not in dump_expressions:
            if chosen_pos is not None:
                related_expression["pos"] = chosen_pos
            if " " in related_expression["expression"]:
                related_expression["pos"] = "MWE"
            dump_concept["related_expressions"].append(related_expression)


def set_dump_pos(dump_concept, chosen_pos):
    for related_expression in dump_concept["related_expressions"]:
        if chosen_pos is not None:
            related_expression["pos"] = chosen_pos
        if " " in related_expression["expression"]:
            related_expression["pos"] = "MWE"


def merge_concept_infos(import_concept, dump_concept):
    if import_concept.get("concept_infos"):
        concept_infos_languages = [
            concept_info["language"]
            for concept_info in dump_concept.get("concept_infos", [])
        ]

        for concept_info in import_concept["concept_infos"]:
            if concept_info["language"] not in concept_infos_languages:
                dump_concept["concept_infos"].append(concept_info)


def merge_collections(import_concept, dump_concept):
    if dump_concept["concept"].get("collection") is None:
        dump_concept["concept"]["collection"] = []
    dump_concept["concept"]["collection"].extend(
        import_concept["concept"]["collection"]
    )


def define_partofspeech(import_concept, dump_concept):
    poses = list(
        {
            related_expression["pos"]
            for related_expression in dump_concept["related_expressions"]
            + import_concept["related_expressions"]
            if related_expression["pos"] is not None
            and related_expression["pos"] != "MWE"
        }
    )
    if len(poses) == 1:
        chosen_pos = poses[0]
    elif len(poses) > 1:
        for pos in poses:
            for related_expression in (
                import_concept["related_expressions"]
                + dump_concept["related_expressions"]
            ):
                if related_expression["pos"] == pos:
                    print(
                        f"{related_expression["pos"]}: "
                        f"{related_expression["expression"]}"
                    )
        prompt = (
            "Choose pos: \n"
            + "\n".join([f"{i}: {pos}" for i, pos in enumerate(poses)])
            + "\n"
        )
        choice = int(input(prompt))
        chosen_pos = poses[choice]
    else:
        chosen_pos = None
    return chosen_pos


def choose_page_title(
    matching_term_articles: set[read_termwiki.TermWikiPage],
) -> str | None:
    article_titles = list(
        {term_article.title for term_article in matching_term_articles}
    )

    if len(article_titles) == 1:
        title = list(article_titles)[0]
    else:
        prompt = (
            "Choose title: \n"
            + "\n".join([f"{i}: {title}" for i, title in enumerate(article_titles)])
            + "\n"
        )
        choice = int(input(prompt))
        try:
            title = article_titles[choice]
        except IndexError:
            title = None
    return title


@main.command()
@click.option(
    "--collection",
    is_flag=True,
    help="Filter by the collection found in the json file",
)
@click.argument("infile", type=click.Path(exists=True))
def merge(collection, infile):
    """Merge content of json file with termwiki articles."""
    search_index = make_search_index()

    with click.open_file(infile, "r") as f:
        my_json = json.load(f)

        this_collection = my_json["collection"]["name"] if collection else None

        new_concepts = []
        for json_concept in my_json["concepts"]:
            matching_term_articles = find_matching_term_articles(
                search_index, json_concept, this_collection
            )
            if not matching_term_articles:
                new_concepts.append(json_concept)
                continue

            title = choose_page_title(matching_term_articles)

            if title is None:
                new_concepts.append(json_concept)
            else:
                for matching_term_article in matching_term_articles:
                    if matching_term_article.title == title:
                        new_concepts.append(
                            merge_concepts(json_concept, asdict(matching_term_article))
                        )
                        break

        my_json["concepts"] = new_concepts
        with click.open_file(infile, "w") as f2:
            f2.write(json.dumps(my_json, indent=2, ensure_ascii=False))
