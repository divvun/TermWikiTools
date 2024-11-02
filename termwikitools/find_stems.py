"""Make a dict of stem:set(languages) from terms and dictionaries.

For terms, index all sanctioned lemmas of the terms.
For dictionaries, index all lemmas of the lookup lemmas. 
For the Sammallahti dictionary, index the translation lemmas as well.
"""

import glob
import os
import re
import sys
from collections import defaultdict

from lxml import etree

from termwikitools.dumphandler import DumpHandler

DICTS = [
    "fin-nob",
    "fin-sme",
    "fin-smn",
    "nob-sma",
    "nob-sme",
    "sma-nob",
    "sma-sme",
    "sme-fin",
    "sme-nob",
    "sme-sma",
    "sme-smn",
    "smn-fin",
    "smn-sme",
]

LANGS = {
    "en": "eng",
    "fi": "fin",
    "lat": "lat",
    "nb": "nob",
    "nn": "nno",
    "se": "sme",
    "sma": "sma",
    "smj": "smj",
    "smn": "smn",
    "sms": "sms",
    "sv": "swe",
}

STEMS = defaultdict(set)

REMOVER_RE = r'[ꞌ|@ˣ."*]'
"""Remove these characters from Sammallahti's original lemmas."""


def sammallahti_remover(line):
    """Remove Sammallahti's special characters."""
    return re.sub(REMOVER_RE, "", line).strip()


def sammallahti_replacer(line):
    """Replace special characters found in Sammallahti's dictionary."""
    return sammallahti_remover(line).translate(
        str.maketrans("Èéíïēīĵĺōūḥḷṃṇṿạẹọụÿⓑⓓⓖ·ṛü’ ", "Eeiieijlouhlmrvaeouybdg ru' ")
    )


def make_dict_entries(dictxml, dictprefix, src, target):
    for entry in dictxml.iter("l"):
        if entry.text is not None:
            STEMS[
                (
                    sammallahti_replacer(entry.text)
                    if dictprefix == "sammallahti"
                    else entry.text
                )
            ].add(src)
    if dictprefix == "sammallahti":
        for entry in dictxml.iter("t"):
            if entry.text is not None and "(+" not in entry.text:
                STEMS[sammallahti_replacer(entry.text)].add(target)


def make_entries(dictxml, dictprefix):
    pair = dictxml.getroot().get("id")
    src = pair[:3]
    target = pair[3:]

    make_dict_entries(dictxml, dictprefix, src, target)


def parse_xmlfile(xml_file):
    parser = etree.XMLParser(remove_comments=True)
    return etree.parse(xml_file, parser=parser)


def import_sammallahti():
    xml_file = os.path.join(
        os.getenv("GUTHOME"),
        "giellalt",
        "dict-sme-fin-x-sammallahti",
        "src",
        "sammallahti.xml",
    )
    try:
        make_entries(parse_xmlfile(xml_file), dictprefix="sammallahti")
    except etree.XMLSyntaxError as error:
        print(
            "Syntax error in {} "
            "with the following error:\n{}\n".format(xml_file, error),
            file=sys.stderr,
        )
    except OSError:
        print("Continuing without Sammallahti's dictionary")


def import_dictfile(xml_file):
    dictxml = parse_xmlfile(xml_file)
    make_entries(dictxml, dictprefix="gt")


def dict_paths():
    return [
        xml_file
        for pair in DICTS
        for xml_file in glob.glob(
            os.path.join(os.getenv("GUTHOME"), "giellalt", f"dict-{pair}", "src")
            + "/*.xml"
        )
        if not xml_file.endswith("meta.xml") and "Der_" not in xml_file
    ]


def import_dicts():
    for xml_file in dict_paths():
        import_dictfile(xml_file)


def import_smjmed():
    habmer_home = os.path.join(
        os.getenv("GUTHOME"), "giellalt", "dict-smj-nob-x-habmer"
    )
    for xml_file in glob.glob(f"{habmer_home}/*.xml"):
        try:
            make_entries(parse_xmlfile(xml_file), dictprefix="habmer")
        except etree.XMLSyntaxError as error:
            print(
                "Syntax error in {} "
                "with the following error:\n{}\n".format(xml_file, error),
                file=sys.stderr,
            )
        except OSError:
            print(f"Continuing without {xml_file}")


def make_m():
    """Iterate over terms."""
    dumphandler = DumpHandler()
    for _, concept in dumphandler.termwiki_pages:
        for expression in concept.related_expressions:
            if expression.sanctioned == "True":
                STEMS[expression.expression].add(LANGS[expression.language])


def import_sms():
    dictprefix = "gt"
    for lang in ["fin", "nob", "rus"]:
        for xml_file in glob.glob(
            os.path.join(os.getenv("GUTHOME"), "giellalt", f"dict-{lang}-sms", "src")
            + "/*.xml"
        ):
            if not xml_file.endswith("meta.xml") and "Der_" not in xml_file:
                make_dict_entries(parse_xmlfile(xml_file), dictprefix, lang, "sms")

    for xml_file in glob.glob(
        os.path.join(os.getenv("GUTHOME"), "giellalt", "dict-sms-mul", "src") + "/*.xml"
    ):
        if not xml_file.endswith("meta.xml") and "Der_" not in xml_file:
            dictxml = parse_xmlfile(xml_file)
            for lang in ["fin", "nob", "rus"]:
                make_dict_entries(dictxml, dictprefix, "sms", lang)


def make_stems() -> dict[str, set[str]]:
    print("Loading stems")
    import_sammallahti()
    import_dicts()
    make_m()
    import_smjmed()
    import_sms()

    return STEMS
