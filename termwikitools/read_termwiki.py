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
#   Copyright © 2016-2019 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Read termwiki pages."""

import inspect
from operator import itemgetter

# from termwikitools import check_tw_expressions
from termwikitools.ordereddefaultdict import OrderedDefaultDict

XI_NAMESPACE = "http://www.w3.org/2001/XInclude"
XML_NAMESPACE = "https://www.w3.org/XML/1998/namespace"
XI = "{%s}" % XI_NAMESPACE
XML = "{%s}" % XML_NAMESPACE
NSMAP = {"xi": XI_NAMESPACE, "xml": XML_NAMESPACE}


def lineno():
    """Return the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def fix_sms(expression: str) -> str:
    """Replace invalid accents with valid ones for the sms language.

    * u2019: RIGHT SINGLE QUOTATION MARK
    * u0027: APOSTROPHE
    * u2032: PRIME
    * u00B4: ACUTE ACCENT
    * u0301: COMBINING ACUTE ACCENT
    * u02BC: MODIFIER LETTER APOSTROPHE
    * u02B9: MODIFIER LETTER PRIME

    Args:
        expression: a string to check for sms letters

    Returns:
        A string containing proper sms letters
    """
    replacement_pairs = [
        ("\u2019", "\u02BC"),
        ("\u0027", "\u02BC"),
        ("\u2032", "\u02B9"),
        ("\u00B4", "\u02B9"),
        ("\u0301", "\u02B9"),
    ]

    for replacement_pair in replacement_pairs:
        expression = expression.replace(replacement_pair[0], replacement_pair[1])

    return expression


class Concept(object):
    """Class that represents a TermWiki concept."""

    def __init__(self):
        """Initialise the Concept class."""
        self.title = ""
        self.data = {
            "concept": {},
            "concept_infos": [],
            "related_expressions": [],
            "related_concepts": [],
        }

    @property
    def related_expressions(self):
        """Get related_expressions."""
        return self.data["related_expressions"]

    @property
    def collections(self):
        """Get collections."""
        if not self.data["concept"].get("collection"):
            self.data["concept"]["collection"] = set()
        return self.data["concept"].get("collection")

    def clean_up_concept(self):
        """Clean up concept data."""
        if self.data["concept"].get("language"):
            del self.data["concept"]["language"]
        if self.data["concept"].get("collection"):
            self.data["concept"]["collection"] = set(
                [
                    self.fix_collection_line(collection.strip())
                    for collection in self.data["concept"]["collection"].split("@@")
                ]
            )

    def clean_up_expression(self, expression):
        """Clean up expression."""
        if "expression" in expression:
            expression["expression"] = " ".join(expression["expression"].split())

            if (
                "sanctioned" in expression and expression["sanctioned"] == "No"
            ) or "sanctioned" not in expression:
                expression["sanctioned"] = "False"
            if "sanctioned" in expression and expression["sanctioned"] == "Yes":
                expression["sanctioned"] = "True"

            if " " in expression["expression"]:
                expression["pos"] = "MWE"

            if "collection" in expression:
                if not self.data.get("collection"):
                    self.data["concept"]["collection"] = set()
                self.data["concept"]["collection"].add(
                    expression["collection"].replace("_", " ")
                )
                del expression["collection"]

            if expression["language"] == "sms":
                expression["expression"] = fix_sms(expression["expression"])

            if expression.get("pos") in ["A/N", "N/A", "xxx"]:
                del expression["pos"]

            if expression.get("pos") in ["mwe", "a", "n", "v"]:
                expression["pos"] = expression["pos"].upper()

            if expression.get("pos") == "Adj":
                expression["pos"] = "A"

            # if expression.get('pos') is None:
            # possible_pos = check_tw_expressions.set_pos(expression)
            # if possible_pos is not None:
            # expression['pos'] = possible_pos

            self.data["related_expressions"].append(expression)

    def from_termwiki(self, text):
        """Parse a termwiki page.

        Args:
            text (str): content of the termwiki page.
            counter (collections.defaultdict(int)): keep track of things

        Returns:
            dict: contains the content of the termwiki page.
        """
        text_iterator = iter(text.replace("\xa0", " ").splitlines())

        for line in text_iterator:
            line = line.strip()
            if self.is_empty_template(line):
                continue

            elif line.startswith("{{Concept info"):
                self.data["concept_infos"].append(
                    self.read_semantic_form(text_iterator)
                )

            elif line.startswith("{{Concept"):
                self.data["concept"] = self.read_semantic_form(text_iterator)
                self.clean_up_concept()

            elif self.is_related_expression(line):
                expression = self.read_semantic_form(text_iterator)
                self.clean_up_expression(expression)

            elif line.startswith("{{Related"):
                self.data["related_concepts"].append(
                    self.read_semantic_form(text_iterator)
                )

        self.to_concept_info()

    def to_concept_info(self):
        """Turn old school Concept to new school Concept.

        Args:
            term (dict): A representation of a TermWiki Concept
        """
        langs = {}
        concept = {}
        concept.update(self.data["concept"])

        if concept:
            for key in list(concept.keys()):
                pos = key.rfind("_")
                if pos > 0:
                    lang = key[pos + 1 :]
                    if lang in [
                        "se",
                        "sv",
                        "fi",
                        "en",
                        "nb",
                        "nn",
                        "sma",
                        "smj",
                        "smn",
                        "sms",
                        "lat",
                    ]:
                        if not langs.get(lang):
                            langs[lang] = {}
                            langs[lang]["language"] = lang
                        new_key = key[:pos]
                        langs[lang][new_key] = concept[key]
                        del concept[key]

        self.data["concept"] = concept
        for lang in langs:
            self.data["concept_infos"].append(langs[lang])

    @staticmethod
    def read_semantic_form(text_iterator):
        """Turn a template into a dict.

        Args:
            text_iterator (str_iterator): the contents of the termwiki article.

        Returns:
            importer.OrderedDefaultDict
        """
        wiki_form = OrderedDefaultDict()
        wiki_form.default_factory = str
        for line in text_iterator:
            if line == "}}":
                return wiki_form
            elif (
                line.startswith("|reviewed=")
                or line.startswith("|is_typo")
                or line.startswith("|has_illegal_char")
                or line.startswith("|in_header")
                or line.startswith("|no picture")
            ):
                pass
            elif line.startswith("|"):
                equality = line.find("=")
                key = line[1:equality]
                if line[equality + 1 :]:
                    wiki_form[key] = line[equality + 1 :].strip()
            else:
                try:
                    wiki_form[key] = "\n".join([wiki_form[key], line.strip()])
                except UnboundLocalError:
                    pass

    @staticmethod
    def is_empty_template(line):
        """Check if a line represents an empty template."""
        return (
            line == "{{Related expression}}"
            or line == "{{Concept info}}"
            or line == "{{Concept}}"
        )

    @staticmethod
    def fix_collection_line(line):
        """Add Collection: to collection line if needed.

        Args:
            line (str): a line found in a termwiki page.

        Returns:
            str
        """
        if "Collection:" not in line:
            return "{}:{}".format("Collection", line)
        else:
            return line

    @staticmethod
    def is_related_expression(line):
        """Check if line is the start of a TermWiki Related expression.

        Args:
            line (str): TermWiki line

        Returns:
            bool
        """
        return line.startswith("{{Related expression") or line.startswith(
            "{{Related_expression"
        )

    def concept_info_str(self, term_strings):
        """Append concept_info to a list of strings."""
        for concept_info in sorted(
            self.data["concept_infos"], key=itemgetter("language")
        ):
            term_strings.append("{{Concept info")
            for key in ["language", "definition", "explanation", "more_info"]:
                if concept_info.get(key):
                    term_strings.append("|{}={}".format(key, concept_info[key]))
            term_strings.append("}}")

    def languages(self):
        return {
            concept_info["language"]
            for concept_info in self.data["concept_infos"]
            for key in concept_info
            if key == "language" and concept_info["language"]
        } | {
            expression["language"]
            for expression in self.related_expressions
            if expression["language"]
        }

    def concept_info_of_langauge(self, language):
        for concept_info in self.data["concept_infos"]:
            for key in concept_info:
                if key == "language" and concept_info[key] == language:
                    return concept_info

    def related_expressions_str(self, term_strings):
        """Append related_expressions to a list of strings."""
        for expression in self.related_expressions:
            term_strings.append("{{Related expression")
            for key, value in expression.items():
                term_strings.append("|{}={}".format(key, value))
            term_strings.append("}}")

    def related_concepts_str(self, term_strings):
        """Append related_concepts to a list of strings."""
        if self.data.get("related_concepts"):
            for related_concept in self.data["related_concepts"]:
                term_strings.append("{{Related concept")
                for key, value in related_concept.items():
                    term_strings.append("|{}={}".format(key, value))
                term_strings.append("}}")

    def concept_str(self, term_strings):
        """Append concept to a list of strings."""
        if self.data["concept"]:
            term_strings.append("{{Concept")
            for key, value in self.data["concept"].items():
                if key == "collection" and value:
                    term_strings.append("|{}={}".format(key, "@@ ".join(sorted(value))))
                else:
                    term_strings.append("|{}={}".format(key, value))
            term_strings.append("}}")
        else:
            term_strings.append("{{Concept}}")

    def __str__(self):
        """Turn a term dict into a semantic wiki page.

        Args:
            term (dict): the result of clean_up_concept

        Returns:
            str: term formatted as a semantic wiki page.
        """
        term_strings = []
        self.concept_info_str(term_strings)
        self.related_expressions_str(term_strings)
        self.related_concepts_str(term_strings)
        self.concept_str(term_strings)

        return "\n".join(term_strings)

    @property
    def category(self):
        colon = self.title.find(":")
        return self.title[:colon]

    def auto_sanction(self, language):
        """Automatically sanction expressions in the given language.

        Args:
            language (str): the language to handle
        """
        for expression in self.related_expressions:
            if expression["language"] == language:
                if (
                    analyser.is_known(language, expression["expression"])
                    and expression["sanctioned"] == "False"
                ):
                    expression["sanctioned"] = "True"

    def has_invalid(self):
        """Print lemmas with invalid characters."""
        for expression in self.related_expressions:
            if expression["sanctioned"] == "True" and "(" in expression["expression"]:
                return True
        else:
            return False

    def find_invalid(self, language, sanctioned):
        """Find expressions with invalid characters.

        Args:
            language (str): the language of the expressions

        Yields:
            str: an offending expression
        """
        for expression in self.related_expressions:
            if (
                expression["language"] == language
                and expression["sanctioned"] == sanctioned
            ):
                if self.invalid_chars_re.search(expression["expression"]):
                    yield expression["expression"]

    def has_sanctioned_sami(self):
        for expression in self.related_expressions:
            if (
                expression["language"] in ["se", "sma", "smj", "smn", "sms"]
                and expression["sanctioned"] == "True"
            ):
                return True

        return False