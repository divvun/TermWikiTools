# -*- coding: utf-8 -*-
"""Read termwiki pages."""

import collections
import os

import lxml.etree as etree

from termwikiimporter import bot, importer


def read_semantic_form(text_iterator):
    """Parse semantic wiki form.

    Args:
        text_iterator (str_iterator): the contents of the termwiki article.
    """
    wiki_form = importer.OrderedDefaultDict()
    wiki_form.default_factory = str
    for line in text_iterator:
        if line == '}}':
            return wiki_form
        elif line.startswith('|is_typo'):
            pass
        elif line.startswith('|'):
            equality = line.find('=')
            key = line[1:equality]
            wiki_form[key] = line[equality + 1:]
        else:
            wiki_form[key] = '\n'.join([wiki_form[key], line])


def parse_termwiki_concept(text, counter):
    """Parse a termwiki page.

    Args:
        text (str): content of the termwiki page.
        counter (collections.defaultdict(int)): keep track of things

    Returns:
        dict: contains the content of the termwiki page.
    """
    text_iterator = iter(text.splitlines())
    expressions = importer.OrderedDefaultDict()
    expressions.default_factory = list
    term = {
        'concept': {},
        'related_concepts': []}
    for line in text_iterator:
        if line.startswith('{{Concept'):
            counter['concept'] += 1
            if not line.endswith('}}'):
                term['concept'] = read_semantic_form(text_iterator)
        elif line.startswith('{{Related expression') or line.startswith('{{Related_expression'):
            counter['expression'] += 1
            expression = read_semantic_form(text_iterator)
            expressions[expression['language']].append(expression)
            counter[expression['language']] += 1
        elif line.startswith('{{Related'):
            term['related_concepts'].append(read_semantic_form(text_iterator))
            counter['rconc'] += 1

    term['expressions'] = expressions

    return term


def clean_up_concept(term, counter):
    """Clean up the contents of concept.

    Possibly change the content of term['concept'].

    Remove definitions if they are found in expressions.
    If the above is a hit, promote explanation to definition,
    and more_info to explanation.

    Args:
        concept (dict): The result from parse_termwiki_concept.
        counter (collections.defaultdict(int)): keep track of things
    """
    for language in term['expressions'].keys():
        definition = 'definition_{}'.format(language)

        if (term['concept'].get(definition) in
                [exp['expression'] for exp in term['expressions'][language]]):
            counter['hits'] += 1
            del term['concept'][definition]

        explanation = 'explanation_{}'.format(language)
        if (term['concept'].get(definition) is None and
                term['concept'].get(explanation) is not None):
            counter['promote_exp'] += 1
            term['concept'][definition] = term['concept'].get(explanation)
            del term['concept'][explanation]

        more_info_lang = 'more_info_{}'.format(language)
        if (term['concept'].get(explanation) is None and
                term['concept'].get(more_info_lang) is not None):
            more_info = term['concept'].get(more_info_lang)
            if not ('ohkkeh' in more_info or 'dåhkkidum' in more_info):
                counter['promote_more'] += 1
                term['concept'][explanation] = term['concept'].get(more_info_lang)
                del term['concept'][more_info_lang]


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

    for language in term['expressions'].keys():
        for expression in term['expressions'][language]:
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


def handle_page(text, counter):
    """Parse a termwiki page.

    Args:
        text (str): content of the page
        counter (dict): count occurences of page types

    Returns:
        str: The cleaned up page, in mediawiki format.

    Raises:
        bot.BotError: if the page is not a known format
    """
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

        concept = parse_termwiki_concept(text, counter)
        clean_up_concept(concept, counter)
        return term_to_string(concept)
    elif 'STIVREN' in text or 'OMDIRIGERING' in text:
        counter['redirect'] += 1
    else:
        raise bot.BotError()


def dump_pages(mediawiki_ns):
    """Make a mediawiki page from page elements found in a xml dump file.

    Yields:
        tuple (str, etree.Element)
    """
    dump = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')

    tree = etree.parse(dump)

    for page in tree.getroot().iter('{}page'.format(mediawiki_ns)):
        title = page.find('./{}title'.format(mediawiki_ns))
        if not title.text.startswith('Expression:') and not title.text.startswith('Collection'):
            yield title, page

    tree.write(dump, pretty_print=True, encoding='utf8')


def clean_dump():
    """Cleanup a given termwiki dump in xml format."""
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'
    counter = collections.defaultdict(int)

    for title, page in dump_pages(mediawiki_ns):
        text = page.find('.//{}text'.format(mediawiki_ns)).text
        if text is not None:
            try:
                page.find('.//{}text'.format(mediawiki_ns)).text = handle_page(
                    text,
                    counter)
            except KeyError:
                counter['no_exp'] += 1
                print(bot.lineno())
                print(title.text)
                print(text)
                print()
            except bot.BotError:
                print(bot.lineno())
                print(title.text)
                print(text)
                print()
                counter['erroneous'] += 1
        else:
            counter['deleted'] += 1

    for key in sorted(counter):
        print(key, counter[key])


if __name__ == "__main__":
    clean_dump()
