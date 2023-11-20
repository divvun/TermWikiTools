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
"""Bot to fix syntax blunders in termwiki articles."""
import collections
import os
import re
import sys

import click

# import hfst
import mwclient
import requests
import unidecode
import yaml
from lxml import etree

from termwikitools import read_termwiki

XI_NAMESPACE = "http://www.w3.org/2001/XInclude"
XML_NAMESPACE = "https://www.w3.org/XML/1998/namespace"
XI = "{%s}" % XI_NAMESPACE
XML = "{%s}" % XML_NAMESPACE
NSMAP = {"xi": XI_NAMESPACE, "xml": XML_NAMESPACE}
NAMESPACES = [
    "Beaivválaš giella",
    "Boazodoallu",
    "Dihtorteknologiija ja diehtoteknihkka",
    "Dáidda ja girjjálašvuohta",
    "Eanandoallu",
    "Education",
    "Ekologiija ja biras",
    "Ekonomiija ja gávppašeapmi",
    "Geografiija",
    "Gielladieđa",
    "Gulahallanteknihkka",
    "Guolástus",
    "Huksenteknihkka",
    "Juridihkka",
    "Luonddudieđa ja matematihkka",
    "Medisiidna",
    "Mášenteknihkka",
    "Ođđa sánit",
    "Servodatdieđa",
    "Stáda almmolaš hálddašeapmi",
    "Religion",
    "Teknihkka industriija duodji",
    "Álšateknihkka",
    "Ásttoáigi ja faláštallan",
    "Ávnnasindustriija",
]

LANGS = {
    "eng": "en",
    "fin": "fi",
    "sme": "se",
    "sma": "sma",
    "smn": "smn",
    "sms": "sms",
    "swe": "sv",
    "nob": "nb",
    "nno": "nn",
    "lat": "lat",
    "smj": "smj",
}

ATTS = re.compile(r"@[^@]+@")


