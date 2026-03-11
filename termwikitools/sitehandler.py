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
import collections
import importlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Iterator

import marshmallow
import yaml

from termwikitools import read_termwiki
from termwikitools.dumphandler import DumpHandler
from termwikitools.handler_common import NAMESPACES

mwclient: Any = importlib.import_module("mwclient")


def update_svn() -> None:
    command = f"svn up {os.getenv('GTHOME')}/words/terms/termwiki"
    ret_value = subprocess.run(command.split(), capture_output=True, check=False)
    if ret_value.returncode != 0:
        raise SystemExit(f"Error: {ret_value.stderr.decode()}")
    print(f"Return value: {ret_value.stdout.decode()}")


def read_time_stamp() -> datetime:
    # read time stamp
    timestamp = (
        Path(f"{os.getenv('GTHOME')}/words/terms/termwiki/timestamp")
        .read_text()
        .strip()
    )
    return datetime.fromisoformat(timestamp.rstrip("Z"))


def write_time_stamp(timestamp: datetime) -> None:
    # write time stamp

    Path(f"{os.getenv('GTHOME')}/words/terms/termwiki/timestamp").write_text(
        timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    command = [
        "svn",
        "commit",
        "-m",
        "Update timestamp",
        f"{os.getenv('GTHOME')}/words/terms/termwiki/timestamp",
    ]
    ret_value = subprocess.run(command, capture_output=True, check=False)

    if ret_value.returncode != 0:
        raise SystemExit(f"Error: {ret_value.stderr.decode()}")
    print(f"Return value: {ret_value.stdout.decode()}")


class SiteHandler:
    """Class that involves using the TermWiki dump.

    Attributes:
        site (mwclient.Site): the TermWiki site
    """

    def __init__(self):
        """Initialise the SiteHandler class."""
        self.site = self.get_site()

    @staticmethod
    def get_site():
        """Get a mwclient site object.

        Returns:
            mwclient.Site
        """
        home = os.getenv("HOME")
        if home is None:
            raise SystemExit("Error: The environment value HOME is not set")

        config_file = os.path.join(home, ".config", "term_config.yaml")
        with open(config_file) as config_stream:
            config = yaml.load(config_stream, Loader=yaml.FullLoader)
            site = mwclient.Site("satni.uit.no", path="/termwiki/")
            site.login(config["username"], config["password"])

            print("Logging in to query …")

            return site

    def content_elements(self, verbose: bool = False) -> Generator[Any, None, None]:
        """Get the concept pages in the TermWiki.

        Yields:
            mwclient.Page
        """
        for category in self.site.allcategories():
            if category.name.replace("Kategoriija:", "") in NAMESPACES:
                if verbose:
                    print(category.name)
                for page in category:
                    if self.is_concept_tag(page.text()):
                        yield page

    @staticmethod
    def is_concept_tag(content: str) -> bool:
        """Check if content is a TermWiki Concept page.

        Args:
            content (str): content of a TermWiki page.

        Returns:
            bool
        """
        return "{{Concept" in content

    @staticmethod
    def save_page(page: Any, content: str, summary: str) -> None:
        """Save a given TermWiki page.

        Args:
            page: The page to be saved.
            content (str): The new content to be saved.
            summary (str): The commit message.

        Raises:
            mwclient.errors.APIError: If the page cannot be saved.
        """
        try:
            page.save(content, summary=summary)
        except mwclient.errors.APIError as error:
            print(page.name, content, str(error), file=sys.stderr)

    def delete_redirects(self) -> None:
        dump = DumpHandler()
        root = dump.tree.getroot()
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        redirects = {
            redirect_xml.getparent().getparent()
            for redirect_xml in root.xpath('.//mw:text', namespaces=namespace)
            if redirect_xml.text and redirect_xml.text.startswith("#STIVREN")
        }
        print("Redirects pages", len(redirects))
        for redirect in redirects:
            title1 = redirect.find(".//mw:title", namespace)
            page = self.site.pages[title1.text]
            if page.redirect:
                page.delete(reason="Redirect page is not needed")
            else:
                print(f"\tis not redirect {title1.text}")

    def add_id(self) -> None:
        dump = DumpHandler()
        for title, content_elt, page_id in dump.content_elements:
            if content_elt is not None and content_elt.text:
                try:
                    dump_tw_page = read_termwiki.termwiki_page_to_dataclass(
                        title, iter(content_elt.text.replace("\xa0", " ").splitlines())
                    )
                    if (
                        dump_tw_page.concept is not None
                        and dump_tw_page.concept.page_id is None
                    ):
                        page = self.site.pages[title]
                        site_tw_page = read_termwiki.termwiki_page_to_dataclass(
                            title, iter(page.text().splitlines())
                        )
                        if site_tw_page.concept is not None:
                            site_tw_page.concept.page_id = page_id
                            print(f"Adding {page_id} to {title}")
                            page.save(site_tw_page.to_termwiki(), summary="Added id")
                except marshmallow.exceptions.ValidationError as error:
                    print(f"Error: {title}", error, file=sys.stderr)

    def make_related_expression_dict(
        self, dump: DumpHandler
    ) -> collections.defaultdict:
        related_expression_dict = collections.defaultdict(set)
        for _, concept in dump.termwiki_pages:
            for related_expression in concept.related_expressions:
                related_expression_dict[
                    f'Expression:{related_expression.expression.replace("&amp;", "&")}'
                ].add(related_expression.language)

        return related_expression_dict

    def make_dump_expression_dict(self, dump: DumpHandler) -> dict:
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        return {
            expression_xml.text.replace("&amp;", "&"): expression_xml.getparent()
            .xpath(".//mw:text", namespaces=namespace)[0]
            .text
            for expression_xml in dump.tree.getroot().xpath(
                './/mw:title', namespaces=namespace
            ) if expression_xml.text and expression_xml.text.startswith("Expression:")
        }

    def make_expression_pages(
        self,
        related_expression_dict: collections.defaultdict,
        dump_expression_dict: dict,
    ) -> None:
        for expression_title, languages in related_expression_dict.items():
            ideal_content = self.make_expression_content(languages)
            if ideal_content != dump_expression_dict.get(expression_title):
                # Avoid deleting pages we are about to recreate.
                dump_expression_dict[expression_title] = ideal_content
                self.fix_expression_page(expression_title, content=ideal_content)

    def delete_expression_pages(
        self,
        related_expression_dict: collections.defaultdict,
        dump_expression_dict: dict,
    ) -> None:
        related_expressions = set(related_expression_dict.keys())
        dump_expressions = set(dump_expression_dict.keys())

        for to_delete in dump_expressions - related_expressions:
            page = self.site.pages[to_delete]
            if page.exists:
                print(f"Removing {to_delete}")
                page.delete(reason="Is not found among related expressions")

    def fix_expression_pages(self) -> None:
        dump = DumpHandler()
        related_expression_dict = self.make_related_expression_dict(dump=dump)
        dump_expression_dict = self.make_dump_expression_dict(dump=dump)

        self.make_expression_pages(related_expression_dict, dump_expression_dict)
        self.delete_expression_pages(related_expression_dict, dump_expression_dict)

    def fix_expression_page(self, expression_title: str, content: str) -> None:
        try:
            page = self.site.pages[expression_title]

            if not page.exists:
                print("\tmaking", expression_title)
                self.save_page(
                    page, content=content, summary="Making new expression page"
                )
                time.sleep(0.2)

            if page.text() != content:
                print("\treally fixing", expression_title)
                self.save_page(page, content=content, summary="Fixing expression page")
                time.sleep(0.2)
        except mwclient.InvalidPageTitle as error:
            print(expression_title, error, file=sys.stderr)

    def make_expression_content(self, languages: set) -> str:
        strings = []
        for language in sorted(languages):
            strings.append("{{Expression")
            strings.append(f"|language={language}")
            strings.append("}}")
        content = "\n".join(strings)
        return content

    def delete_pages(self, part_of_title: str) -> None:
        dump = DumpHandler()
        root = dump.tree.getroot()
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        to_deletes = {
            title_xml.text
            for title_xml in root.xpath('.//mw:title', namespaces=namespace)
            if title_xml.text and title_xml.text.startswith(part_of_title)
        }
        print(f"{len(to_deletes)} pages to delete")
        for to_delete in to_deletes:
            page = self.site.pages[to_delete]
            if page.exists:
                try:
                    print(f"Removing {to_delete}")
                    page.delete(reason="Page is not needed anymore")
                    time.sleep(0.2)
                except mwclient.errors.APIError as error:
                    print(f"Error deleting {to_delete}: {error}", file=sys.stderr)

    def fix(self) -> None:
        """Make the bot fix all pages."""
        dump = DumpHandler()
        for title, dump_tw_page in dump.termwiki_pages:
            fixed_dump_tw_page = read_termwiki.cleanup_termwiki_page(dump_tw_page)
            if dump_tw_page != fixed_dump_tw_page:
                page = self.site.pages[title]
                self.fix_termwiki_page(page)

    def fix_termwiki_page(self, page: Any) -> None:
        """Make the bot fix a named page."""
        if page.exists:
            try:
                tw_page = read_termwiki.termwiki_page_to_dataclass(
                    page.name, iter(page.text().replace("\xa0", " ").splitlines())
                )
                fixed_tw_page = read_termwiki.cleanup_termwiki_page(tw_page)
                if fixed_tw_page != tw_page:
                    self.save_page(
                        page, fixed_tw_page.to_termwiki(), summary="Fixing content"
                    )
            except (KeyError, marshmallow.exceptions.ValidationError) as error:
                print(f"Error: {page.name}", error, file=sys.stderr)
                raise SystemExit() from None
        else:
            print(f"page {page.name} does not exist")

    def semantic_ask_results(
        self, query: str
    ) -> Generator[tuple[int, str], None, None]:
        for number, answer in enumerate(self.site.ask(query), start=1):
            print(answer)
            yield number, answer["fulltext"]

    def add_extra_collection(self) -> None:
        visited_pages = set()
        dumphandler = DumpHandler()
        for title, dump_tw_page in dumphandler.termwiki_pages:
            concept = dump_tw_page.concept
            if (
                concept is None
                or not concept.collection
                or "Collection:SD-terms" not in concept.collection
                or title in visited_pages
            ):
                continue

            visited_pages.add(title)
            page = self.site.pages[title]
            site_tw_page = read_termwiki.termwiki_page_to_dataclass(
                title, iter(page.text().splitlines())
            )
            if site_tw_page.concept is None:
                continue

            _, _, name = title.partition(":")
            if not name:
                continue

            extra_collection = f"Collection:SD-terms-{name[0].lower()}"
            collections = set(site_tw_page.concept.collection or [])
            if extra_collection not in collections:
                site_tw_page.concept.collection = sorted(
                    collections | {extra_collection}
                )
                print(f"\n\t{title} {extra_collection}\n")
                self.save_page(
                    page,
                    site_tw_page.to_termwiki(),
                    summary=f"Add collection: {extra_collection}",
                )

        print(len(visited_pages))

    def revert(self) -> None:
        """Automatically sanction expressions that have no collection.

        The theory is that concept pages with no collections mostly are from
        the risten.no import, and if there are no typos found in an expression
        they should be sanctioned.

        Args:
            language (str): the language to sanction
        """
        rollback_token = self.site.get_token("rollback")
        for page in self.content_elements():
            try:
                self.site.api(
                    "rollback",
                    title=page.name,
                    user="SDTermImporter",
                    summary="Use Stempage in Related expression",
                    markbot="1",
                    token=rollback_token,
                )
            except mwclient.errors.APIError as error:
                print(page.name, error)

    def remove_paren(self, old_title: str) -> str:
        """Remove parenthesis from termwiki page name.

        Args:
            old_title: a title containing a parenthesis

        Returns:
            A new unique page name without parenthesis
        """
        new_title = old_title[: old_title.find("(")].strip()
        my_title = new_title
        instance = 1
        page = self.site.pages[my_title]
        while page.exists:
            my_title = "{} {}".format(new_title, instance)
            page = self.site.pages[my_title]
            instance += 1

        return my_title

    def move_page(self, old_name: str, new_name: str) -> None:
        """Move a termwiki page from old to new name."""
        orig_page = self.site.pages[old_name]
        try:
            print(f"Moving from {orig_page.name} to {new_name}")
            orig_page.move(
                new_name, reason="Remove parenthesis from page names", no_redirect=True
            )
        except mwclient.errors.InvalidPageTitle as error:
            print(old_name, error, file=sys.stderr)

    @staticmethod
    def normalize_sms_title(title: str) -> str:
        """Replace characters that are invalid in sms page names."""
        return title.translate(
            str.maketrans(
                "\u2019\u0027\u2032\u00b4\u0301",
                "\u02bc\u02bc\u02b9\u02b9\u02b9",
            )
        )

    @staticmethod
    def parse_revision_timestamp(revision: dict[str, Any]) -> datetime | None:
        timestamp = revision.get("timestamp")
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return None

    def fix_revisions(self) -> None:
        """Restore selected dump pages when only importer accounts touched them."""
        start_time = datetime.strptime("15 Feb 19", "%d %b %y").replace(
            tzinfo=timezone.utc
        )

        dumphandler = DumpHandler()
        for title, dump_tw_page in dumphandler.termwiki_pages:
            concept = dump_tw_page.concept
            if (
                concept is None
                or not concept.collection
                or "Collection:JustermTana" not in concept.collection
            ):
                continue

            page = self.site.pages[title]
            users = {
                revision["user"]
                for revision in page.revisions()
                if revision.get("user")
                and (timestamp := self.parse_revision_timestamp(revision)) is not None
                and timestamp > start_time
                and "mporter" not in revision["user"]
            }
            if users:
                print(title, users)
            else:
                print(f"Saving {title}")
                self.save_page(
                    page,
                    dump_tw_page.to_termwiki(),
                    summary="Saved from backup",
                )

    def improve_pagenames(self) -> None:
        """Remove characters that break eXist search from page names."""
        for page in self.content_elements():
            try:
                my_title = self.normalize_sms_title(
                    self.remove_paren(page.name) if "(" in page.name else page.name
                )
                if page.name != my_title:
                    self.move_page(page.name, my_title)
            except mwclient.errors.InvalidPageTitle:
                print(f"Failed on {page.name}")

    def get_valid_site_termwiki_pages(
        self
    ) -> Iterator[tuple[read_termwiki.TermWikiPage, str, Any]]:
        dumphandler = DumpHandler()
        for dump_tw_page, page_id in dumphandler.dump_pages_newer_than_timestamp(
            read_time_stamp()
        ):
            page = self.site.pages[dump_tw_page.title]

            try:
                yield (
                    read_termwiki.termwiki_page_to_dataclass(
                        dump_tw_page.title, iter(page.text().splitlines())
                    ),
                    page_id,
                    page,
                )
            except marshmallow.exceptions.ValidationError as error:
                print(
                    f"Error: Fix termwiki {dump_tw_page.title}",
                    error,
                    file=sys.stderr,
                )
                print(f"Content: {page.text()}", file=sys.stderr)

    def fix_recent_termwiki_pages(self) -> None:
        """Fix termwiki pages newer than the time stamp, including adding id.

        Args:
            timestamp: the time stamp to compare against

        Returns:
            The latest time stamp
        """
        # fix termwiki pages newer than the time stamp, including adding id
        for valid_site_tw_page, page_id, page in self.get_valid_site_termwiki_pages():
            fixed_tw_page = read_termwiki.cleanup_termwiki_page(valid_site_tw_page)
            if fixed_tw_page.concept is not None:
                fixed_tw_page.concept.page_id = page_id
                try:
                    if fixed_tw_page != valid_site_tw_page:
                        print("Saving", valid_site_tw_page.title)
                        self.save_page(
                            page,
                            fixed_tw_page.to_termwiki(),
                            summary="Fixing content",
                        )
                        time.sleep(0.2)  # only sleep if we actually save
                except KeyError as error:
                    print(
                        f"Error: Please fix {valid_site_tw_page.title}",
                        error,
                        file=sys.stderr,
                    )
                    content = json.dumps(
                        asdict(fixed_tw_page), ensure_ascii=False, indent=2
                    )
                    print(
                        f"Content: {content}",
                        file=sys.stderr,
                    )

    def fix_by_timestamp(self) -> None:
        """Fix termwiki pages by timestamp."""
        if not os.getenv("GTHOME"):
            raise SystemExit("Error: The environment value GTHOME is not set")
        update_svn()
        self.fix_recent_termwiki_pages()
        write_time_stamp(datetime.now(timezone.utc))
        self.fix_expression_pages()
        self.delete_redirects()
