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

import marshmallow_dataclass
from marshmallow import ValidationError

from termwikitools.handler_common import LANGUAGES


def validate_lang(language: str) -> None:
    """Validates if the given language is supported.

    Args:
        language (str): The language to be validated.

    Raises:
        ValidationError: If the language is not supported.

    Returns:
        None
    """
    if language not in LANGUAGES.values():
        raise ValidationError(f"{language} is not one of {LANGUAGES.values()}")


def validate_pos(pos: str) -> None:
    """Validate the given part-of-speech (POS) against a list of valid POS values.

    Args:
        pos (str): The part-of-speech to validate.

    Raises:
        ValidationError: If the given POS is not in the list of valid POS values.

    Returns:
        None
    """
    pos_list = [
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

    if pos not in pos_list:
        raise ValidationError(f"{pos} must be one of {pos_list}")


def validate_relation(relation):
    relations = [
        "broader concept",
        "narrower concept",
        "coordinate concept",
        "comprehensive concept",
        "partitive concept",
        "pragmatic relation",
        "unspecified",
        "synonym",  # value found in Mika Saijets 2005: Boazonamahusat
        "cohyponym",  # value found in Mika Saijets 2005: Boazonamahusat
        "hyperonym",  # value found in Mika Saijets 2005: Boazonamahusat
    ]

    if relation not in relations:
        raise ValidationError(f"{relation} is not one of {relations}")


def validate_status(status: str) -> None:
    statuses = ["recommended", "out of date", "avoid", "rare"]

    if status not in statuses:
        raise ValidationError(f"status must be one of {statuses}")


@dataclass
class ConceptInfo:
    language: str = field(metadata={"validate": validate_lang})
    definition: str | None
    explanation: str | None
    more_info: str | None

    def to_termwiki(self) -> str:
        """Converts the object to a TermWiki format string.

        Returns:
            str: The TermWiki format string.
        """
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
    note: str | None
    pos: str | None
    source: str | None
    inflection: str | None
    country: str | None
    dialect: str | None
    status: str | None = field(metadata={"validate": validate_status})
    expression: str
    language: str = field(metadata={"validate": validate_lang})
    sanctioned: str = "False"

    def to_termwiki(self) -> str:
        """Converts the object to a TermWiki formatted string.

        Returns:
            str: The TermWiki formatted string.
        """
        expression_dict = asdict(self)
        strings = ["{{Related expression"]
        strings.extend(
            [
                f"|{key}={expression_dict[key]}"
                for key in [
                    "language",
                    "expression",
                    "pos",
                    "status",
                    "sanctioned",
                    "note",
                    "source",
                    "inflection",
                    "country",
                    "dialect",
                ]
                if expression_dict[key] is not None
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
        """Converts the object to a TermWiki format string.

        Returns:
            str: The TermWiki format string.
        """
        concept_dict = asdict(self)
        strings = ["{{Related concept"]
        strings.extend(
            [
                f"|{key}={concept_dict[key]}"
                for key in ["language", "definition", "explanation", "more_info"]
                if concept_dict[key] is not None
            ]
        )
        strings.append("}}")

        return "\n".join(strings)


@dataclass
class Concept:
    collection: list[str] | None
    category: str | None
    main_category: str | None
    sources: str | None
    page_id: str | None

    def to_termwiki(self) -> str:
        """Converts the object to a TermWiki formatted string.

        Returns:
            str: The TermWiki formatted string representation of the object.
        """
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
        """Converts the object to a TermWiki formatted string.

        Returns:
            str: The TermWiki formatted string representation of the object.
        """
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


def process_content(text_iterator: Iterable[str]):
    concept = read_semantic_form(text_iterator)

    # turn collection parts into a sorted list of unique elements
    if concept.get("collection"):
        concept["collection"] = sorted(
            {collection.strip() for collection in concept["collection"].split("@@")}
        )

    return concept


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
        stripped = line.strip()
        if stripped.startswith("{{") and stripped.endswith("}}"):
            continue

        if stripped == "{{Concept info":
            concept_dict.setdefault("concept_infos", [])
            concept_dict["concept_infos"].append(read_semantic_form(text_iterator))

        if stripped == "{{Concept":
            concept_dict["concept"] = process_content(text_iterator)

        if stripped == "{{Related expression":
            concept_dict.setdefault("related_expressions", [])
            concept_dict["related_expressions"].append(
                read_semantic_form(text_iterator)
            )

        if stripped == "{{Related concept":
            concept_dict.setdefault("related_concepts", [])
            concept_dict["related_concepts"].append(read_semantic_form(text_iterator))

    return TERMWIKI_PAGE_SCHEMA.load(concept_dict)


def read_semantic_form(text_iterator):
    """Turn a template into a dict.

    Args:
        text_iterator (str_iterator): An iterator that provides the contents of the
            termwiki article.

    Returns:
        dict: A dictionary representing the semantic form of the template.
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
    """Clean up expression.

    Args:
        expression (RelatedExpression): The expression to be cleaned up.

    Returns:
        dict: The cleaned up expression.
    """
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
    """Clean up concept data.

    Args:
        concept (Concept): The concept object to be cleaned up.

    Returns:
        dict: The cleaned up concept data as a dictionary.
    """
    concept_dict = asdict(concept)

    if concept.collection:
        concept_dict["collection"] = sorted(
            {
                f"Collection:{collection.strip()}"
                if "Collection:" not in collection
                else collection.strip()
                for collection in concept_dict["collection"]
            }
        )

    return concept_dict


def cleanup_termwiki_page(termwiki_page: TermWikiPage) -> TermWikiPage:
    """Cleans up a TermWikiPage object by applying cleanup functions to its attributes.

    Args:
        termwiki_page (TermWikiPage): The TermWikiPage object to be cleaned up.

    Returns:
        TermWikiPage: The cleaned up TermWikiPage object.
    """
    termwiki_page_dict = asdict(termwiki_page)
    termwiki_page_dict["concept"] = cleanup_concept(termwiki_page.concept)
    termwiki_page_dict["related_expressions"] = [
        cleanup_expression(expression)
        for expression in termwiki_page.related_expressions
    ]

    return TERMWIKI_PAGE_SCHEMA.load(termwiki_page_dict)


def validate_langs(languages: list[str]) -> None:
    """Validates a list of languages against the valid languages.

    Args:
        languages (list[str]): The list of languages to validate.

    Raises:
        ValidationError: If any language in the list is not among the valid languages.
    """
    for language in languages:
        if language not in LANGUAGES.values():
            raise ValidationError(
                f"{language} not among the valid languages: {LANGUAGES.values()}"
            )


def validate_collection_name(name: str) -> None:
    """Validates the collection name.

    The collection name must start with 'Collection:' and should not contain any '/'.

    Args:
        name (str): The collection name to be validated.

    Raises:
        ValidationError: If the collection name does not meet the validation criteria.
    """
    if not (name.startswith("Collection:") and "/" not in name):
        raise ValidationError(
            f"Name must start with 'Collection:' and contain no '/' {name}"
        )


@dataclass
class Collection:
    name: str = field(metadata={"validate": validate_collection_name})
    info: list[str] | None
    owner: str
    languages: list[str] = field(metadata={"validate": validate_langs})

    def to_termwiki(self) -> str:
        """Converts the object to a TermWiki formatted string.

        Returns:
            str: The TermWiki formatted string.
        """
        strings = self.info if self.info else []
        strings.append("\n{{Collection")
        strings.append(f"|languages={', '.join(self.languages)}")
        strings.append("}}")
        strings.append(f"\n[[Kategoriija:{self.owner}]]")

        return "\n".join(strings)


COLLECTION_SCHEMA = marshmallow_dataclass.class_schema(Collection)()
