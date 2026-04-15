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
import itertools
import json
import os
import re
import sys
import urllib.parse
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Generator, Iterable, Iterator, Tuple

import hfst
import marshmallow
from lxml import etree
from lxml.etree import _Element
from marshmallow import ValidationError
from openpyxl import Workbook
from openpyxl.styles import Alignment
from rdflib import RDF, SKOS, BNode, Graph, Literal, Namespace, URIRef

from termwikitools import read_termwiki
from termwikitools.handler_common import LANGUAGES, NAMESPACES
from termwikitools.read_termwiki import (
    INVALID_CHARS_RE,
    Concept,
    ConceptInfo,
    RelatedConcept,
    RelatedExpression,
    TermWikiPage,
    termwiki_page_to_dataclass,
)

ATTS = re.compile(r"@[^@]+@")

# VocBench export constants
_VOCBENCH_BASE = "https://satni.uit.no/termwiki/"
_TW = Namespace(_VOCBENCH_BASE + "prop/")
SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")

_LANG_TAGS: dict[str, str] = {
    "se": "se",
    "fi": "fi",
    "en": "en",
    "nb": "nb",
    "nn": "nn",
    "sv": "sv",
    "sma": "sma",
    "smj": "smj",
    "smn": "smn",
    "sms": "sms",
    "lat": "la",
}

