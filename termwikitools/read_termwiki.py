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
"""Read termwiki pages."""

from dataclasses import asdict, dataclass, field
from typing import Generator, Iterable
from marshmallow import ValidationError
import marshmallow_dataclass

from termwikitools.handler_common import LANGUAGES


def validate_lang(language):
    return (
        ValidationError(f"language must be one of {LANGUAGES.values()}")
        if language not in LANGUAGES.values()
        else None
    )


def validate_pos(pos):
    pos = [
        "N",
        "A",
        "Adv",
        "V",
        "Pron",
        "CS",
        "CC",
        "Adp",
        "Po",
        "Pr",
        "Interj",
        "Pcle",
        "Num",
        "ABBR",
        "MWE",
    ]

    return ValidationError(f"pos must be one of {pos}") if pos not in pos else None


def validate_relation(relation):
    relations = [
        "broader concept",
        "narrower concept",
        "coordinate concept",
        "comprehensive concept",
        "partitive concept",
        "pragmatic relation",
        "cohyponym",  # spurious value found in termwiki
        "unspecified",
    ]

    return (
        ValidationError(f"relation must be one of {relations}")
        if relation not in relations
        else None
    )


def validate_status(status):
    statuses = ["recommended", "out of date", "avoid", "rare"]

    return (
        ValidationError(f"status must be one of {statuses}")
        if status not in statuses
        else None
    )


@dataclass
class ConceptInfo:
    language: str = field(metadata={"validate": validate_lang})
    definition: str | None
    explanation: str | None
    more_info: str | None

    def to_termwiki(self) -> str:
        strings = ["{{Concept info"]
        strings.extend(
            [
                f"|{key}={value}"
                for key, value in asdict(self).items()
                if value is not None
            ]
        )
        strings.append("}}")

        return "\n".join(strings)


@dataclass
class RelatedExpression:
    language: str = field(metadata={"validate": validate_lang})
    expression: str
    pos: str | None
    status: str | None = field(metadata={"validate": validate_status})
    note: str | None
    source: str | None
    inflection: str | None
    country: str | None
    dialect: str | None
    sanctioned: str = "False"

    def to_termwiki(self) -> str:
        strings = ["{{Related expression"]
        strings.extend(
            [
                f"|{key}={value}"
                for key, value in asdict(self).items()
                if value is not None
            ]
        )
        strings.append("}}")

        return "\n".join(strings)


@dataclass
class RelatedConcept:
    concept: str
    relation: str = field(
        default="unspecified", metadata={"validate": validate_relation}
    )

    def to_termwiki(self) -> str:
        strings = ["{{Related concept"]
        strings.extend(
            [
                f"|{key}={value}"
                for key, value in asdict(self).items()
                if value is not None
            ]
        )
        strings.append("}}")

        return "\n".join(strings)


@dataclass
class Concept:
    collection: set[str] | None
    category: str | None
    main_category: str | None
    sources: str | None
    page_id: str | None

    def to_termwiki(self) -> str:
        concept_dict = asdict(self)
        if all(value is None for value in concept_dict.values()):
            return "{{Concept}}"

        # turn collection parts into a string again
        if concept_dict.get("collection"):
            concept_dict["collection"] = "@@ ".join(concept_dict.get("collection"))

        strings = ["{{Concept"]
        strings.extend(
            [
                f"|{key}={value}"
                for key, value in concept_dict.items()
                if value is not None
            ]
        )
        strings.append("}}")

        return "\n".join(strings)


@dataclass
class TermWikiPage:
    title: str
    concept: Concept | None
    concept_infos: list[ConceptInfo] | None
    related_expressions: list[RelatedExpression]
    related_concepts: list[RelatedConcept] | None

    def to_termwiki(self) -> str:
        strings = []
        if self.concept_infos:
            strings.extend(
                [concept_info.to_termwiki() for concept_info in self.concept_infos]
            )

        strings.extend(
            [
                related_expression.to_termwiki()
                for related_expression in self.related_expressions
            ]
        )

        if self.related_concepts:
            strings.extend(
                [
                    related_concept.to_termwiki()
                    for related_concept in self.related_concepts
                ]
            )
        strings.append(self.concept.to_termwiki())

        return "\n".join(strings)

    def find_invalid(
        self, language: str, sanctioned: bool
    ) -> Generator[str, None, None]:
        """Find expressions with invalid characters.

        Args:
            language (str): the language of the expressions

        Yields:
            str: an offending expression
        """
        for related_expression in self.related_expressions:
            if (
                related_expression.language == language
                and related_expression.sanctioned == sanctioned
            ):
                if self.invalid_chars_re.search(related_expression.expression):
                    yield related_expression.expression

    def has_sanctioned_sami(self) -> bool:
        return any(
            related_expression.language in ["se", "sma", "smj", "smn", "sms"]
            and related_expression.sanctioned == "True"
            for related_expression in self.related_expressions
        )


