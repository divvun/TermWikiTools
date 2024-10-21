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
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Generator, Iterable, Tuple

import hfst  # type: ignore
from lxml import etree
from lxml.etree import _Element
from marshmallow import ValidationError

from termwikitools import read_termwiki
from termwikitools.handler_common import LANGUAGES, NAMESPACES
from termwikitools.read_termwiki import (
    INVALID_CHARS_RE,
    Concept,
    RelatedExpression,
    TermWikiPage,
    termwiki_page_to_dataclass,
)
from termwikitools.satni import termwikipage_to_satniconcept

ATTS = re.compile(r"@[^@]+@")


class DumpHandler:
    """Class that involves using the TermWiki dump.

    Attributes:
        termwiki_xml_root (str): path where termwiki xml files live.
        dump (str): path to the dump file.
        tree (etree.ElementTree): the parsed dump file.
        mediawiki_ns (str): the mediawiki name space found in the dump file.
    """

    termwiki_xml_root = os.path.join(os.getenv("GTHOME") or "", "words/terms/termwiki")
    dump = os.path.join(termwiki_xml_root, "dump.xml")
    tree = etree.parse(dump)
    mediawiki_ns = "{http://www.mediawiki.org/xml/export-0.10/}"

    def save_concept(self, tw_concept: Concept, main_title: str) -> None:
        """Save a concept to the dump file."""
        root = self.tree.getroot()
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        titles = root.xpath(f'.//mw:title[text()="{main_title}"]', namespaces=namespace)
        title = titles[0]
        if title is not None:
            page = title.getparent()
            tuxt = page.xpath(".//mw:text", namespaces=namespace)[0]
            tuxt.text = str(tw_concept)
        else:
            raise SystemExit(f"did not find {main_title}")

    @property
    def pages(self) -> Iterable[Tuple[str, _Element, str]]:
        """Get the namespaced pages from dump.xml.

        Yields:
            tuple: The title and the content of a TermWiki page.
        """
        for page in self.tree.getroot().iter("{}page".format(self.mediawiki_ns)):
            if page is not None:
                title_element = page.find(".//{}title".format(self.mediawiki_ns))
                if title_element is not None and title_element.text is not None:
                    title = title_element.text
                    if title[: title.find(":")] in NAMESPACES:
                        page_id_element = page.find(".//{}id".format(self.mediawiki_ns))
                        if (
                            page_id_element is not None
                            and page_id_element.text is not None
                        ):
                            yield title, page, page_id_element.text

    @property
    def content_elements(self) -> Iterable[Tuple[str, _Element, str]]:
        """Get concept elements found in dump.xml.

        Yields:
            etree.Element: the content element found in a page element.
        """
        for title, page, page_id in self.pages:
            content_elt = page.find(f".//{self.mediawiki_ns}text")
            if (
                content_elt is not None
                and content_elt.text
                and "{{Concept" in content_elt.text
            ):
                yield title, content_elt, page_id

    @property
    def termwiki_pages(self) -> Iterable[Tuple[str, TermWikiPage]]:
        """Get concepts found in dump.xml.

        Yields:
            Concept: the content element found in a page element.
        """
        for title, content_elt, _ in self.content_elements:
            try:
                if content_elt is not None and content_elt.text:
                    yield title, termwiki_page_to_dataclass(
                        title, iter(content_elt.text.replace("\xa0", " ").splitlines())
                    )
            except (ValidationError, KeyError) as error:
                print(
                    "Error",
                    error,
                    "https://satni.uit.no/termwiki/index.php?title="
                    f"{title.replace(' ', '_')}",
                    file=sys.stderr,
                )

    def expressions(
        self, language, only_sanctioned
    ) -> Iterable[Tuple[str, RelatedExpression]]:
        """All expressions found in dumphandler."""
        return (
            (title, expression)
            for title, concept in self.termwiki_pages
            for expression in concept.related_expressions
            if (
                expression.language == language
                and expression.sanctioned == only_sanctioned
            )
        )

    def dump2json(self):
        json_file = Path("terms.json")
        json_file.write_text(
            json.dumps(
                [
                    asdict(termwikipage_to_satniconcept(termwikipage))
                    for _, termwikipage in self.termwiki_pages
                ]
            )
        )

    def not_found_in_normfst(
        self, language: str, only_sanctioned: str
    ) -> collections.defaultdict:
        """Return expressions not found in normfst."""
        not_founds = collections.defaultdict(set)
        norm_analyser = hfst.HfstInputStream(
            f"/usr/local/share/giella/{language}/analyser-gt-norm.hfstol"
        ).read()

        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(LANGUAGES[language], only_sanctioned):
            for real_expression in [
                re.sub(r"[\(\),?\+\*\[\]=;:!]", "", real_expression)
                for real_expression1 in expression.expression.split()
                for real_expression in real_expression1.split("/")
            ]:
                if (
                    real_expression
                    and not real_expression.startswith(("‑", "-"))
                    and not norm_analyser.lookup(real_expression)
                ):
                    not_founds[real_expression].add(
                        f'{base_url}/index.php?title={title.replace(" ", "_")}'
                    )

        return not_founds

    @staticmethod
    def known_to_descfst(
        language: str, not_in_norms: collections.defaultdict
    ) -> dict[str, dict[str, set[str] | list[str]]]:
        # TODO: make suggestions: remove Err-tags, run analyses through generator-norm
        desc_analyser = hfst.HfstInputStream(
            f"/usr/local/share/giella/{language}/analyser-gt-desc.hfstol"
        ).read()
        founds: dict[str, dict[str, set[str] | list[str]]] = collections.defaultdict(
            dict
        )

        for real_expression in not_in_norms:
            analyses = {
                ATTS.sub("", analysis[0])
                for analysis in desc_analyser.lookup(real_expression)
            }
            # Remove compounds if lemma is lexicalised
            if any("+Cmp#" not in analysis for analysis in analyses):
                analyses = {
                    analysis for analysis in analyses if "+Cmp#" not in analysis
                }
            # If any analysis endswith +Nom, keep analyses ending with +Nom
            if any(analysis.endswith("+Nom") for analysis in analyses):
                analyses = {
                    analysis for analysis in analyses if analysis.endswith("+Nom")
                }
            if analyses:
                founds[real_expression]["analyses"] = analyses
                founds[real_expression]["sources"] = sorted(
                    not_in_norms[real_expression]
                )

        return founds

    def print_missing(self, language, only_sanctioned):
        """Find all expressions of the given language.

        Args:
            language (src): language of the terms.
        """

        def revsorted_expressions(not_founds):
            return [
                reverted[::-1]
                for reverted in sorted([not_found[::-1] for not_found in not_founds])
            ]

        not_in_norms = self.not_found_in_normfst(language, only_sanctioned)

        descriptives = self.known_to_descfst(language, not_in_norms)
        for descriptive in revsorted_expressions(descriptives):
            print(descriptive)
            print(
                "\n".join(
                    [
                        f"{descriptive}\t{analysis}"
                        for analysis in descriptives[descriptive]["analyses"]
                    ]
                )
            )
            print(
                "\n".join(
                    [f"\t{source}" for source in descriptives[descriptive]["sources"]]
                )
            )
            print()

        norms = {
            expression: not_in_norms[expression]
            for expression in not_in_norms
            if expression not in descriptives
        }

        for norm in revsorted_expressions(norms):
            print(f"{norm}:{norm} TODO ; !", end="  ")
            print(" ".join(sorted(norms[norm])))

    def sum_terms(self, language: str) -> None:
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        counter: dict[str, int] = collections.defaultdict(int)
        for _, concept in self.termwiki_pages:
            for expression in concept.related_expressions:
                if expression.language == language:
                    counter[expression.sanctioned] += 1

        print(
            "{}:\nSanctioned:\t{}\nNot-sanctioned:\t{}\nTotal:\t\t{}".format(
                language,
                counter["True"],
                counter["False"],
                counter["False"] + counter["True"],
            )
        )

    def terms_of_lang(self, language: str) -> None:
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        for title, concept in self.termwiki_pages:
            for expression in concept.related_expressions:
                if expression.language == language and expression.sanctioned == "True":
                    print(
                        expression.expression,
                        f'https://satni.uit.no/termwiki/index.php?title={title.replace(" ", "_")}',  # noqa: E501
                    )

    def print_invalid_chars(self, language, only_sanctioned) -> None:
        """Find terms with invalid characters, print the errors to stdout."""
        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(language, only_sanctioned):
            if INVALID_CHARS_RE.search(expression.expression):
                print(
                    f"{expression.expression} "
                    f'{base_url}/index.php?title={title.replace(" ", "_")}'
                )

    def find_collections(self):
        """Check if collections are correctly defined."""
        for title, _, page in self.pages:
            if title.startswith("Collection:"):
                content_elt = page.find(".//{}text".format(self.mediawiki_ns))
                text = content_elt.text
                if text:
                    if "{{Collection" not in text:
                        print("|collection={}\n{}".format(title, text))
                        print()
                else:
                    print(title, etree.tostring(content_elt, encoding="unicode"))

    def collection_to_excel(self, name: str):
        """Write a collection to an excel file."""

        def get_languages(name: str) -> list[str]:
            namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
            collection_elements = self.tree.getroot().xpath(
                f'.//mw:page/mw:title[text() = "{name}"]',
                namespaces=namespace,
            )

            if not collection_elements:
                raise SystemExit(f"Collection {name} not found")

            if collection_elements[0].text is None:
                raise SystemExit(f"Collection {name} has no content")

            page = collection_elements[0].getparent()

            content_elt = page.find(".//{}text".format(self.mediawiki_ns))
            text = content_elt.text
            print(text)
            content = read_termwiki.read_semantic_form(
                iter(text.replace("\xa0", " ").splitlines())
            )
            print(content)
            return content.get("languages", "").split(", ")

        def get_collection_content(
            name: str,
        ) -> Generator[list[Tuple[str, str]], None, None]:
            for _, termwikipage in self.termwiki_pages:
                if (
                    termwikipage.concept is not None
                    and termwikipage.concept.collection
                    and name in termwikipage.concept.collection
                ):
                    yield [
                        (
                            "\n".join(termwikipage.get_terms(language)),
                            termwikipage.get_definition(language),
                        )
                        for language in languages
                    ]

        from openpyxl import Workbook
        from openpyxl.styles import Alignment

        wb = Workbook()
        ws = wb.active

        languages = get_languages(f"Collection:{name}")
        ws.append(languages)
        for y_index, row in enumerate(
            get_collection_content(f"Collection:{name}"), start=2
        ):
            if any(terms for (terms, _) in row):
                for x_index, (terms, definition) in enumerate(row, start=1):
                    ws.cell(
                        row=y_index, column=x_index, value=f"{terms}{definition}"
                    ).alignment = Alignment(shrink_to_fit=True, wrap_text=True)

        wb.save(f"{name.replace(' ', '_')}.xlsx")

    def sort_dump(self):
        """Sort the dump file by page title."""
        root = self.tree.getroot()
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}

        pages = root.xpath(".//mw:page", namespaces=namespace)
        pages[:] = sorted(
            pages, key=lambda page: page.find("./mw:title", namespaces=namespace).text
        )

        for page in root.xpath(".//mw:page", namespaces=namespace):
            page.getparent().remove(page)

        for page in pages:
            root.append(page)

        self.tree.write(self.dump, pretty_print=True, encoding="utf-8")

    def print_expression_pairs(self, lang1, lang2, category=None):
        """Print pairs of expressions, for use in making bidix files."""
        for title, concept in self.termwiki_pages:
            if category is None or title.startswith(category):
                if concept.has_sanctioned_sami():
                    langs = {lang1: set(), lang2: set()}
                    for expression in concept.related_expressions:
                        if expression.language in (lang1, lang2):
                            if expression.sanctioned:
                                langs[expression.language].add(expression.expression)

                    if langs[lang1] and langs[lang2]:
                        for expression in langs[lang1]:
                            print("{}\t{}".format(expression, ", ".join(langs[lang2])))

    def statistics(self, language: str) -> None:
        counter: dict[str, dict[str, int]] = {}
        for title, concept in self.termwiki_pages:
            if any(
                expression.language == language
                for expression in concept.related_expressions
            ):
                category = title[: title.find(":")]
                if not counter.get(category):
                    counter[category] = collections.defaultdict(int)
                counter[category]["concepts"] += 1
                expression_with_lang = [
                    expression
                    for expression in concept.related_expressions
                    if expression.language == language
                ]
                counter[category]["expressions"] += len(expression_with_lang)
                counter[category]["true_expressions"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if expression.sanctioned == "True"
                    ]
                )
                counter[category]["false_expressions"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if expression.sanctioned == "False"
                    ]
                )
                counter[category]["invalid"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if INVALID_CHARS_RE.search(expression.expression)
                    ]
                )

        total: dict[str, int] = collections.defaultdict(int)
        print(language)
        for category in counter:
            print(category)
            for item in counter[category].items():
                total[item[0]] += item[1]
                print(f"{item[0]}\t{item[1]}")
            print()

        print(f"Totally for {language}")
        for item in total.items():
            total[item[0]] += item[1]
            print(f"{item[0]}\t{item[1]}")
        print()
