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
            for page in category:
                yield page


def dump_concept_pages(dump_tree):
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'

    for page in dump_tree.getroot().iter('{}page'.format(mediawiki_ns)):
        title = page.find('.//{}title'.format(mediawiki_ns)).text
        if title[:title.find(':')] in NAMESPACES:
            yield page


def fix_site():
    """Make the bot fix all pages."""
    counter = collections.defaultdict(int)
    print('Logging in …')
    site = get_site()

    print('About to iterate categories')
    for page in termwiki_concept_pages(site):

        orig_text = page.text()
        new_text = read_termwiki.fix_content(orig_text)

        if orig_text != new_text:
            try:
                page.save(new_text, summary='Fixing content')
            except mwclient.errors.APIError as error:
                print(page.name, new_text, str(error), file=sys.stderr)

    for key in sorted(counter):
        print(key, counter[key])


def fix_dump():
    """Check to see if everything works as expected."""
    dump = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'
    tree = etree.parse(dump)

    for page in dump_concept_pages(tree):
        content_elt = page.find('.//{}text'.format(mediawiki_ns))
        try:
            content_elt.text = read_termwiki.fix_content(content_elt.text)
        except ValueError:
            print(read_termwiki.lineno(),
                  page.find('.//{}title'.format(mediawiki_ns)).text,
                  'has invalid content\n',
                  content_elt.text,
                  file=sys.stderr)

    tree.write(dump, pretty_print=True, encoding='utf8')


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
