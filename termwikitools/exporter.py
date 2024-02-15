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
#   Copyright © 2016-2024 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Export content of files to the termwiki."""

import argparse
import json
import time

from termwikitools import bot
from termwikitools.read_termwiki import (
    COLLECTION_SCHEMA,
    TERMWIKI_PAGE_SCHEMA,
)


def parse_options():
    """Parse commandline options."""
    parser = argparse.ArgumentParser(
        description="Write .result.json files to the termwiki."
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing termwiki pages.",
    )
    parser.add_argument(
        "wikifiles",
        nargs="+",
        help="One or more files containing output from the termimport.",
    )

    args = parser.parse_args()

    return args


def write_to_termwiki():
    """Write the content of the given files to the termwiki."""
    args = parse_options()

    # Initialize Site object
    print("Logging in …")
    sitehandler = bot.SiteHandler()
    site = sitehandler.get_site()

    for wikifile in args.wikifiles:
        export_json = json.load(open(wikifile))

        collection = COLLECTION_SCHEMA.load(export_json["collection"])
        collection_page = site.Pages[collection.name]
        collection_text = collection_page.text()
        if not collection_text:
            print(f"Saving {collection.name}")
            collection_page.save(collection.to_termwiki(), summary="New import")
        for concept in export_json["concepts"]:
            termwikipage = TERMWIKI_PAGE_SCHEMA.load(concept)
            site_page = site.Pages[termwikipage.title]
            site_text = site_page.text()
            if not site_text:
                print(f"Saving {termwikipage.title}")
                site_page.save(termwikipage.to_termwiki(), summary="New import")
            elif args.force and site.text != termwikipage.to_termwiki():
                print(f"Overwriting {termwikipage.title}")
                site_page.save(
                    termwikipage.to_termwiki(), summary="Overwrite with new content"
                )
            else:
                print(f"{termwikipage.title} already exists")
            time.sleep(0.5)
