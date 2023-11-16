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
#   Copyright © 2018 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Make SMW pages from lexc files.

The formats should be:

The format of a Contlex page
{{Continuation lexicon
|Contlex name=JOHTOLAT
|Language=se
|Pos=N
}}

The name of Contlex page:
Contlex:<Language> <Pos> <Contlex name>

The format of a Stem page:
{{Stem
|Lemma=johtolat
|Contlex=se N JOHTOLAT
|Freetext=<Freetext part in lexc line>
|Comment=<The comment following the lexc line>
}}

The name of a Stem page:
Stem:<Lemma> <Contlex>
"""

import datetime
import io
import os
import re
from collections import defaultdict


WANTED_LEXICONS = {
    "sme": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["ALIT", "Eahpe_Adjective", "AdjectivePx", "AdjectiveNoPx"],
        },
        "adpositions": {
            "pos": "Adp",
            "lexicons": ["Adposition"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["Adverb"],
        },
        "conjunctions": {
            "pos": "Cc",
            "lexicons": ["CleanConjunction"],
        },
        "interjections": {
            "pos": "Interj",
            "lexicons": ["Interjection"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["HyphNouns", "Eahpe_Noun", "NounNoPx", "NounPxKin", "NounPx"],
        },
        "particles": {
            "pos": "Pcle",
            "lexicons": ["Particles"],
        },
        "subjunctions": {
            "pos": "CS",
            "lexicons": ["ConfuseConjunction", "CleanSubjunction"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["Eahpe_Verb", "Verb"],
        },
    },
    "smj": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["Adjective"],
        },
        "adpositions": {
            "pos": "Adp",
            "lexicons": ["Adposition"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["Adverb"],
        },
        "conjunctions": {
            "pos": "Cc",
            "lexicons": ["Conjunction"],
        },
        "interjections": {
            "pos": "Interj",
            "lexicons": ["Interjection"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["HyphNouns", "NounPxKin", "NounNoPx", "NounPx"],
        },
        "particles": {
            "pos": "Pcle",
            "lexicons": ["Particle"],
        },
        "subjunctions": {
            "pos": "CS",
            "lexicons": ["Subjunction"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["Verb"],
        },
    },
    "sma": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["Adjective"],
        },
        "adpositions": {
            "pos": "Adp",
            "lexicons": ["Adposition"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["Adverb"],
        },
        "conjunctions": {
            "pos": "Cc",
            "lexicons": ["Conjunction"],
        },
        "interjections": {
            "pos": "Interj",
            "lexicons": ["Interjection"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["HyphNouns", "NounPxKin", "NounNoPx"],
        },
        "particles": {
            "pos": "Pcle",
            "lexicons": ["Particle"],
        },
        "subjunctions": {
            "pos": "CS",
            "lexicons": ["Subjunction"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["Aux", "Verb"],
        },
    },
    "smn": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["AdjectiveRoot"],
        },
        "adpositions": {
            "pos": "Adp",
            "lexicons": ["Pre", "Post"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["Adverb"],
        },
        "conjunctions": {
            "pos": "Cc",
            "lexicons": ["Conjunction"],
        },
        "interjections": {
            "pos": "Interj",
            "lexicons": ["Interjection"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["Noun"],
        },
        "particles": {
            "pos": "Pcle",
            "lexicons": ["Particle"],
        },
        "subjunctions": {
            "pos": "CS",
            "lexicons": ["Subjunction"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["VGenVerbs", "Verbs"],
        },
    },
    "nob": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["AdjectiveRoot"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["Adverb"],
        },
        "conjunctions": {
            "pos": "Cc",
            "lexicons": ["Conjunction"],
        },
        "interjections": {
            "pos": "Interj",
            "lexicons": ["Interjection"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["2_letter", "3_letter", "NounRoot"],
        },
        "prepositions": {
            "pos": "Pr",
            "lexicons": ["Preposition"],
        },
        "subjunctions": {
            "pos": "CS",
            "lexicons": ["Subjunction"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["irregular-verb", "regular-verb"],
        },
    },
    "fin": {
        "adjectives": {
            "pos": "A",
            "lexicons": ["ADJECTIVE"],
        },
        "adverbs": {
            "pos": "Adv",
            "lexicons": ["ADVERB"],
        },
        "cc": {
            "pos": "Cc",
            "lexicons": ["CC"],
        },
        "cs": {
            "pos": "CS",
            "lexicons": ["CS"],
        },
        "interj": {
            "pos": "Interj",
            "lexicons": ["INTERJECTION"],
        },
        "nouns": {
            "pos": "N",
            "lexicons": ["NOUN"],
        },
        "particles": {
            "pos": "Pcle",
            "lexicons": ["PARTICLE"],
        },
        "pp": {
            "pos": "Adp",
            "lexicons": ["ADPOSITION"],
        },
        "verbs": {
            "pos": "V",
            "lexicons": ["VERB"],
        },
    },
}
"""dict: Govern which files and lexicons to extract for the given languages."""

LEXC_LINE_RE = re.compile(
    r"""
    (?P<contlex>\S+)            #  any nonspace
    (?P<translation>\s+".*")?   #  optional translation, might be empty
    \s*;\s*                     #  skip space and semicolon
    (?P<comment>!.*)?           #  followed by an optional comment
    $
