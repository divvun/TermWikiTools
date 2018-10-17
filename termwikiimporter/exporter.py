# -*- coding: utf-8 -*-
"""Export content of files to the termwiki."""

import argparse
import collections

from lxml import etree

from termwikiimporter import bot


def parse_options():
    """Parse commandline options."""
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument('wikifiles',
                        nargs='+',
                        help='One or more files containing output from the termimport.')

    args = parser.parse_args()

    return args


def write_to_termwiki():
    """Write the content of the given files to the termwiki."""
    args = parse_options()

    # Initialize Site object
    print('Logging in …')
    sitehandler = bot.SiteHandler()
    site = sitehandler.get_site()

    page_titles = collections.defaultdict(int)
    all_pages = etree.Element('all_pages')

    for wikifile in args.wikifiles:
        wikitree = etree.parse(wikifile)
        for wikipage in wikitree.xpath('.//page'):
            all_pages.append(wikipage)
            page_titles[wikipage.get('title')] += 1

    for page_title, count in list(page_titles.items()):
        pages = all_pages.xpath('.//page[@title="' + page_title + '"]')
        print(page_title, count, len(pages))
        new_page_title = page_title
        counter = 1
        while len(pages) > 0 and counter <= count + 1:
            print('testing page', new_page_title)
            site_page = site.Pages[new_page_title]
            site_text = site_page.text()
            if site_text != '':
                print('\t removing from list', new_page_title)
                for page in pages:
                    for page in pages:
                        if site_text == page.find('./content').text:
                            pages.remove(page)
            else:
                print('\t adding content', new_page_title)
                site_page.save(pages.pop().find('./content').text,
                               summary='New import')
            new_page_title = page_title + '_' + str(counter)
            counter += 1
        print('pages len', len(pages))