TERMWIKI_PAGE_SCHEMA = marshmallow_dataclass.class_schema(TermWikiPage)()


def termwiki_page_to_dataclass(
    title: str, text_iterator: Iterable[str]
) -> TermWikiPage:
    """Parse a termwiki page.

    Args:
        title: title of the TermWiki page
        text_iterator: iterator to the content of the termwiki page.

    Returns:
        dict: contains the content of the termwiki page.
    """

    concept_dict = {"title": title}
    for line in text_iterator:
        line = line.strip()
        if line.startswith("{{") and line.endswith("}}"):
            continue

        if line == "{{Concept info":
            if concept_dict.get("concept_infos") is None:
                concept_dict["concept_infos"] = []
            concept_dict["concept_infos"].append(read_semantic_form(text_iterator))

        if line == "{{Concept":
            concept = read_semantic_form(text_iterator)

            # turn collection parts into a set
            if concept.get("collection"):
                concept["collection"] = {
                    collection.strip()
                    for collection in concept["collection"].split("@@")
                }
            concept_dict["concept"] = concept

        if line == "{{Related expression":
            if concept_dict.get("related_expressions") is None:
                concept_dict["related_expressions"] = []
            concept_dict["related_expressions"].append(
                read_semantic_form(text_iterator)
            )

        if line == "{{Related concept":
            if concept_dict.get("related_concepts") is None:
                concept_dict["related_concepts"] = []
            concept_dict["related_concepts"].append(read_semantic_form(text_iterator))

    return TERMWIKI_PAGE_SCHEMA.load(concept_dict)


def read_semantic_form(text_iterator):
    """Turn a template into a dict.

    Args:
        text_iterator (str_iterator): the contents of the termwiki article.

    Returns:
        importer.OrderedDefaultDict
    """
    wiki_form = {}
    for line in text_iterator:
        if line == "}}":
            break
        elif line.startswith("|"):
            (key, _, value) = line[1:].partition("=")
            if value:
                wiki_form[key] = value.strip()
        else:
            try:
                wiki_form[key] = "\n".join([wiki_form[key], line.strip()])
            except UnboundLocalError:
                pass

    return wiki_form


LANG_TRANS = {
    """Sammallahti letters from his sme-fin dictionary"""
    "se": str.maketrans("Èéíïēīĵĺōūḥḷṃṇṿạẹọụÿⓑⓓⓖ·ṛü’ ", "Eeiieijlouhlmrvaeouybdg ru' "),
    """Replace invalid accents with valid ones for the sms language.

    * u2019: RIGHT SINGLE QUOTATION MARK
    * u0027: APOSTROPHE
    * u2032: PRIME
    * u00B4: ACUTE ACCENT
    * u0301: COMBINING ACUTE ACCENT
    * u02BC: MODIFIER LETTER APOSTROPHE
    * u02B9: MODIFIER LETTER PRIME"""
    "sms": str.maketrans(
        "\u2019\u0027\u2032\u00B4\u0301", "\u02BC\u02BC\u02B9\u02B9\u02B9"
    ),
}


def cleanup_expression(expression: RelatedExpression) -> dict:
    """Clean up expression."""
    expression = asdict(expression)

    # Fix pos
    if " " in expression["expression"]:
        expression["pos"] = "MWE"

    if LANG_TRANS.get(expression["language"]):
        expression["expression"] = expression["expression"].translate(
            LANG_TRANS.get(expression["language"])
        )

    return expression


def cleanup_concept(concept: Concept) -> dict:
    """Clean up concept data."""
    concept_dict = asdict(concept)

    if concept.collection:
        concept_dict["collection"] = {
            f"Collection:{collection.strip()}"
            if "Collection:" not in collection
            else collection.strip()
            for collection in concept_dict["collection"]
        }

    return concept_dict


def cleanup_termwiki_page(termwiki_page: TermWikiPage) -> TermWikiPage:
    termwiki_page_dict = asdict(termwiki_page)
    termwiki_page_dict["concept"] = cleanup_concept(termwiki_page.concept)
    termwiki_page_dict["related_expressions"] = [
        cleanup_expression(expression)
        for expression in termwiki_page.related_expressions
    ]

    return TERMWIKI_PAGE_SCHEMA.load(termwiki_page_dict)