_RELATION_MAP: dict[str, URIRef] = {
    "broader concept": SKOS.broader,
    "comprehensive concept": SKOS.broader,
    "hyperonym": SKOS.broader,
    "narrower concept": SKOS.narrower,
    "partitive concept": SKOS.narrower,
    "coordinate concept": SKOS.related,
    "cohyponym": SKOS.related,
    "synonym": SKOS.related,
    "pragmatic relation": SKOS.related,
    "unspecified": SKOS.related,
}


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
                    yield (
                        title,
                        termwiki_page_to_dataclass(
                            title,
                            iter(content_elt.text.replace("\xa0", " ").splitlines()),
                        ),
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
        self, language: str, only_sanctioned: str
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
                [asdict(termwikipage) for _, termwikipage in self.termwiki_pages],
                ensure_ascii=False,
                indent=2,
            )
        )

    def dump2vocbench(self, output_path: str = "termwiki.ttl") -> None:
        """Convert dump.xml content to SKOS/RDF Turtle for VocBench import.

        Each TermWiki page becomes a skos:Concept. Collections become
        skos:ConceptScheme instances. Sanctioned expressions become
        skos:prefLabel (first per language) or skos:altLabel; unsanctioned
        expressions become skos:altLabel. Definitions map to skos:definition
        and explanations to skos:scopeNote.

        Args:
            output_path: Destination file path (default: termwiki.ttl).
        """
        base = Namespace(_VOCBENCH_BASE)
        g = Graph()
        g.bind("skos", SKOS)
        g.bind("skosxl", SKOSXL)
        g.bind("termwiki", base)
        g.bind("tw", _TW)

        schemes: dict[str, URIRef] = {}

        def concept_uri(title: str) -> URIRef:
            return base["index.php?title=" + urllib.parse.quote(title, safe="")]

        def ensure_scheme(collection: str) -> URIRef:
            if collection not in schemes:
                uri = base["scheme/" + urllib.parse.quote(collection, safe="")]
                schemes[collection] = uri
                g.add((uri, RDF.type, SKOS.ConceptScheme))
                g.add((uri, SKOS.prefLabel, Literal(collection)))
            return schemes[collection]

        for title, page in self.termwiki_pages:
            self._add_concept_to_graph(g, page, title, concept_uri, ensure_scheme)

        output = Path(output_path)
        output.write_text(g.serialize(format="turtle"), encoding="utf-8")
        print(f"Wrote {len(g)} triples to {output}")

    @staticmethod
    def _add_concept_to_graph(
        g: Graph,
        page: TermWikiPage,
        title: str,
        concept_uri: Callable[[str], URIRef],
        ensure_scheme: Callable[[str], URIRef],
    ) -> None:
        uri = concept_uri(title)
        g.add((uri, RDF.type, SKOS.Concept))
        if page.concept and page.concept.collection:
            for collection in page.concept.collection:
                g.add((uri, SKOS.inScheme, ensure_scheme(collection)))
        DumpHandler._add_labels(g, uri, page.related_expressions)
        DumpHandler._add_definitions(g, uri, page.concept_infos)
        DumpHandler._add_relations(g, uri, page.related_concepts, concept_uri)

    @staticmethod
    def _add_labels(
        g: Graph, uri: URIRef, expressions: Iterable[RelatedExpression]
    ) -> None:
        pref_label_langs: set[str] = set()
        for expr in expressions:
            tag = _LANG_TAGS.get(expr.language, expr.language)
            literal = Literal(expr.expression, lang=tag)
            is_pref = expr.sanctioned == "True" and tag not in pref_label_langs
            if is_pref:
                pref_label_langs.add(tag)

            label_node = BNode()
            g.add((label_node, RDF.type, SKOSXL.Label))
            g.add((label_node, SKOSXL.literalForm, literal))
            if expr.pos:
                g.add((label_node, _TW.pos, Literal(expr.pos)))
            if expr.source:
                g.add((label_node, _TW.source, Literal(expr.source)))
            if expr.inflection:
                g.add((label_node, _TW.inflection, Literal(expr.inflection)))
            if expr.country:
                g.add((label_node, _TW.country, Literal(expr.country)))
            if expr.dialect:
                g.add((label_node, _TW.dialect, Literal(expr.dialect)))
            if expr.status:
                g.add((label_node, _TW.status, Literal(expr.status)))
            if expr.note:
                g.add((label_node, SKOS.note, Literal(expr.note, lang=tag)))

            pred = SKOSXL.prefLabel if is_pref else SKOSXL.altLabel
            g.add((uri, pred, label_node))

    @staticmethod
    def _add_definitions(
        g: Graph, uri: URIRef, concept_infos: Iterable[ConceptInfo] | None
    ) -> None:
        if not concept_infos:
            return
        for ci in concept_infos:
            tag = _LANG_TAGS.get(ci.language, ci.language)
            if ci.definition:
                g.add((uri, SKOS.definition, Literal(ci.definition, lang=tag)))
            if ci.explanation:
                g.add((uri, SKOS.scopeNote, Literal(ci.explanation, lang=tag)))
            if ci.more_info:
                g.add((uri, SKOS.note, Literal(ci.more_info, lang=tag)))

    @staticmethod
    def _add_relations(
        g: Graph,
        uri: URIRef,
        related_concepts: Iterable[RelatedConcept] | None,
        concept_uri: Callable[[str], URIRef],
    ) -> None:
        if not related_concepts:
            return
        for rc in related_concepts:
            predicate = _RELATION_MAP.get(rc.relation, SKOS.related)
            g.add((uri, predicate, concept_uri(rc.concept)))

    def not_found_in_normfst(
        self, language: str, only_sanctioned: str
    ) -> collections.defaultdict:
        giella_dir = os.getenv("GTLANGS")
        assert giella_dir is not None, "GTLANGS environment variable not set"
        """Return expressions not found in normfst."""
        not_founds = collections.defaultdict(set)
        norm_analyser_path = (
            Path(giella_dir)
            / f"lang-{language}"
            / "src"
            / "fst"
            / "analyser-gt-norm.hfstol"
        )
        assert norm_analyser_path.exists(), (
            f"Norm analyser not found: {norm_analyser_path}"
        )
        norm_analyser = hfst.HfstInputStream(norm_analyser_path.as_posix()).read()

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
                        f"{base_url}/index.php?title={title.replace(' ', '_')}"
                    )

        return not_founds

    @staticmethod
    def known_to_descfst(
        language: str, not_in_norms: collections.defaultdict
    ) -> dict[str, dict[str, set[str] | list[str]]]:
        # TODO: make suggestions: remove Err-tags, run analyses through generator-norm
        giella_dir = os.getenv("GTLANGS")
        assert giella_dir is not None, "GTLANGS environment variable not set"
        desc_analyser_path = (
            Path(giella_dir)
            / f"lang-{language}"
            / "src"
            / "fst"
            / "analyser-gt-desc.hfstol"
        )
        assert desc_analyser_path.exists(), (
            f"Descriptive analyser not found: {desc_analyser_path}"
        )
        desc_analyser = hfst.HfstInputStream(desc_analyser_path.as_posix()).read()
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

    def typo_analyses_to_suggestions(
        self, typo_analyses: Iterable[str], language
    ) -> set[str]:
        giella_dir = os.getenv("GTLANGS")
        assert giella_dir is not None, "GTLANGS environment variable not set"
        norm_generator_path = (
            Path(giella_dir)
            / f"lang-{language}"
            / "src"
            / "fst"
            / "generator-gt-norm.hfstol"
        )
        assert norm_generator_path.exists(), (
            f"Descriptive generator not found: {norm_generator_path}"
        )
        norm_generator = hfst.HfstInputStream(norm_generator_path.as_posix()).read()
        rinsed_blabla = (
            analysis.replace("+Err/Orth", "").replace("+Err/Lex", "")
            for analysis in typo_analyses
        )
        return {
            ATTS.sub("", suggestion[0])
            for analysis in rinsed_blabla
            for suggestion in norm_generator.lookup(analysis)
        }

    def print_missing(self, language: str, only_sanctioned: str):
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

        norms = {
            expression: not_in_norms[expression]
            for expression in not_in_norms
            if expression not in descriptives
        }

        for norm in revsorted_expressions(norms):
            print(f"{norm}:{norm} TODO ; !", end="  ")
            print(" ".join(sorted(norms[norm])))

    def print_typos(self, language: str, only_sanctioned: str) -> None:
        """Find all expressions of the given language.

        Args:
            language: language of the terms.
        """

        def revsorted_expressions(not_founds):
            return [
                reverted[::-1]
                for reverted in sorted([not_found[::-1] for not_found in not_founds])
            ]

        not_in_norms = self.not_found_in_normfst(language, only_sanctioned)

        descriptives = self.known_to_descfst(language, not_in_norms)
        for descriptive in revsorted_expressions(descriptives):
            suggestions = self.typo_analyses_to_suggestions(
                descriptives[descriptive]["analyses"], language
            )
            if suggestions and descriptive not in suggestions:
                sources = "\n".join(
                    [f"\t{source}" for source in descriptives[descriptive]["sources"]]
                )
                print(f"{descriptive} -> {', '.join(suggestions)}\n{sources}\n")

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
                        f"https://satni.uit.no/termwiki/index.php?title={title.replace(' ', '_')}",  # noqa: E501
                    )

    def print_invalid_chars(self, language: str, only_sanctioned: str) -> None:
        """Find terms with invalid characters, print the errors to stdout."""
        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(language, only_sanctioned):
            if INVALID_CHARS_RE.search(expression.expression):
                print(
                    f"{expression.expression} "
                    f"{base_url}/index.php?title={title.replace(' ', '_')}"
                )

    def find_collections(self) -> None:
        """Check if collections are correctly defined."""
        for title, page, _ in self.pages:
            if title.startswith("Collection:"):
                content_elt = page.find(".//{}text".format(self.mediawiki_ns))
                if content_elt is None:
                    print(title, "missing content element")
                    continue
                text = content_elt.text
                if text:
                    if "{{Collection" not in text:
                        print("|collection={}\n{}".format(title, text))
                        print()
                else:
                    print(title, etree.tostring(content_elt, encoding="unicode"))

    def _get_collection_languages(self, name: str) -> list[str]:
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        collection_elements = self.tree.getroot().xpath(
            f'.//mw:page/mw:title[text() = "{name}"]',
            namespaces=namespace,
        )

        if not collection_elements:
            raise SystemExit(f"Collection {name} not found")

        collection_title = collection_elements[0]
        if not isinstance(collection_title, _Element):
            raise SystemExit(f"Collection {name} has an unexpected XML shape")

        if collection_title.text is None:
            raise SystemExit(f"Collection {name} has no content")

        page = collection_title.getparent()
        if page is None:
            raise SystemExit(f"Collection {name} has no page element")

        content_elt = page.find(".//{}text".format(self.mediawiki_ns))
        if content_elt is None or content_elt.text is None:
            raise SystemExit(f"Collection {name} has no content")

        text = content_elt.text
        print(text)
        content = read_termwiki.read_semantic_form(
            iter(text.replace("\xa0", " ").splitlines())
        )
        print(content)
        return content.get("languages", "").split(", ")

    def _get_collection_content(
        self, name: str, languages: list[str]
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

    def collection_to_excel(self, name: str) -> None:
        """Write a collection to an excel file."""

        wb = Workbook()
        ws = wb.active
        if ws is None:
            raise SystemExit("Workbook has no active worksheet")

        languages = self._get_collection_languages(f"Collection:{name}")
        ws.append(languages)
        for y_index, row in enumerate(
            self._get_collection_content(f"Collection:{name}", languages), start=2
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

    def print_no_lang2(
        self, lang1: str, lang2: str, helper_langs: list[str], category=None
    ) -> None:
        """Print expressions of lang1, that do not exist in lang2."""
        for title, concept in self.termwiki_pages:
            if category is None or title.startswith(category):
                if concept.has_sanctioned_sami():
                    all_expressions: list[str] = []
                    langs: dict[str, set[str]] = collections.defaultdict(set)
                    for expression in concept.related_expressions:
                        if expression.language in [lang1, lang2] + helper_langs:
                            if expression.sanctioned:
                                langs[expression.language].add(expression.expression)

                    if langs[lang1] and not langs[lang2]:
                        all_expressions.append(f"{', '.join(langs[lang1])}")

                        for helper_lang in helper_langs:
                            if langs[helper_lang]:
                                all_expressions.append(
                                    f"{', '.join(langs[helper_lang])}"
                                )

                        print("{}".format("\t".join(all_expressions)))

    def find_duplicate_candidates(
        self, only_sanctioned: str
    ) -> dict[frozenset, set[str]]:
        """Return cross-language term pairs shared by more than one Concept page.

        Keys are frozensets of two (language, expression) pairs from different
        languages. Only entries where 2+ Concept pages share the pair are returned.
        """
        index: dict[frozenset, set[str]] = collections.defaultdict(set)
        for title, page in self.termwiki_pages:
            lang_expr_pairs = [
                (expr.language, expr.expression)
                for expr in page.related_expressions
                if only_sanctioned != "True" or expr.sanctioned == "True"
            ]
            for pair_a, pair_b in itertools.combinations(lang_expr_pairs, 2):
                if pair_a[0] != pair_b[0]:
                    key = frozenset({pair_a, pair_b})
                    index[key].add(title)
        return {key: titles for key, titles in index.items() if len(titles) > 1}

    def render_duplicate_candidates_wikitext(self, only_sanctioned: str) -> str:
        """Render duplicate candidates as a MediaWiki review page."""
        grouped: dict[tuple[str, str], list[tuple[tuple[str, str], list[str]]]] = (
            collections.defaultdict(list)
        )
        for pair, titles in self.find_duplicate_candidates(only_sanctioned).items():
            sorted_pair = tuple(sorted(pair, key=lambda p: (p[0], p[1])))
            lang_pair = (sorted_pair[0][0], sorted_pair[1][0])
            grouped[lang_pair].append((sorted_pair, sorted(titles)))

        lines = [
            "__TOC__",
            "",
            "This page lists possible duplicate Concept pages detected automatically.",
            "",
            "Use Decision=merge to approve merging, or keep to leave pages untouched.",
            "Only rows with Decision=merge and Processed=no are executed by the bot.",
            "",
        ]

        if not grouped:
            lines.append("No duplicate candidates were found.")
            return "\n".join(lines)

        for lang1, lang2 in sorted(grouped):
            lines.append(f"== {lang1} <-> {lang2} ==")
            lines.append('{| class="wikitable sortable"')
            lines.append(
                "! Term pair !! Candidate pages !! Decision "
                "!! Keep page !! Report !! Processed"
            )

            for pair, titles in sorted(grouped[(lang1, lang2)], key=lambda p: p[0]):
                set_titles = set(titles)
                if len(set_titles) > 1:
                    pair_text = " <-> ".join(f"{lang}:{expr}" for lang, expr in pair)
                    pages_text = " / ".join(f"[[{title}]]" for title in set_titles)
                    lines.append("|-")
                    lines.append(
                        f"| {pair_text} || {pages_text} || keep || || || no"
                    )

            lines.append("|}")
            lines.append("")

        return "\n".join(lines)

    def print_duplicate_candidates(self, only_sanctioned: str) -> None:
        """Print Concept pages that share a cross-language term pair."""
        candidates = self.find_duplicate_candidates(only_sanctioned)
        for pair, titles in sorted(candidates.items(), key=lambda x: sorted(x[1])):
            sorted_pair = sorted(pair, key=lambda p: p[0])
            print("  ".join(f"{lang}:{expr}" for lang, expr in sorted_pair))
            for title in sorted(titles):
                print(f"  {title}")
            print()

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
        for category, category_counts in counter.items():
            print(category)
            for key, value in category_counts.items():
                total[key] += value
                print(f"{key}\t{value}")
            print()

        print(f"Totally for {language}")
        for key, value in total.items():
            print(f"{key}\t{value}")
        print()

    def dump_pages_newer_than_timestamp(
        self, timestamp: datetime
    ) -> Iterator[tuple[TermWikiPage, str]]:
        """Check if the dump file is newer than the given timestamp."""
        dumphandler = DumpHandler()
        for title, dump_xml_page, page_id in dumphandler.pages:
            xml_timestamp = dump_xml_page.find(
                ".//{}timestamp".format(dumphandler.mediawiki_ns)
            )
            if xml_timestamp is not None and xml_timestamp.text is not None:
                dump_timestamp = datetime.fromisoformat(xml_timestamp.text.rstrip("Z"))
                if dump_timestamp > timestamp:
                    if dump_xml_page is not None and dump_xml_page.text:
                        try:
                            yield (
                                read_termwiki.termwiki_page_to_dataclass(
                                    title,
                                    iter(
                                        dump_xml_page.text.replace(
                                            "\xa0", " "
                                        ).splitlines()
                                    ),
                                ),
                                page_id,
                            )
                        except marshmallow.exceptions.ValidationError as error:
                            print(f"Error: {title}", error, file=sys.stderr)
                            print(f"Content: {dump_xml_page.text}", file=sys.stderr)
