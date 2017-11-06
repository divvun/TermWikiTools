# -*- coding: utf-8 -*-
"""Bot to fix syntax blunders in termwiki articles."""


import collections
import os
import sys
import yaml

import mwclient
from lxml import etree

from termwikiimporter import read_termwiki


NAMESPACES = [
    'Boazodoallu',
    'Dihtorteknologiija ja diehtoteknihkka',
    'Dáidda ja girjjálašvuohta',
    'Eanandoallu',
    'Education',
    'Ekologiija ja biras',
    'Ekonomiija ja gávppašeapmi',
    'Geografiija',
    'Gielladieđa',
    'Gulahallanteknihkka',
    'Guolástus',
    'Huksenteknihkka',
    'Juridihkka',
    'Luonddudieđa ja matematihkka',
    'Medisiidna',
    'Mášenteknihkka',
    'Ođđa sánit',
    'Servodatdieđa',
    'Stáda almmolaš hálddašeapmi',
    'Teknihkka industriija duodji',
    'Álšateknihkka',
    'Ásttoáigi ja faláštallan',
    'Ávnnasindustriija',
]


def get_site():
    """Get a mwclient site object.

    Returns:
        mwclient.Site
    """
    config_file = os.path.join(os.getenv('HOME'),
                               '.config',
                               'term_config.yaml')
    with open(config_file) as config_stream:
        config = yaml.load(config_stream)
        site = mwclient.Site('satni.uit.no', path='/termwiki/')
        site.login(config['username'], config['password'])

        return site


def termwiki_concept_pages(site):
    """Get the concept pages in the TermWiki.

    Args:
        site (mwclient.Site): A site object.

    Yields:
        mwclient.Page
    """
    for category in site.allcategories():
        if category.name.replace('Kategoriija:', '') in NAMESPACES:
            print(category.name)
            for page in category:
                if is_concept_tag(page.text()):
                    yield page
            print()


def dump_concept_pages(dump_tree):
    """Get the concept pages from dump.xml.

    Args:
        dump_tree (lxml.ElementTree): the dump.xml element tree.

    Yields:
        str: content of a TermWiki page.
    """
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'

    for page in dump_tree.getroot().iter('{}page'.format(mediawiki_ns)):
        title = page.find('.//{}title'.format(mediawiki_ns)).text
        if title[:title.find(':')] in NAMESPACES:
            yield page


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


def write_expressions(expressions, site):
    """Make Expression pages.

    Args:
        expressions (list of importer.OrderDefaultDict): The expressions found
            in the Concept page.
        site (mwclient.Site): The site object
    """
    for expression in expressions:
        page = site.Pages['Expression:{}'.format(
            expression['expression'])]
        if not page.exists:
            print('Creating page: {}'.format(page.name))
            page.save(
                to_page_content(expression),
                summary='Creating new Expression page')
        else:
            existings = parse_expression(page.text(),
                                         expression['expression'])
            for existing in existings:
                try:
                    if (existing['language'] == expression['language'] and
                            existing['pos'] == expression['pos']):
                        break
                except TypeError:
                    print(existing, expression)
                    sys.exit(18)
            else:
                existings.append({
                    'language': expression['language'],
                    'pos': expression['pos']})

            new_text = '\n'.join(
                [to_page_content(expression) for expression in existings])
            if page.text() != new_text:
                print()
                print('Correcting content in: {}'.format(page.name))
                page.save(new_text, summary='Correcting content')


def parse_expression(text, page_name):
    """Parse an expression page.

    Args:
        text (str): content of an Expression page.
        page_name (str): name of the Expression page.

    Returns:
        dict(str, str): contains the keys and values found on the Expression
            page.
    """
    existing = []
    text_iterator = iter(text.splitlines())

    for line in text_iterator:
        if line.startswith('{{Expression') and '}}' not in line:
            exp = read_termwiki.read_semantic_form(text_iterator)
            if exp:
                if ' ' in page_name:
                    exp['pos'] = 'MWE'
                if exp not in existing:
                    existing.append(exp)

    return existing


def to_page_content(expression):
    """Turn an expression dict to into Expression page content.

    Args:
        expression (importer.OrderDefaultDict): a dict representing an
            expression

    Returns:
        str: a string containing a TermWiki Expression.
    """
    text_lines = ['{{Expression']
    text_lines.extend(['|{}={}'.format(key, expression[key])
                       for key in expression])
    text_lines.append('}}')

    return '\n'.join(text_lines)


def fix_dump():
    """Check to see if everything works as expected."""
    dump = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'
    tree = etree.parse(dump)

    for page in dump_concept_pages(tree):
        content_elt = page.find('.//{}text'.format(mediawiki_ns))
        if '{{' in content_elt.text:
            content_elt.text = read_termwiki.term_to_string(
                    read_termwiki.handle_page(content_elt.text))

    tree.write(dump, pretty_print=True, encoding='utf8')


def fix_site():
    """Make the bot fix all pages."""
    counter = collections.defaultdict(int)
    print('Logging in …')
    site = get_site()

    print('About to iterate categories')
    for page in termwiki_concept_pages(site):
        print('.', end='')
        sys.stdout.flush()
        orig_text = page.text()

        if '{{' in orig_text:
            concept = read_termwiki.handle_page(orig_text)
            new_text = read_termwiki.term_to_string(concept)

            if orig_text != new_text:
                print()
                print(read_termwiki.lineno(), page.name)
                try:
                    page.save(new_text, summary='Fixing content')
                except mwclient.errors.APIError as error:
                    print(page.name, new_text, str(error), file=sys.stderr)

            write_expressions(concept['expressions'], site)

    for key in sorted(counter):
        print(key, counter[key])


def main():
    """Either fix a TermWiki site or test fixing routines on dump.xml."""
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        fix_dump()
    elif len(sys.argv) == 2 and sys.argv[1] == 'site':
        fix_site()
    else:
        print(
            'Usage:\ntermbot site to fix the TermWiki\n'
            'termbot test to run a test on dump.xml')
