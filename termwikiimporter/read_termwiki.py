# -*- coding: utf-8 -*-

import collections
import os
import sys

import lxml.etree as etree

sys.path.append(os.path.join(os.getenv('HOME'), 'repos/TermWikiImporter'))

from termwikiimporter import bot, importer


def read_concept(h):
    concept = importer.OrderedDefaultDict()
    concept.default_factory = str
    for line in h:
        if line == '}}':
            return concept
        elif line.startswith('|'):
            parts = line[1:].split('=')
            key = parts[0]
            concept[key] = parts[1]
        else:
            concept[key] = '\n'.join([concept[key], line])


def parse_termwiki_concept(text, counter):
    """Parse a termwiki page.

    Arguments:
        text (str): content of the termwiki page.

    Returns:
        dict: contains the content of the termwiki page.
    """
    h = iter(text.splitlines())
    expressions = importer.OrderedDefaultDict()
    expressions.default_factory = list
    concept = {
        'concept': {},
        'related_concepts': []}
    for line in h:
        if line.startswith('{{Concept'):
            counter['concept'] += 1
            if not line.endswith('}}'):
                concept['concept'] = read_concept(h)
        elif line.startswith('{{Related expression') or line.startswith('{{Related_expression'):
            counter['expression'] += 1
            expression = read_concept(h)
            expressions[expression['language']].append(expression)
            counter[expression['language']] += 1
        elif line.startswith('{{Related'):
            concept['related_concepts'].append(read_concept(h))
            counter['rconc'] += 1

    concept['expressions'] = expressions

    return concept


def clean_up_concept(concept, counter):
    """Clean up the contents of concept.

    Arguments:
        concept (dict): The result from parse_termwiki_concept.
    """
    for language in concept['expressions'].keys():
        d = 'definition_{}'.format(language)

        if concept['concept'].get(d) in [exp['expression'] for exp in concept['expressions'][language]]:
            counter['hits'] += 1
            del concept['concept'][d]

        e = 'explanation_{}'.format(language)
        if concept['concept'].get(d) is None and concept['concept'].get(e) is not None:
            counter['promote_exp'] += 1
            concept['concept'][d] = concept['concept'].get(e)
            del concept['concept'][e]

        m = 'more_info_{}'.format(language)
        if concept['concept'].get(e) is None and concept['concept'].get(m) is not None:
            mi = concept['concept'].get(m)
            if not ('ohkkeh' in mi or 'dåhkkidum' in mi):
                counter['promote_more'] += 1
                concept['concept'][e] = concept['concept'].get(m)
                del concept['concept'][m]


def concept_to_string(concept):
    concept_strings = []
    if concept['concept']:
        concept_strings.append('{{Concept')
        for key, value in concept['concept'].items():
            concept_strings.append('|{}={}'.format(key, value))
        concept_strings.append('}}')
    else:
        concept_strings.append('{{Concept}}')

    for language in concept['expressions'].keys():
        for expression in concept['expressions'][language]:
            concept_strings.append('{{Related expression')
            for key, value in expression.items():
                concept_strings.append('|{}={}'.format(key, value))
            concept_strings.append('}}')

    for related_concept in concept['related_concepts']:
        concept_strings.append('{{Related concept')
        for key, value in related_concept.items():
            concept_strings.append('|{}={}'.format(key, value))
        concept_strings.append('}}')

    return '\n'.join(concept_strings)


def clean_dump():
    DUMP = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')

    counter = collections.defaultdict(int)
    tree = etree.parse(DUMP)

    for page in tree.getroot().iter('{http://www.mediawiki.org/xml/export-0.10/}page'):
        title = page.find('./{http://www.mediawiki.org/xml/export-0.10/}title')
        if not title.text.startswith('Expression:') and not title.text.startswith('Collection'):

            text = page.find(
                './/{http://www.mediawiki.org/xml/export-0.10/}text').text
            if '{{Concept' in text and ('{{Related expression' in text or '{{Related_expression' in text):
                before = text.find('{{')
                if before > 0:
                    print('text before {{')
                    print(text[:before])
                after = text.rfind('}}')
                if 0 < after + 2 < len(text):
                    print('text after')
                    print(text[after:])
                counter['real'] += 1
                try:
                    concept = parse_termwiki_concept(text, counter)
                    clean_up_concept(concept, counter)
                    page.find(
                './/{http://www.mediawiki.org/xml/export-0.10/}text').text = concept_to_string(concept)
                except KeyError:
                    counter['no_exp'] += 1
                    # print(title.text)
                    # print(text)
                    # print()
            else:
                counter['fake'] += 1


    tree.write(DUMP, pretty_print=True, encoding='utf8')
    print(counter)


if __name__ == "__main__":
    clean_dump()
