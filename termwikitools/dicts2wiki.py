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
"""Functions to import and export giella xml dicts to the TermWiki."""
import collections
import glob
import os
import sys

from lxml import etree


def valid_xmldict():
    """Parse xml dictionaries."""
    for pair in [
        "finsme",
        "finsmn",
        "nobsma",
        "nobsme",
        "nobsmj",
        "nobsmj",
        "smafin",
        "smanob",
        "smasme",
        "smefin",
        "smenob",
        "smesma",
        "smesmj",
        "smesmn",
        "smjnob",
        "smjsme",
        "smnsme",
        "swesma",
    ]:
        dict_root = os.path.join(os.getenv("GTHOME"), "words/dicts", pair, "src")
        for xml_file in glob.glob(dict_root + "/*.xml"):
            if not xml_file.endswith("meta.xml") and "Der_" not in xml_file:
                # TODO: handle Der_ files
                try:
                    parser = etree.XMLParser(remove_comments=True, dtd_validation=True)
                    dictxml = etree.parse(xml_file, parser=parser)

                    origlang = dictxml.getroot().get(
                        "{http://www.w3.org/XML/1998/namespace}lang"
                    )
                    if origlang != pair[:3]:
                        raise SystemExit(
                            "{}: origlang {} in the file does not match "
                            "the language in the filename {}".format(
                                xml_file, origlang, pair[:3]
                            )
                        )

                    dict_id = dictxml.getroot().get("id")
                    if pair != dict_id:
                        raise SystemExit(
                            "{}: language pair in the file does not match "
                            "the one given in the filename {}".format(
                                xml_file, dict_id, pair
                            )
                        )

                    yield dictxml, xml_file
                except etree.XMLSyntaxError as error:
                    print(
                        "Syntax error in {} "
                        "with the following error:\n{}\n".format(xml_file, error),
                        file=sys.stderr,
                    )


def parse_dicts() -> collections.defaultdict:
    """Extract xml dictionaries to a dict."""

    for dictxml, xml_file in valid_xmldict():

        with open(xml_file, "wb") as xml_stream:
            xml_stream.write(
                etree.tostring(
                    dictxml, encoding="UTF-8", pretty_print=True, xml_declaration=True
                )
            )


def main() -> None:
    """Parse the xml dictionaries."""
    parse_dicts()
