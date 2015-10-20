# -*- coding: utf-8 -*-


import argparse
from lxml import etree
import mwclient


def parse_options():
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument('wikifiles',
                        nargs='+',
                        help='One or more files containing output from the termimport.')

    args = parser.parse_args()

    return args


def write_to_termwiki():
    args = parse_options()

    # Initialize Site object
    password = raw_input('Write password: ')
    site = mwclient.Site('gtsvn.uit.no', path='/termwiki/')
    site.login('SDTermImporter', password)

    for wikifile in args.wikifiles:
        for wikipage in etree.parse(wikifile).xpath('.//page'):
            page = site.Pages[wikipage.get('title')]
            page.save(wikipage.find('./content').text,
                      summary='Import from ' + wikifile.replace('.xml', '.xlsx'))

