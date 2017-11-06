# -*- coding: utf-8 -*-
"""Read termwiki pages."""

import inspect

from termwikiimporter.ordereddefaultdict import OrderedDefaultDict


def lineno():
    """Return the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def read_semantic_form(text_iterator):
    """Parse semantic wiki form.

    Args:
        text_iterator (str_iterator): the contents of the termwiki article.

    Returns:
        importer.OrderedDefaultDict
    """
    wiki_form = OrderedDefaultDict()
    wiki_form.default_factory = str
    for line in text_iterator:
        if line == '}}':
            return wiki_form
        elif line.startswith('|reviewed=') or line.startswith('|is_typo'):
            pass
        elif line.startswith('|'):
            equality = line.find('=')
            key = line[1:equality]
            if line[equality + 1:]:
                wiki_form[key] = line[equality + 1:]
        else:
            wiki_form[key] = '\n'.join([wiki_form[key], line])


def fixed_collection_line(line):
    """Add Collection: to collection line if needed.

    Args:
        line (str): a line found in a termwiki page.

    Returns:
        str
    """
    if '|collection' in line and 'Collection:' not in line:
        return line.replace('=', '=Collection:')
    else:
        return line


def fix_collection(orig_text):
    """Add Collection: to collection line if needed.

    Plain text conversion.

    Args:
        orig_text

    Returns:
        str
    """
    return '\n'.join(
        [fixed_collection_line(line) for line in orig_text.split('\n')])


def remove_unwanted_tag(orig_text):
    """Remove unwanted attributes from a termwiki page.

    Plain text conversion.

    Args:
        orig_text

    Returns:
        str
    """
    unwanteds = ['|is_typo', '|has_illegal_char']

    for unwanted in unwanteds:
        new_text = '\n'.join([line for line in orig_text.split('\n')
                              if not line.startswith(unwanted)])
        orig_text = new_text

    return orig_text


def is_related_expression(line):
    """Check if line is the start of a TermWiki Related expression.

    Args:
        line (str): TermWiki line

    Returns:
        bool
    """
    return (line.startswith('{{Related expression') or
            line.startswith('{{Related_expression'))


def to_concept_info(term):
    """Turn old school Concept to new school Concept.

    Arguments:
        term (dict): A representation of a TermWiki Concept
    """
    langs = {}

    concept = {}
    concept.update(term['concept'])

    if concept:
        for key in list(concept.keys()):
            pos = key.rfind('_')
            if pos > 0:
                lang = key[pos + 1:]
                if lang in ['se', 'sv', 'fi', 'en', 'nb', 'nn', 'sma', 'smj',
                            'smn', 'sms', 'lat']:
                    if not langs.get(lang):
                        langs[lang] = {}
                        langs[lang]['language'] = lang
                    new_key = key[:pos]
                    langs[lang][new_key] = concept[key]
                    del concept[key]

    term['concept'] = concept
    for lang in langs:
        term['concept_infos'].append(langs[lang])

    #if term['concept_infos']:
        #print(lineno(), term['concept_infos'])


def parse_termwiki_concept(text):
    """Parse a termwiki page.

    Args:
        text (str): content of the termwiki page.
        counter (collections.defaultdict(int)): keep track of things

    Returns:
        dict: contains the content of the termwiki page.
    """
    text_iterator = iter(text.splitlines())
    term = {
        'concept': {},
        'concept_infos': [],
        'related_expressions': [],
        'related_concepts': []
    }

    for line in text_iterator:
        if (line == '{{Related expression}}' or
                line == '{{Concept info}}' or line == '{{Concept}}'):
            continue
        elif line.startswith('{{Concept info'):
            term['concept_infos'].append(read_semantic_form(text_iterator))
        elif line.startswith('{{Concept'):
            term['concept'] = read_semantic_form(text_iterator)
            if term['concept'].get('language'):
                del term['concept']['language']
            if term['concept'].get('collection'):
                term['concept']['collection'] = set(
                    term['concept']['collection'].split('@@'))
        elif is_related_expression(line):
            expression = read_semantic_form(text_iterator)

            if 'sanctioned' not in expression:
                expression['sanctioned'] = 'No'
            if 'expression' in expression:
                if ' ' in expression['expression']:
                    expression['pos'] = 'MWE'
                if 'collection' in expression:
                    term['collection'].add(expression['collection'].replace('_', ' '))
                    del expression['collection']
                term['related_expressions'].append(expression)

        elif line.startswith('{{Related'):
            term['related_concepts'].append(read_semantic_form(text_iterator))

    to_concept_info(term)

    return term


def term_to_string(term):
    """Turn a term dict to a semantic wiki page.

    Args:
        term (dict): the result of clean_up_concept

    Returns:
        str: term formatted as a semantic wiki page.
    """
    term_strings = []

    for concept_info in term['concept_infos']:
        #print(lineno(), concept_info)
        term_strings.append('{{Concept info')
        for key, value in concept_info.items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')

    for expression in term['related_expressions']:
        term_strings.append('{{Related expression')
        for key, value in expression.items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')

    if term.get('related_concept'):
        for related_concept in term['related_concepts']:
            term_strings.append('{{Related concept')
            for key, value in related_concept.items():
                term_strings.append('|{}={}'.format(key, value))
            term_strings.append('}}')

    if term['concept']:
        term_strings.append('{{Concept')
        for key, value in term['concept'].items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')
    else:
        term_strings.append('{{Concept}}')

    return '\n'.join(term_strings)


def handle_page(orig_text):
    """Parse a termwiki page.

    Args:
        text (str): content of the page

    Returns:
        str: The cleaned up page, in mediawiki format.

    Raises:
        ValueError: if the page is not a known format
    """
    before = orig_text.find('{{')
    if before > 0:
        print('text before {{')
        print(orig_text[:before])
    after = orig_text.rfind('}}')
    if 0 < after + 2 < len(orig_text):
        print('text after')
        print(orig_text[after:])
        print(orig_text)

    return parse_termwiki_concept(
        fix_collection(remove_unwanted_tag(orig_text)))