def list_recent_changes(amount):
    namespaces = "|".join(
        str(i)
        for i in [
            1102,
            1202,
            1210,
            1218,
            1226,
            1234,
            1242,
            1250,
            1258,
            1266,
            1274,
            1282,
            1290,
            1298,
            1306,
            1314,
            1322,
            1330,
            1338,
            1346,
            1354,
            1362,
            1364,
            1366,
            1368,
            1370,
            1373,
            1382,
            1384,
            1386,
        ]
    )

    session = requests.Session()

    url = "https://satni.uit.no/termwiki/api.php"

    params = {
        "format": "json",
        "rcprop": "title",
        "list": "recentchanges",
        "action": "query",
        "rcnamespace": namespaces,
        "rclimit": amount,
        "rcexcludeuser": "SDTermImporter",
    }

    request = session.get(url=url, params=params)
    data = request.json()

    recentchanges = data["query"]["recentchanges"]

    return sorted([title for title in {rc["title"] for rc in recentchanges}])


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

    def save_concept(self, tw_concept: read_termwiki.Concept, main_title: str) -> None:
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
    def pages(self):
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
    def content_elements(self):
        """Get concept elements found in dump.xml.

        Yields:
            etree.Element: the content element found in a page element.
        """
        for title, page, page_id in self.pages:
            content_elt = page.find(".//{}text".format(self.mediawiki_ns))
            if content_elt.text and "{{Concept" in content_elt.text:
                yield title, content_elt, page_id

    @property
    def concepts(self):
        """Get concepts found in dump.xml.

        Yields:
            read_termwiki.Concept: the content element found in a page element.
        """
        for title, content_elt, _ in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            yield title, concept

    def expressions(self, **kwargs):
        """All expressions found in dumphandler."""
        return (
            (title, expression)
            for title, concept in self.concepts
            for expression in concept.related_expressions
            if all(expression[key] == value for key, value in kwargs.items())
        )

    def dump2xml(self):
        l2l = {
            "en": "eng",
            "fi": "fin",
            "nb": "nob",
            "nn": "nno",
            "se": "sme",
            "sv": "swe",
        }
        roots = {}
        for title, concept in self.concepts:
            category = title.split(":")[0]
            if roots.get(category) is None:
                print(f"registering category: {category}")
                roots[category] = etree.Element("r")
            r = roots.get(category)
            data = concept.data
            mlc = etree.SubElement(r, "mc", attrib={"name": title})
            if concept.get("page_id"):
                mlc.set("pageid", concept.get("page_id"))
            for collection in concept.get("collection", []):
                col = etree.SubElement(mlc, "collection")
                col.text = collection
            for lang in concept.languages():
                if lang in [
                    related_expression.get("language")
                    for related_expression in data["related_expressions"]
                ]:
                    c = etree.SubElement(mlc, "c", attrib={"lang": l2l.get(lang, lang)})
                    for concept_info in data["concept_infos"]:
                        if concept_info.get("language", "uff") == lang:
                            if concept_info.get("definition"):
                                d = etree.SubElement(c, "d")
                                d.text = concept_info.get("definition")
                            if concept_info.get("explanation"):
                                e = etree.SubElement(c, "e")
                                e.text = concept_info.get("explanation")
                            if concept_info.get("more_info"):
                                m = etree.SubElement(c, "m")
                                m.text = concept_info.get("more_info")
                    for related_expression in data["related_expressions"]:
                        if related_expression.get("language") == lang:
                            term = etree.SubElement(
                                c,
                                "term",
                                attrib={
                                    "sanctioned": "true"
                                    if related_expression.get("sanctioned") == "True"
                                    else "false"
                                },
                            )
                            if related_expression.get("status"):
                                term.set("status", related_expression.get("status"))

                            # print(related_expression)
                            lemma = etree.SubElement(term, "l")
                            lemma.text = related_expression.get("expression")

                            if related_expression.get("pos"):
                                lemma.set("pos", related_expression.get("pos"))

                            for tag in ["note", "source"]:
                                if related_expression.get(tag):
                                    a = etree.SubElement(term, tag)
                                    a.text = related_expression.get(tag)
            if not mlc.xpath("./c"):
                print("no c")
                print(etree.tostring(mlc, encoding="unicode"))
                mlc.getparent().remove(mlc)

        for category, root in roots.items():
            asciiname = unidecode.unidecode(category).replace(" ", "_").lower()
            print(f"{category}")
            with open(f"{asciiname}.xml", "w") as term_:
                print(
                    etree.tostring(root, encoding="unicode", pretty_print=True),
                    file=term_,
                )

    def not_found_in_normfst(self, **kwargs):
        """Return expressions not found in normfst."""
        analyser_lang = "sme" if kwargs["language"] == "se" else kwargs["language"]
        not_founds = collections.defaultdict(set)
        norm_analyser = hfst.HfstInputStream(
            f"/usr/share/giella/{analyser_lang}/analyser-gt-norm.hfstol"
        ).read()

        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(**kwargs):
            for real_expression1 in expression["expression"].split():
                for real_expression in real_expression1.split("/"):
                    for invalid in [
                        "(",
                        ")",
                        ",",
                        "?",
                        "+",
                        "*",
                        "[",
                        "]",
                        "=",
                        ";",
                        ":",
                        "!",
                    ]:
                        real_expression = real_expression.replace(invalid, "")
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
    def known_to_descfst(language, not_in_norms):
        analyser_lang = "sme" if language == "se" else language
        desc_analyser = hfst.HfstInputStream(
            f"/usr/share/giella/{analyser_lang}/analyser-gt-desc.hfstol"
        ).read()
        founds = collections.defaultdict(dict)

        for real_expression in not_in_norms:
            analyses = {
                ATTS.sub("", analysis[0])
                for analysis in desc_analyser.lookup(real_expression)
            }
            without_cmp = {analysis for analysis in analyses if "+Cmp#" not in analysis}
            if analyses:
                founds[real_expression]["analyses"] = (
                    without_cmp if without_cmp else analyses
                )
                founds[real_expression]["sources"] = [
                    source for source in sorted(not_in_norms[real_expression])
                ]

        return founds

    def print_missing(self, **kwargs):
        """Find all expressions of the given language.

        Args:
            language (src): language of the terms.
        """

        def revsorted_expressions(not_founds):
            return [
                reverted[::-1]
                for reverted in sorted([not_found[::-1] for not_found in not_founds])
            ]

        not_in_norms = self.not_found_in_normfst(**kwargs)

        descriptives = self.known_to_descfst(kwargs["language"], not_in_norms)
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

    def sum_terms(self, language=None):
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        counter = collections.defaultdict(int)
        for _, concept in self.concepts:
            for expression in concept.related_expressions:
                if expression["language"] == language:
                    counter[expression["sanctioned"]] += 1

        print(
            "{}:\nSanctioned:\t{}\nNot-sanctioned:\t{}\nTotal:\t\t{}".format(
                language,
                counter["True"],
                counter["False"],
                counter["False"] + counter["True"],
            )
        )

    def print_invalid_chars(self, language, sanctioned):
        """Find terms with invalid characters, print the errors to stdout."""
        invalid_chars_re = re.compile(r"[()[\]?:;+*=]")
        base_url = "https://satni.uit.no/termwiki"
        for title, expression in self.expressions(
            language=language, sanctioned=sanctioned
        ):
            if invalid_chars_re.search(expression["expression"]):
                print(
                    f'{expression["expression"]} {base_url}/index.php?title={title.replace(" ", "_")}'
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
                        if (
                            expression["language"] == lang1
                            or expression["language"] == lang2
                        ):
                            if expression["sanctioned"] == "True":
                                langs[expression["language"]].add(
                                    expression["expression"]
                                )

                    if langs[lang1] and langs[lang2]:
                        for expression in langs[lang1]:
                            print("{}\t{}".format(expression, ", ".join(langs[lang2])))

    @staticmethod
    def get_site():
        """Get a mwclient site object.

        Returns:
            mwclient.Site
        """
        config_file = os.path.join(os.getenv("HOME"), ".config", "term_config.yaml")
        with open(config_file) as config_stream:
            config = yaml.load(config_stream)
            site = mwclient.Site("satni.uit.no", path="/termwiki/")
            site.login(config["username"], config["password"])

            print("Logging in to query …")

            return site

    def statistics(self, language):
        invalid_chars_re = re.compile(r"[()[\]?:;+*=]")
        counter = {}
        for title, concept in self.concepts:
            if any(
                [
                    expression["language"] == language
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
                    if expression["language"] == language
                ]
                counter[category]["expressions"] += len(expression_with_lang)
                counter[category]["true_expressions"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if expression["sanctioned"] == "True"
                    ]
                )
                counter[category]["false_expressions"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if expression["sanctioned"] == "False"
                    ]
                )
                counter[category]["invalid"] += len(
                    [
                        expression
                        for expression in expression_with_lang
                        if invalid_chars_re.search(expression["expression"])
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
    def content_elements(self, verbose=False):
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
    def save_page(page, content, summary):
        """Save a given TermWiki page.

        Args:
            content (str): the new content to be saved.
            summary (str): the commit message.
        """
        try:
            page.save(content, summary=summary)
        except mwclient.errors.APIError as error:
            print(page.name, content, str(error), file=sys.stderr)

    def delete_redirects(self):
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

    def add_id(self):
        dump = DumpHandler()
        for title, content_elt, page_id in dump.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            if not concept.concept.get("page_id"):
                page = self.site.Pages[title]
                real_concept = read_termwiki.Concept()
                real_concept.from_termwiki(page.text)
                real_concept.concept["page_id"] = page_id
                print(f"Adding {page_id} to {title}")
                page.save(str(real_concept), summary="Added id")

    def make_related_expression_dict(self, dump):
        related_expression_dict = collections.defaultdict(set)
        for _, concept in dump.concepts:
            for expression_title in concept.related_expressions:
                related_expression_dict[
                    f'Expression:{expression_title["expression"].replace("&amp;", "&")}'
                ].add(expression_title["language"])

        return related_expression_dict

    def make_dump_expression_dict(self, dump):
        namespace = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}
        return {
            expression_xml.text: expression_xml.getparent()
            .xpath(".//mw:text", namespaces=namespace)[0]
            .text
            for expression_xml in dump.tree.getroot().xpath(
                './/mw:title[starts-with(text(), "Expression:")]', namespaces=namespace
            )
        }

    def make_expression_pages(self, related_expression_dict, dump_expression_dict):
        for expression_title, languages in related_expression_dict.items():
            ideal_content = self.make_expression_content(languages)
            if ideal_content != dump_expression_dict.get(expression_title):
                print(f"fixing {expression_title}")
                print("ideal", ideal_content)
                print("from dump", dump_expression_dict.get(expression_title))
                print()
                self.fix_expression_page(expression_title, content=ideal_content)

    def delete_expression_pages(self, related_expression_dict, dump_expression_dict):
        related_expressions = {title for title in related_expression_dict.keys()}
        dump_expressions = {title for title in dump_expression_dict.keys()}

        for to_delete in related_expressions - dump_expressions:
            page = self.site.Pages[to_delete]
            if page.exists:
                print(f"Removing {to_delete}")
                page.delete(reason="Is not found among related expressions")

    def fix_expression_pages(self):
        dump = DumpHandler()
        related_expression_dict = self.make_related_expression_dict(dump=dump)
        dump_expression_dict = self.make_dump_expression_dict(dump=dump)

        self.make_expression_pages(related_expression_dict, dump_expression_dict)
        self.delete_expression_pages(related_expression_dict, dump_expression_dict)

    def fix_expression_page(self, expression_title, content):
        page = self.site.Pages[expression_title]
        if not page.exists:
            self.save_page(page, content=content, summary="Making new expression page")
        else:
            if page.text != content:
                print("\treally fixing", expression_title)
                self.save_page(page, content=content, summary="Fixing expression page")

    def make_expression_content(self, languages):
        strings = []
        for language in sorted(languages):
            strings.append("{{Expression")
            strings.append(f"|language={language}")
            strings.append("}}")
        content = "\n".join(strings)
        return content

    def delete_pages(self, part_of_title):
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

    def fix(self):
        """Make the bot fix all pages."""
        counter = collections.defaultdict(int)

        for page in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(page.text())
            if concept.related_expressions:
                self.save_page(page, str(concept), summary="Fixing content")

        for key in sorted(counter):
            print(key, counter[key])

    def fix_name(self, title):
        """Make the bot fix a named page."""
        page = self.site.pages[title]

        if page.exists:
            concept = read_termwiki.Concept()
            concept.from_termwiki(page.text())
            if concept.related_expressions:
                print(f"Fixing: {title}")
                self.save_page(page, str(concept), summary="Fixing content")

                for expression in concept.related_expressions:
                    expression_title = (
                        f'Expression:{expression["expression"].replace("&amp;", "&")}'
                    )

                    expression_page = self.site.pages[expression_title]
                    if not expression_page.exists:
                        self.make_expression_page(expression)
        else:
            print(f"page {title} does not exist")

    def make_expression_page(self, expression):
        title = f'Expression:{expression["expression"]}'
        try:
            expression_page = self.site.Pages[title]
            print(f"Trying to make {title}", end=" ")
            if not expression_page.exists:
                strings = []
                strings.append("{{Expression")
                strings.append(f"|{'language'}={expression['language']}")
                strings.append("}}")
                expression_page.save("\n".join(strings), summary="Created by termbot")
                print("succeeded")
            else:
                print("already exists")
        except mwclient.errors.InvalidPageTitle:
            print(f"Invalid title {title}")

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


@click.group()
def main():
    """Fix site or extract data from local copy of TermWiki."""
    pass


@main.group()
def dump():
    """Extract data from local copy of TermWiki."""
    pass


@dump.command()
def xml():
    """Dump the TermWiki database to XML files."""
    dumphandler = DumpHandler()
    dumphandler.dump2xml()


@dump.command()
@click.argument(
    "language",
    type=click.Choice(LANGS.keys()),
)
@click.option(
    "--sanctioned",
    is_flag=True,
    help="Sanctioned status for GG.",
)
def missing(language, sanctioned):
    """Print missing terms for a language."""
    dumphandler = DumpHandler()
    dumphandler.print_missing(sanctioned=sanctioned, language=language)


@dump.command()
def collection():
    """Find collections in the dump."""
    dumphandler = DumpHandler()
    dumphandler.find_collections()


@dump.command()
@click.argument("language", type=click.Choice(LANGS.keys()))
@click.option("--sanctioned", is_flag=True, help="Sanctioned status for GG.")
def invalid(language, sanctioned):
    """Print invalid characters for a language."""
    dumphandler = DumpHandler()
    dumphandler.print_invalid_chars(
        language=LANGS[language], sanctioned="True" if sanctioned else "False"
    )


@dump.command()
@click.argument("language", type=click.Choice(LANGS.keys()))
def sum(language):
    """Sum the number of terms for a language."""
    dumphandler = DumpHandler()
    dumphandler.sum_terms(language=LANGS[language])


@dump.command()
@click.argument("languages", nargs=-1, type=click.Choice(LANGS.keys()), required=True)
def statistics(languages):
    """Print statistics for one or more languages."""
    dumphandler = DumpHandler()
    for language in languages:
        dumphandler.statistics(language=LANGS[language])


@dump.command()
def sort():
    """Sort the dump."""
    dumphandler = DumpHandler()
    dumphandler.sort_dump()


@dump.command()
@click.argument("source", type=click.Choice(LANGS.keys()))
@click.argument("target", type=click.Choice(LANGS.keys()))
@click.option(
    "--category",
    type=click.Choice([namespace.replace(" ", "_") for namespace in NAMESPACES]),
    help="Choose category",
)
def pairs(source, target, category):
    """Print expression pairs for two languages."""
    dumphandler = DumpHandler()
    dumphandler.print_expression_pairs(
        lang1=LANGS[source], lang2=LANGS[target], category=category.replace("_", " ")
    )


@main.group()
def site():
    pass


@site.command()
def fix():
    """Fix all Concept pages on the TermWiki."""
    site_handler = SiteHandler()
    site_handler.fix()


@site.command()
def rev():
    site_handler = SiteHandler()
    site_handler.fix_revisions()


@site.command()
def revert():
    site_handler = SiteHandler()
    site_handler.revert()


@site.command()
def query():
    site_handler = SiteHandler()
    site_handler.add_extra_collection()


@site.command()
def fix_expression_pages():
    """Fix expression pages."""
    site_handler = SiteHandler()
    site_handler.fix_expression_pages()


@site.command()
def delete_redirects():
    """Delete redirects on the TermWiki, they are not needed."""
    site_handler = SiteHandler()
    site_handler.delete_redirects()


@site.command()
def add_id():
    """Add permanent id to Concept pages on the TermWiki"""
    site_handler = SiteHandler()
    site_handler.add_id()


@site.command()
def improve_pagenames():
    """Improve page names on the TermWiki"""
    site_handler = SiteHandler()
    site_handler.improve_pagenames()


@site.command()
@click.argument("substring")
def delete_pages(substring):
    """Delete pages containing the substring from the TermWiki."""
    site_handler = SiteHandler()
    site_handler.delete_pages(substring)


@site.command()
@click.option("--amount", default=10, help="The number of recent changes to fix")
def fixrecent(amount):
    """Fix recently changed Concept pages on the TermWiki."""
    site_handler = SiteHandler()
    for title in list_recent_changes(amount):
        site_handler.fix_name(title)
