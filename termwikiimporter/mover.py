# -*- coding: utf-8 -*-
"""Move pages in the termwiki."""

import argparse
import collections
import os
import sys

from lxml import etree

from termwikiimporter import bot, importer

CATEGORIES = [
    'Boazodoallu‎', 'Dihtorteknologiija ja diehtoteknihkka',
    'Dáidda ja girjjálašvuohta‎', 'Eanandoallu‎', 'Ekologiija ja biras‎',
    'Ekonomiija ja gávppašeapmi', 'Geografiija‎', 'Gielladieđa‎',
    'Gulahallanteknihkka‎', 'Guolástus‎', 'Huksenteknihkka‎', 'Juridihkka',
    'Luonddudieđa ja matematihkka‎', 'Medisiidna‎', 'Mášenteknihkka‎',
    'Ođđa sánit‎', 'Servodatdieđa‎', 'Stáda, almmolaš hálddašeapmi‎',
    'Teknihkka, industriija, duodji‎', 'Álšateknihkka‎',
    'Ásttoáigi ja faláštallan‎', 'Ávnnasindustriija‎'
]


def parse_options():
    """Parse the options given to the program."""
    parser = argparse.ArgumentParser(
        description=
        'Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument(
        'wikifiles',
        nargs='+',
        help='One or more files containing output from the termimport.')

    args = parser.parse_args()

    return args


def rename_category(oldname, newname):
    """Rename a category and all the pages belonging to it."""
    print('Logging in …')
    site = bot.get_site()

    print('Changing the category in pages')
    for page in site.Categories[oldname]:
        print(page.name)
        page.save(page.text().replace(oldname, newname),
                  summary='Rename category {} -> {}'.format(oldname, newname))


def get_new_page_title(site, new_page_title):
    """Get the new title for the page."""
    new_title = new_page_title
    new_page = site.Pages[new_title]
    counter = 0
    while new_page.text() != '':
        counter += 1
        new_title = new_page_title + '_' + str(counter)
        new_page = site.Pages[new_title]

    return new_title


def move_termwiki():
    """Move pages in the termwiki."""
    print('Logging in …')
    site = bot.get_site()

    print('contacting')
    counter = 0
    pages = etree.Element('pages')
    for category in CATEGORIES:
        sys.stdout.write('\n' + category + '\n')
        for page in site.Categories[category]:
            sys.stdout.write('.')
            page_elt = etree.Element('page')
            page_elt.set('title', page.name)
            content = etree.Element('content')
            content.text = page.text()
            page_elt.append(content)
            pages.append(page_elt)
            counter += 1

    with open('abba.txt', 'w') as abba:
        abba.write(etree.tostring(pages, encoding='utf8', pretty_print=True))
    print(counter)


def move_termwiki_old():
    """Old version of the move_termwiki function."""
    args = parse_options()

    site = bot.get_site()

    page_titles = collections.defaultdict(int)
    all_pages = etree.Element('all_pages')

    for wikifile in args.wikifiles:
        wikitree = etree.parse(wikifile)
        for wikipage in wikitree.xpath('.//page'):
            all_pages.append(wikipage)
            page_titles[wikipage.get('title')] += 1

    for page_title, count in list(page_titles.items()):
        if count > 1:
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


def get_expressions():
    """Get all expression pages, write them to a xmlish file."""
    print('Logging in …')
    site = bot.get_site()

    all_pages = etree.Element('pages')

    for page in site.Categories['Expressions']:
        a_page = etree.Element('page')
        a_page.set('title', page.name)
        content = etree.Element('content')
        content.text = page.text()
        a_page.append(content)
        all_pages.append(a_page)
        sys.stdout.write('-')
        sys.stdout.flush()

    with open('expressions.txt', 'w') as expressions:
        expressions.write(etree.tostring(all_pages, pretty_print=True))


def parse_expression():
    """Parse expressions found in a file."""
    expressions_element = etree.parse(
        os.path.join('termwikiimporter', 'test', 'expressions.txt'))
    counter = collections.defaultdict(int)
    for expression in expressions_element.xpath('page'):
        try:
            content = bot.expression_parser(expression.find('content').text)
            for key, value in content.items():
                counter[key] += value
        except bot.BotError as error:
            print(expression.get('title'), str(error))
        except AttributeError:
            print('empty page', expression.get('title'))

    for key, value in counter.items():
        print(key, value)


def parse_dump(filename):
    """Read the TermWiki dump.xml file, let concept_parser change the content.

    Write the output to another file.

    This is used to get an overview at the changes done by concept_parser
    to find test examples.
    """
    dump_element = etree.parse(filename)
    print(bot.lineno(), filename)
    for element in dump_element.xpath('.//page'):
        category = element.find('title').text.split(':')[0]
        if category in CATEGORIES:
            c_text = element.find('.//text')
            b_text = bot.concept_parser(c_text.text)
            if c_text.text != b_text:
                c_text.text = b_text

    dump_element.write('dump1.xml', encoding='utf8')


def main():
    """The main function of the script."""
    # get_expressions()
    # parse_expression()
    parse_dump(sys.argv[1])
