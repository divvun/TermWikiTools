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
#   Copyright © 2016-2023 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Bot to fix syntax blunders in termwiki articles."""

import time

import click
import requests

from termwikitools.dumphandler import NAMESPACES, DumpHandler
from termwikitools.handler_common import LANGUAGES
from termwikitools.sitehandler import SiteHandler


def list_recent_changes(amount):
    namespaces = "|".join(
        str(i)
        for i in [
            1102,
            1202,
            1210,
            1218,
            1226,
            1234,
            1242,
            1250,
            1258,
            1266,
            1274,
            1282,
            1290,
            1298,
            1306,
            1314,
            1322,
            1330,
            1338,
            1346,
            1354,
            1362,
            1364,
            1366,
            1368,
            1370,
            1373,
            1382,
            1384,
            1386,
        ]
    )

    session = requests.Session()

    url = "https://satni.uit.no/termwiki/api.php"

    params = {
        "format": "json",
        "rcprop": "title",
        "list": "recentchanges",
        "action": "query",
        "rcnamespace": namespaces,
        "rclimit": amount,
        "rcexcludeuser": "SDTermImporter",
    }

    request = session.get(url=url, params=params)
    data = request.json()

    recentchanges = data["query"]["recentchanges"]

    return sorted({rc["title"] for rc in recentchanges})


@click.group()
def main():
    """Fix site or extract data from local copy of TermWiki."""
    pass


@main.group()
def dump():
    """Extract data from local copy of TermWiki."""
    pass


@dump.command()
def json():
    """Dump the TermWiki database to json."""
    dumphandler = DumpHandler()
    dumphandler.dump2json()


@dump.command()
@click.argument(
    "language",
    type=click.Choice(list(LANGUAGES.keys())),
)
@click.option(
    "--only-sanctioned",
    is_flag=True,
    help="Sanctioned status for GG.",
)
def missing(language, only_sanctioned):
    """Print missing terms for a language."""
    dumphandler = DumpHandler()
    dumphandler.print_missing(
        language=language, only_sanctioned="True" if only_sanctioned else "False"
    )


@dump.command()
def collection():
    """Find collections in the dump."""
    dumphandler = DumpHandler()
    dumphandler.find_collections()


@dump.command()
@click.argument("language", type=click.Choice(list(LANGUAGES.keys())))
@click.option("--only-sanctioned", is_flag=True, help="Sanctioned status for GG.")
def invalid(language, only_sanctioned):
    """Print invalid characters for a language."""
    dumphandler = DumpHandler()
    print(language, only_sanctioned)
    dumphandler.print_invalid_chars(
        language=LANGUAGES[language],
        only_sanctioned="True" if only_sanctioned else "False",
    )


@dump.command()
@click.argument("language", type=click.Choice(list(LANGUAGES.keys())))
def number_of_terms(language):
    """Sum the number of terms for a language."""
    dumphandler = DumpHandler()
    dumphandler.sum_terms(language=LANGUAGES[language])


@dump.command()
@click.argument("language", type=click.Choice(list(LANGUAGES.keys())))
def terms_of_lang(language):
    """Sum the number of terms for a language."""
    dumphandler = DumpHandler()
    dumphandler.terms_of_lang(language=LANGUAGES[language])


@dump.command()
@click.argument(
    "languages", nargs=-1, type=click.Choice(list(LANGUAGES.keys())), required=True
)
def statistics(languages):
    """Print statistics for one or more languages."""
    dumphandler = DumpHandler()
    for language in languages:
        dumphandler.statistics(language=LANGUAGES[language])


@dump.command()
def sort():
    """Sort the dump."""
    dumphandler = DumpHandler()
    dumphandler.sort_dump()


@dump.command()
@click.argument("source", type=click.Choice(list(LANGUAGES.keys())))
@click.argument("target", type=click.Choice(list(LANGUAGES.keys())))
@click.option(
    "--category",
    type=click.Choice([namespace.replace(" ", "_") for namespace in NAMESPACES]),
    help="Choose category",
)
def pairs(source, target, category):
    """Print expression pairs for two languages."""
    dumphandler = DumpHandler()
    dumphandler.print_expression_pairs(
        lang1=LANGUAGES[source],
        lang2=LANGUAGES[target],
        category=category.replace("_", " ") if category is not None else category,
    )


@main.group()
def site():
    pass


@site.command()
def fix():
    """Fix all Concept pages on the TermWiki."""
    site_handler = SiteHandler()
    site_handler.fix()


@site.command()
def rev():
    site_handler = SiteHandler()
    site_handler.fix_revisions()


@site.command()
def revert():
    site_handler = SiteHandler()
    site_handler.revert()


@site.command()
def query():
    site_handler = SiteHandler()
    site_handler.add_extra_collection()


@site.command()
def fix_expression_pages():
    """Fix expression pages."""
    site_handler = SiteHandler()
    site_handler.fix_expression_pages()


@site.command()
def delete_redirects():
    """Delete redirects on the TermWiki, they are not needed."""
    site_handler = SiteHandler()
    site_handler.delete_redirects()


@site.command()
def add_id():
    """Add permanent id to Concept pages on the TermWiki"""
    site_handler = SiteHandler()
    site_handler.add_id()


@site.command()
def improve_pagenames():
    """Improve page names on the TermWiki"""
    site_handler = SiteHandler()
    site_handler.improve_pagenames()


@site.command()
@click.argument("substring")
def delete_pages(substring):
    """Delete pages containing the substring from the TermWiki."""
    site_handler = SiteHandler()
    site_handler.delete_pages(substring)


@site.command()
@click.option("--amount", default=10, help="The number of recent changes to fix")
def fixrecent(amount):
    """Fix recently changed Concept pages on the TermWiki."""
    site_handler = SiteHandler()
    for title in list_recent_changes(amount):
        page = site_handler.site.pages[title]
        site_handler.fix_termwiki_page(page)
        time.sleep(0.2)
