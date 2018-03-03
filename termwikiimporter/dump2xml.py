# -*- coding: utf-8 -*-
"""Turn Concept templates found in termwiki dump.xml file to xml."""

import os
import sys
from lxml import etree
from collections import defaultdict

from termwikiimporter import read_termwiki


counter = defaultdict(int)


def concept2xml(concept, general):
    """Set the main elements of a concept element."""
    for key, value in concept['concept'].items():
        if key == 'collection':
            for collection in concept['concept']['collection']:
                etree.SubElement(general, 'collection').text = collection
        else:
            etree.SubElement(general, key).text = value


def keys2key_xml(concept_info, element_name, concept_xml):
    """Turn template attributes into xml elements.

    Arguments:
        concept (dict): dict containing info TermWiki template attributes
        element_name (str): name of the TermWiki template
        concept2xml (etree.Element): the Concept element
    """
    if not (concept_info.get('sanctioned') and
            concept_info['sanctioned'] == 'False'):
        info = etree.SubElement(concept_xml, element_name)
        for key, value in concept_info.items():
            etree.SubElement(info, key).text = value


def contains_sami(concept_xml):
    uff = set.intersection(
        set(['se', 'sma', 'smj', 'smn', 'sms']),
        {lang.text
         for lang in concept_xml.xpath('./related_expression/language')})

    return len(uff)


def concept_page2xml(concept, pages):
    """Turn a TermWiki concept into xml.

    Arguments:
        concept (dict): contains the info found inside a TermWiki
            Concept template.
    """
    concept_xml = etree.Element('concept')

    concept2xml(concept, concept_xml)
    for keys in ['concept_infos', 'related_expressions', 'related_concepts']:
        for concept_info in concept[keys]:
            keys2key_xml(concept_info, keys[:-1], concept_xml)

    if contains_sami(concept_xml):
        counter['sami'] += 1
        pages.append(concept_xml)


def dump2contents():
    """Turn concept pages found in dump.xml to a dict.

    Yields:
        dict: dump.xml concept turned into a dict
    """
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
            counter['concepts'] += 1
            yield concept


def dump2xml():
    """Read concepts from the dump.xml file.

    Only save terms where at least one related expression is sanctioned.
    """
    pages = etree.Element('concepts')

    for concept in dump2contents():
        concept_page2xml(concept, pages)

    return pages


print(etree.tostring(dump2xml(), encoding='unicode', pretty_print=True))
print(counter, file=sys.stderr)
