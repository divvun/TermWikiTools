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
#   Copyright © 2023 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#

from dataclasses import dataclass
from typing import Any

import marshmallow_dataclass

from termwikitools.handler_common import LANGUAGES
from termwikitools.read_termwiki import TermWikiPage


@dataclass
class Algu:
    word_id: str
    lexeme_id: str | None


@dataclass
class Lemma:
    pos: str | None
    lemma: str
    country: str | None
    dialect: str | None
    algu: Algu | None


@dataclass
class Term:
    status: str | None
    sanctioned: bool
    note: str | None
    source: str | None
    expression: Lemma


@dataclass
class Concept:
    language: str
    definition: str | None
    explanation: str | None
    terms: list[Term]


@dataclass
class SatniConcept:
    name: str
    collections: list[str] | None
    concepts: list[Concept]


SATNI_CONCEPT_SCHEMA = marshmallow_dataclass.class_schema(SatniConcept)()


def termwikipage_to_satniconcept(termwikipage: TermWikiPage) -> SatniConcept:
    satniconcept_dict: dict[str, Any] = {}
    satniconcept_dict["name"] = termwikipage.title
    if termwikipage.concept:
        satniconcept_dict["collections"] = termwikipage.concept.collection

    satniconcept_dict["concepts"] = make_satniconcepts(termwikipage)

    return SATNI_CONCEPT_SCHEMA.load(satniconcept_dict)


def make_satniconcepts(termwikipage: TermWikiPage) -> list[dict]:
    concepts = []
    terms_by_language = make_terms_by_language(termwikipage)
    for language in terms_by_language:
        concept = {
            "language": language,
            "terms": terms_by_language[language]["terms"],
        }
        if termwikipage.concept_infos:
            for termwikipage_concept_info in termwikipage.concept_infos:
                if (
                    termwikipage_concept_info.language == LANGUAGES[language]
                ):  #  termwikipage_concept_info.language is iso 639-2
                    concept["definition"] = termwikipage_concept_info.definition
                    concept["explanation"] = termwikipage_concept_info.explanation
        concepts.append(concept)

    return concepts


def make_terms_by_language(termwikipage: TermWikiPage) -> dict:
    reversed_lang = {value: key for key, value in LANGUAGES.items()}
    terms_by_language: dict[str, Any] = {}
    for related_expression in termwikipage.related_expressions:
        if related_expression.sanctioned == "True":
            language = reversed_lang[
                related_expression.language
            ]  # iso 639-2 to iso-639-3
            if not terms_by_language.get(language):
                terms_by_language[language] = {}
                terms_by_language[language]["terms"] = []
            terms_by_language[language]["terms"].append(
                {
                    "status": related_expression.status,
                    "sanctioned": related_expression.status == "True",
                    "note": related_expression.note,
                    "source": related_expression.source,
                    "expression": {
                        "lemma": related_expression.expression,
                        "pos": related_expression.pos,
                        "country": related_expression.country,
                        "dialect": related_expression.dialect,
                    },
                }
            )

    return terms_by_language