""",
    re.VERBOSE | re.UNICODE,
)
"""regex: This is used to recognise a lexc line from other content."""

LEXC_CONTENT_RE = re.compile(
    r"""
    (?P<exclam>^\s*!\s*)?          #  optional comment
    (?P<content>(<.+>)|(.+))?      #  optional content
""",
    re.VERBOSE | re.UNICODE,
)
"""regex: identify more specific parts of a lexc line."""


def parse_line(old_match: dict) -> defaultdict:
    """Parse a lexc line.

    Args:
        old_match: the output of LEXC_LINE_RE.groupdict.

    Returns:
        defaultdict: The entries inside the lexc line expressed as
            a defaultdict
    """
    line_dict = defaultdict(str)

    if old_match.get("exclam"):
        line_dict["exclam"] = "!"

    line_dict["contlex"] = old_match.get("contlex")
    if old_match.get("translation"):
        line_dict["translation"] = (
            old_match.get("translation").strip().replace("%¥", "% ")
        )

    if old_match.get("comment"):
        line_dict["comment"] = old_match.get("comment").strip().replace("%¥", "% ")

    line = old_match.get("content")
    if line:
        line = line.replace("%¥", "% ")
        if line.startswith("<") and line.endswith(">"):
            line_dict["upper"] = line
        else:
            lexc_line_match = line.find(":")

            if lexc_line_match != -1:
                line_dict["upper"] = line[:lexc_line_match].strip()
                line_dict["divisor"] = ":"
                line_dict["lower"] = line[lexc_line_match + 1 :].strip()
                if line_dict["lower"].endswith("%"):
                    line_dict["lower"] = line_dict["lower"] + " "
            else:
                if line.strip():
                    line_dict["upper"] = line.strip()

    return line_dict


def line2dict(line: str) -> dict:
    """Parse a valid line.

    Args:
        line: a lexc line
    """
    line = line.replace("% ", "%¥")
    lexc_line_match = LEXC_LINE_RE.search(line)
    if lexc_line_match:
        content = lexc_line_match.groupdict()
        content.update(LEXC_CONTENT_RE.match(LEXC_LINE_RE.sub("", line)).groupdict())
        return parse_line(content)

    return {}


class FileHandler(object):
    """Turn a stem lexc file into SMW pages.

    Attributes:
        giella2termwiki: map Giella language codes to TermWiki language codes
        file2pos: map filenames to Giella part of speech codes
        filetemplate: template for lexc filenames
        lang: Giella language code
        stemfile: name of the stemfile without suffix
        contlexes: set that contains names of the continuation lexicons found
            in the stemfile
        filename: the full path to the stem lexc file
    """

    giella2termwiki = {
        "fin": "fi",
        "nob": "nb",
        "sma": "sma",
        "sme": "se",
        "smj": "smj",
        "smn": "smn",
    }

    filetemplate = os.path.join(
        os.getenv("GTHOME"), "langs/{}/src/morphology/stems/{}.lexc"
    )

    def __init__(self, lang: str, stemfile: str, outdir: str) -> None:
        """Initialise the FileHandler class.

        Args:
            lang: Giella language code.
            stemfile: name of the stemfile without suffix
        """
        self.lang = lang
        self.stemfile = stemfile
        self.contlexes = set()
        self.filename = self.filetemplate.format(lang, stemfile)
        self.outdir = outdir

    @property
    def termwikilang(self) -> str:
        """Get the language code used in TermWiki."""
        return self.giella2termwiki[self.lang]

    @property
    def termwikipos(self) -> str:
        """Return the part of speech code used in TermWiki."""
        return WANTED_LEXICONS[self.lang][self.stemfile]["pos"]

    @property
    def wanted_lexicons(self) -> list:
        """Return the wanted lexicons for this file."""
        return WANTED_LEXICONS[self.lang][self.stemfile]["lexicons"]

    def contlex_name(self, contlex: str) -> str:
        r"""Return the contlex name used in TermWiki.

        / is replaced with \ because / in page names indicates subpages in
        Mediawiki.

        Args:
            contlex: name of a continuation lexicon.
        """
        return "{} {} {}".format(
            self.termwikilang, self.termwikipos, contlex.replace("/", "\\")
        )

    @staticmethod
    def write_file(filename: str, stringlist: list) -> None:
        """Write stem and contlex wiki files."""
        if os.path.exists(filename):
            pass
            # print('{} already exists'.format(filename))
        else:
            with open(filename, "w") as file_:
                print("\n".join(stringlist), file=file_)

    def print_stem(self, lemma: str, line_dict: dict) -> None:
        """Produce the content and name of a TermWiki Stem page.

        Args:
            lemma: the lemma
            line_dict: the lexc line mapped to a dict containing the different
                parts of lexc line
        """
        stem = ["{{Stem"]
        stem.append("|Lemma={}".format(lemma))
        stem.append("|Contlex={}".format(self.contlex_name(line_dict["contlex"])))
        if line_dict["translation"]:
            stem.append("|Freetext={}".format(line_dict["translation"]))
        if line_dict["comment"]:
            stem.append("|Comment={}".format(line_dict["comment"]))
        stem.append("}}")
        stemname = "{}/Stem:{} {}".format(
            self.outdir,
            lemma.replace("/", "\\"),
            self.contlex_name(line_dict["contlex"]),
        )
        self.write_file(stemname, stem)

    def print_contlex(self, contlex: str) -> None:
        """Produce the content and name of a TermWiki Contlex page.

        Args:
            contlex: name of a continuation lexicon.
        """
        if contlex not in self.contlexes:
            self.contlexes.add(contlex)
            content = ["{{Continuation lexicon"]
            content.append("|Contlex name={}".format(contlex))
            content.append("|Language={}".format(self.termwikilang))
            content.append("|Pos={}".format(self.termwikipos))
            content.append("}}")
            contname = "{}/Contlex:{}".format(self.outdir, self.contlex_name(contlex))
            self.write_file(contname, content)

    def print_dupes(self, dupe_dict: dict) -> None:
        """Print list of duplicates.

        Only print if there is any content.
        """
        dupe_list = []

        for lemma in dupe_dict:
            if len(dupe_dict[lemma]) > 1:
                dupe_list.append(lemma)
                for line in dupe_dict[lemma]:
                    dupe_list.append("\t{}".format(line.rstrip()))

        if dupe_list:
            with io.open(
                "dupes-{}-{}.txt".format(self.termwikilang, self.termwikipos), "w"
            ) as dupefile:
                print("\n".join(dupe_list), file=dupefile)

    def parse_file(self) -> None:
        """Parse the lexc stem file."""
        dupes = defaultdict(list)

        print(self.termwikilang, self.termwikipos)
        with io.open(self.filename) as lexc:
            skip = True

            for lexc_line in lexc:
                if lexc_line.startswith("LEXICON"):
                    parts = lexc_line.split()
                    skip = parts[1] not in self.wanted_lexicons
                    continue

                if not skip and "+Err" not in lexc_line:
                    line_dict = line2dict(lexc_line.rstrip())
                    if line_dict and not line_dict["exclam"]:
                        upper = line_dict["upper"].split("+")[0].replace("%", "")
                        # if analyser.is_known(self.lang, upper):
                        if upper:
                            dupes[upper].append(lexc_line)
                            self.print_stem(upper, line_dict)
                            self.print_contlex(line_dict["contlex"])

        self.print_dupes(dupes)


def main() -> None:
    """Parse the files and lexicons as directed in WANTED_LEXICONS."""
    outdir = datetime.datetime.now().isoformat()
    os.makedirs(outdir)
    for lang in WANTED_LEXICONS:
        for stemfile in WANTED_LEXICONS[lang]:
            filehandler = FileHandler(lang, stemfile, outdir)
            filehandler.parse_file()


if __name__ == "__main__":
    main()