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
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import sys
from typing import Generator, Tuple

import hfst
from lxml import etree
from marshmallow import ValidationError

from termwikitools.handler_common import LANGUAGES, NAMESPACES
from termwikitools.read_termwiki import (
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

    termwiki_xml_root = os.path.join(os.getenv("GTHOME"), "words/terms/termwiki")
    dump = os.path.join(termwiki_xml_root, "dump.xml")
    tree = etree.parse(dump)
    mediawiki_ns = "{http://www.mediawiki.org/xml/export-0.10/}"

    def save_concept(self, tw_concept: Concept, main_title: str) -> None:
        """Save a concept to the dump file."""
        root = self.tree.getroot()
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        title = root.xpath(f'.//mw:title[text()="{main_title}"]', namespaces=namespace)[
            0
        ]
        if title is not None:
            page = title.getparent()
            tuxt = page.xpath(".//mw:text", namespaces=namespace)[0]
            tuxt.text = str(tw_concept)
        else:
            raise SystemExit(f"did not find {main_title}")

    @property
    def pages(self) -> Generator[Tuple[str, etree.Element, str], None, None]:
        """Get the namespaced pages from dump.xml.

        Yields:
            tuple: The title and the content of a TermWiki page.
        """
        for page in self.tree.getroot().iter("{}page".format(self.mediawiki_ns)):
            title = page.find(".//{}title".format(self.mediawiki_ns)).text
            page_id = page.find(".//{}id".format(self.mediawiki_ns)).text
            if title[: title.find(":")] in NAMESPACES:
                yield title, page, page_id

    @property
    def content_elements(self) -> Generator[Tuple[str, str, str], None, None]:
        """Get concept elements found in dump.xml.

        Yields:
            etree.Element: the content element found in a page element.
        """
        for title, page, page_id in self.pages:
            content_elt = page.find(f".//{self.mediawiki_ns}text")
            if content_elt.text and "{{Concept" in content_elt.text:
                yield title, content_elt, page_id

    @property
    def concepts(self) -> Generator[Tuple[str, TermWikiPage], None, None]:
        """Get concepts found in dump.xml.

        Yields:
            Concept: the content element found in a page element.
        """
        for title, content_elt, _ in self.content_elements:
            try:
                yield title, termwiki_page_to_dataclass(
                    title, iter(content_elt.text.replace("\xa0", " ").splitlines())
                )
            except (ValidationError, KeyError) as error:
                print(
                    "Error",
                    error,
                    f"https://satni.uit.no/termwiki/index.php?title={title.replace(' ', '_')}",
                    file=sys.stderr,
                )

    def expressions(
        self, language, only_sanctioned
    ) -> Generator[Tuple[str, RelatedExpression], None, None]:
        """All expressions found in dumphandler."""
        return (
            (title, expression)
            for title, concept in self.concepts
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
                    for _, termwikipage in self.concepts
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
    ) -> collections.defaultdict:
        # TODO: make suggestions: remove Err-tags, run analyses through generator-norm
        desc_analyser = hfst.HfstInputStream(
            f"/usr/local/share/giella/{language}/analyser-gt-desc.hfstol"
        ).read()
        founds = collections.defaultdict(dict)

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
                founds[real_expression]["sources"] = [
                    source for source in sorted(not_in_norms[real_expression])
                ]

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
            print(" ".join([url for url in sorted(norms[norm])]))

    def sum_terms(self, language: str) -> None:
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        counter = collections.defaultdict(int)
        for _, concept in self.concepts:
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

    def print_invalid_chars(self, language, only_sanctioned) -> None:
        """Find terms with invalid characters, print the errors to stdout."""
        invalid_chars_re = re.compile(r"[()[\]?:;+*=]")
        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(language, only_sanctioned):
            if invalid_chars_re.search(expression.expression):
                print(
                    f'{expression.expression} {base_url}/index.php?title={title.replace(" ", "_")}'
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
        for title, concept in self.concepts:
            if category is None or title.startswith(category):
                if concept.has_sanctioned_sami():
                    langs = {lang1: set(), lang2: set()}
                    for expression in concept.related_expressions:
                        if expression.language == lang1 or expression.language == lang2:
                            if expression.sanctioned:
                                langs[expression.language].add(expression.expression)

                    if langs[lang1] and langs[lang2]:
                        for expression in langs[lang1]:
                            print("{}\t{}".format(expression, ", ".join(langs[lang2])))

    def statistics(self, language: str) -> None:
        invalid_chars_re = re.compile(r"[()[\]?:;+*=]")
        counter = {}
        for title, concept in self.concepts:
            if any(
                [
                    expression.language == language
                    for expression in concept.related_expressions
                ]
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
                        if invalid_chars_re.search(expression.expression)
                    ]
                )

        total = collections.defaultdict(int)
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
