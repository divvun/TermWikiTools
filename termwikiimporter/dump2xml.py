# -*- coding: utf-8 -*-
"""Turn Concept templates found in termwiki dump.xml file to xml."""

import os
from lxml import etree

from termwikiimporter import read_termwiki


def concept2xml(concept, general):
    for key, value in concept['concept'].items():
        if key == 'collection':
            for collection in concept['concept']['collection']:
                etree.SubElement(general, 'collection').text = collection
        else:
            etree.SubElement(general, key).text = value


def keys2key_xml(concept, keys, general):
    for concept_info in concept[keys]:
        info = etree.SubElement(general, keys[:-1])
        for key, value in concept_info.items():
            etree.SubElement(info, key).text = value


def concept_page2xml(concept):
    """Turn a TermWiki concept into xml.

    Arguments:
        concept (dict): contains the info found inside a TermWiki
            Concept template.
    """
    concept_xml = etree.Element('concept')

    concept2xml(concept, concept_xml)
    for keys in ['concept_infos', 'related_expressions', 'related_concepts']:
        keys2key_xml(concept, keys, concept_xml)

    return concept_xml


def dump2contents():
    tree = etree.parse(
        os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml'))
    namespaces = {'m': 'http://www.mediawiki.org/xml/export-0.10/'}

    for page in tree.getroot().xpath('.//m:page', namespaces=namespaces):
        text = page.find('.//m:text', namespaces=namespaces)
        if (text is not None and
                text.text is not None and '{{Concept' in text.text):
            concept = read_termwiki.parse_termwiki_concept(text.text)
            concept['concept']['title'] = page.find(
                './/m:title', namespaces=namespaces).text

            yield concept


def dump2xml():
    """Read concepts from the dump.xml file."""
    pages = etree.Element('concepts')

    for concept in dump2contents():
        pages.append(concept_page2xml(concept))

    return pages


print(etree.tostring(dump2xml(), encoding='unicode', pretty_print=True))
