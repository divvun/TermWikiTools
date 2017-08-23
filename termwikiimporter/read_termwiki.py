# -*- coding: utf-8 -*-
"""Read termwiki pages."""

import inspect
import sys

from termwikiimporter import importer


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
    wiki_form = importer.OrderedDefaultDict()
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

    Args:
        orig_text

    Returns:
        str
    """
    return '\n'.join(
        [fixed_collection_line(line) for line in orig_text.split('\n')])


def remove_unwanted_tag(orig_text):
    """Remove unwanted attributes from a termwiki page.

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


def fix_content(orig_text):
    """Clean up the content of a TermWiki article.

    Args:
        orig_text (str): Original text of a TermWiki article.

    Returns:
        str: Content of cleaned up TermWiki text
    """
    ruw = remove_unwanted_tag(orig_text)
    if orig_text != ruw:
        print(lineno())
    f_coll = fix_collection(ruw)
    #if ruw != f_coll:
        #print(lineno())
    rthp = handle_page(f_coll)
    #if f_coll != rthp:
        #print(lineno())
    #print()

    return rthp


def is_related_expression(line):
    """Check if line is the start of a TermWiki Related expression.

    Args:
        line (str): TermWiki line

    Returns:
        bool
    """
    return (line.startswith('{{Related expression') or
            line.startswith('{{Related_expression'))


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
        'expressions': [],
        'related_concepts': []}
    for line in text_iterator:
        if line.startswith('{{Concept'):
            if not line.endswith('}}'):
                term['concept'] = read_semantic_form(text_iterator)
        elif is_related_expression(line):
            expression = read_semantic_form(text_iterator)
            if 'sanctioned' not in expression:
                expression['sanctioned'] = 'No'

            if 'expression' in expression:
                term['expressions'].append(expression)

        elif line.startswith('{{Related'):
            term['related_concepts'].append(read_semantic_form(text_iterator))

    return term


def term_to_string(term):
    """Turn a term dict to a semantic wiki page.

    Args:
        term (dict): the result of clean_up_concept

    Returns:
        str: term formatted as a semantic wiki page.
    """
    term_strings = []
    if term['concept']:
        term_strings.append('{{Concept')
        for key, value in term['concept'].items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')
    else:
        term_strings.append('{{Concept}}')

    for expression in term['expressions']:
        term_strings.append('{{Related expression')
        for key, value in expression.items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')

    for related_concept in term['related_concepts']:
        term_strings.append('{{Related concept')
        for key, value in related_concept.items():
            term_strings.append('|{}={}'.format(key, value))
        term_strings.append('}}')

    return '\n'.join(term_strings)


def is_concept_tag(content):
    """Check if content is a TermWiki Concept page.

    Args:
        content (str): content of a TermWiki page.

    Returns:
        bool
    """
    return ('{{Concept' in content and
            ('{{Related expression' in content or
                '{{Related_expression' in content))


def handle_page(text):
    """Parse a termwiki page.

    Args:
        text (str): content of the page

    Returns:
        str: The cleaned up page, in mediawiki format.

    Raises:
        ValueError: if the page is not a known format
    """
    if is_concept_tag(text):
        before = text.find('{{')
        if before > 0:
            print('text before {{')
            print(text[:before])
        after = text.rfind('}}')
        if 0 < after + 2 < len(text):
            print('text after')
            print(text[after:])

        concept = parse_termwiki_concept(text)
        return term_to_string(concept)
    elif 'STIVREN' in text or 'OMDIRIGERING' in text:
        return text
    else:
        raise ValueError('Unknown content:\n{}'.format(text))

