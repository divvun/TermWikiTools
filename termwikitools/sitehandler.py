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
import collections
import os
import sys
from typing import Any, Generator

import mwclient
import yaml

from termwikitools import read_termwiki
from termwikitools.dumphandler import DumpHandler
from termwikitools.handler_common import NAMESPACES


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
        config_file = os.path.join(os.getenv("HOME"), ".config", "term_config.yaml")
        with open(config_file) as config_stream:
            config = yaml.load(config_stream, Loader=yaml.FullLoader)
            site = mwclient.Site("satni.uit.no", path="/termwiki/")
            site.login(config["username"], config["password"])

            print("Logging in to query …")

            return site

    @property
    def content_elements(self, verbose=False) -> Generator[Any, None, None]:
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
    def is_concept_tag(content):
        """Check if content is a TermWiki Concept page.

        Args:
            content (str): content of a TermWiki page.

        Returns:
            bool
        """
        return "{{Concept" in content

    @staticmethod
    def save_page(page: mwclient.page.Page, content: str, summary: str) -> None:
        """Save a given TermWiki page.

        Args:
            page (mwclient.page.Page): The page to be saved.
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
            for redirect_xml in root.xpath(
                './/mw:text[starts-with(text(), "#STIVREN")]', namespaces=namespace
            )
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
            dump_tw_page = read_termwiki.termwiki_page_to_dataclass(
                title, iter(content_elt.text.replace("\xa0", " ").splitlines())
            )
            if dump_tw_page.concept.page_id is None:
                page = self.site.Pages[title]
                site_tw_page = read_termwiki.termwiki_page_to_dataclass(
                    title, iter(page.text().splitlines())
                )
                site_tw_page.concept.page_id = page_id
                print(f"Adding {page_id} to {title}")
                page.save(site_tw_page.to_termwiki(), summary="Added id")

    def make_related_expression_dict(
        self, dump: DumpHandler
    ) -> collections.defaultdict:
        related_expression_dict = collections.defaultdict(set)
        for _, concept in dump.concepts:
            for expression_title in concept.related_expressions:
                related_expression_dict[
                    f'Expression:{expression_title.expression.replace("&amp;", "&")}'
                ].add(expression_title.language)

        return related_expression_dict

    def make_dump_expression_dict(self, dump: DumpHandler) -> dict:
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        return {
            expression_xml.text: expression_xml.getparent()
            .xpath(".//mw:text", namespaces=namespace)[0]
            .text
            for expression_xml in dump.tree.getroot().xpath(
                './/mw:title[starts-with(text(), "Expression:")]', namespaces=namespace
            )
        }

    def make_expression_pages(
        self,
        related_expression_dict: collections.defaultdict,
        dump_expression_dict: dict,
    ) -> None:
        for expression_title, languages in related_expression_dict.items():
            ideal_content = self.make_expression_content(languages)
            if ideal_content != dump_expression_dict.get(expression_title):
                dump_expression_dict[
                    expression_title
                ] = ideal_content  # to avoid this being deleted in [`delete_expression_pages`]
                self.fix_expression_page(expression_title, content=ideal_content)

    def delete_expression_pages(
        self,
        related_expression_dict: collections.defaultdict,
        dump_expression_dict: dict,
    ) -> None:
        related_expressions = {title for title in related_expression_dict.keys()}
        dump_expressions = {title for title in dump_expression_dict.keys()}

        for to_delete in related_expressions - dump_expressions:
            page = self.site.Pages[to_delete]
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
        page = self.site.Pages[expression_title]
        if not page.exists:
            self.save_page(page, content=content, summary="Making new expression page")
        else:
            if page.text != content:
                print("\treally fixing", expression_title)
                self.save_page(page, content=content, summary="Fixing expression page")

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
            expression_xml.text
            for expression_xml in root.xpath(
                f'.//mw:title[starts-with(text(), "{part_of_title}")]',
                namespaces=namespace,
            )
        }
        print(f"{len(to_deletes)} pages to delete")
        for to_delete in to_deletes:
            page = self.site.Pages[to_delete]
            if page.exists:
                print(f"Removing {to_delete}")
                page.delete(reason="Pages is not needed anymore")

    def fix(self) -> None:
        """Make the bot fix all pages."""
        dump = DumpHandler()
        for title, dump_tw_page in dump.concepts:
            fixed_dump_tw_page = read_termwiki.cleanup_termwiki_page(dump_tw_page)
            if dump_tw_page != fixed_dump_tw_page:
                page = self.pages[title]
                self.fix_termwiki_page(page)

    def fix_termwiki_page(self, page: Any) -> None:
        """Make the bot fix a named page."""
        if page.exists:
            tw_page = read_termwiki.termwiki_page_to_dataclass(
                page.name, iter(page.text().replace("\xa0", " ").splitlines())
            )
            fixed_tw_page = read_termwiki.cleanup_termwiki_page(tw_page)
            if fixed_tw_page != tw_page:
                self.save_page(
                    page, fixed_tw_page.to_termwiki(), summary="Fixing content"
                )
        else:
            print(f"page {page.name} does not exist")

    def semantic_ask_results(self, query):
        for number, answer in enumerate(self.site.ask(query), start=1):
            print(answer)
            yield number, answer["fulltext"]

    def add_extra_collection(self):
        visited_pages = set()
        dumphandler = DumpHandler()
        for title, content_elt, _ in dumphandler.content_elements:
            concept1 = read_termwiki.Concept()
            concept1.from_termwiki(content_elt.text)
            if "Collection:SD-terms" in concept1.collections:
                if title not in visited_pages:
                    visited_pages.add(title)
                    page = self.site.Pages[title]
                    concept = read_termwiki.Concept()
                    concept.from_termwiki(page.text())
                    name = title.split(":")[1]
                    extra_collection = f"Collection:SD-terms-{name[0].lower()}"
                    if extra_collection not in concept.collections:
                        concept.collections.add(extra_collection)
                        print(f"\n\t{title} {extra_collection}\n")
                        self.save_page(
                            page,
                            str(concept),
                            summary=f"Add collection: {extra_collection}",
                        )

        print(len(visited_pages))

    def query_replace_text(self, language):
        """Do a semantic media query and fix pages.

        Change the query and the actions when needed …

        http://mwclient.readthedocs.io/en/latest/reference/site.html#mwclient.client.Site.ask
        https://www.semantic-mediawiki.org/wiki/Help:API
        """
        query = (
            "[[Related expression::+]]"
            "[[Language::{}]]"
            "[[Sanctioned::False]]".format(language)
        )

        for number, concept in self.semantic_ask_results(query):
            if concept.collections is None:
                print("Hit no: {}, title: {}".format(number, concept.title))
                self.save_page(
                    page,
                    str(concept),
                    summary="Sanctioned expressions not associated with any "
                    "collections that the normative {} fst "
                    "recognises.".format(language),
                )

    def revert(self):
        """Automatically sanction expressions that have no collection.

        The theory is that concept pages with no collections mostly are from
        the risten.no import, and if there are no typos found in an expression
        they should be sanctioned.

        Args:
            language (str): the language to sanction
        """
        rollback_token = self.site.get_token("rollback")
        for page in self.content_elements:
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

    def fix_revisions(self) -> None:
        """Example on how to restore pages only touched by bots."""
        import time

        token = self.site.api("query", meta="tokens")
        start_time = time.strptime("15 Feb 19", "%d %b %y")

        dumphandler = DumpHandler()
        for title, content_elt, _ in dumphandler.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)

            if "Collection:JustermTana" in concept.collections:
                page = self.site.Pages[concept.title]
                users = {
                    revision["user"]
                    for revision in page.revisions()
                    if revision["timestamp"] > start_time
                    and "mporter" not in revision["user"]
                }
                if users:
                    print(title, users)
                else:
                    print(f"Saving {title}")
                    self.save_page(page, str(concept), summary="Saved from backup")

    def improve_pagenames(self) -> None:
        """Remove characters that break eXist search from page names."""
        for page in self.content_elements:
            try:
                my_title = read_termwiki.fix_sms(
                    self.remove_paren(page.name) if "(" in page.name else page.name
                )
                if page.name != my_title:
                    self.move_page(page.name, my_title)
            except mwclient.errors.InvalidPageTitle:
                print(f"Failed on {page.name}")
