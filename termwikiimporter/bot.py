# -*- coding: utf-8 -*-
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this file. If not, see <http://www.gnu.org/licenses/>.
#
#   Copyright © 2016-2019 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Bot to fix syntax blunders in termwiki articles."""
import collections
import json
import os
import sys
import uuid
import re

import hfst
import mwclient
import yaml
from lxml import etree

from termwikiimporter import dicts2wiki, read_termwiki

XI_NAMESPACE = 'http://www.w3.org/2001/XInclude'
XML_NAMESPACE = 'https://www.w3.org/XML/1998/namespace'
XI = '{%s}' % XI_NAMESPACE
XML = '{%s}' % XML_NAMESPACE
NSMAP = {'xi': XI_NAMESPACE, 'xml': XML_NAMESPACE}
NAMESPACES = [
    'Beaivválaš giella',
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
    'Religion',
    'Teknihkka industriija duodji',
    'Álšateknihkka',
    'Ásttoáigi ja faláštallan',
    'Ávnnasindustriija',
]


def correct_sanctioned(sanctioned):
    if sanctioned not in ['False', 'True']:
        raise SystemExit(f'sanctioned must be True or False')


def missing_dicts(language):
    """Parse dicts to look for part of speech."""
    not_founds = collections.defaultdict(set)
    analyser_lang = 'sme' if language == 'se' else language
    path = f'/usr/share/giella/{analyser_lang}/analyser-gt-norm.hfstol'
    if os.path.isfile(path):
        analyser = hfst.HfstInputStream(path).read()
    else:
        raise SystemExit(f'{path} does not exist')

    for dictxml, xml_dict in dicts2wiki.valid_xmldict():
        language_pairs = dictxml.getroot().get('id')
        if language in language_pairs:
            tag = 'l' if language_pairs[:3] == language else 't'
            if tag == 't':
                for tg_element in dictxml.xpath('.//tg'):
                    if tg_element.get(
                            '{http://www.w3.org/XML/1998/namespace}lang'
                    ) == language:
                        for lemma_element in tg_element.iter(tag):
                            if lemma_element.text is not None:
                                for lemma in lemma_element.text.split():
                                    if not analyser.lookup(lemma.strip()):
                                        not_founds[lemma.strip()].add(
                                            xml_dict.replace(
                                                os.getenv('GTHOME'),
                                                '$GTHOME'))
            else:
                for lemma_element in dictxml.iter(tag):
                    for lemma in lemma_element.text.split():
                        if not analyser.lookup(lemma.strip()):
                            not_founds[lemma.strip()].add(
                                xml_dict.replace(os.getenv('GTHOME'),
                                                 '$GTHOME'))

    return not_founds


def have_same_expressions(concept1: read_termwiki.Concept,
                          concept2: read_termwiki.Concept) -> bool:
    """Check if the expressions of the concepts are the same."""
    set1 = {(expression['expression'], expression['language'])
            for expression in concept1.related_expressions}
    set2 = {(expression['expression'], expression['language'])
            for expression in concept2.related_expressions}
    return len(set1.intersection(set2)) > 3


def print_entry(concept):
    """Print a concept."""
    if ':' not in concept.title:
        print(f'\n==={concept.title}===')
    else:
        print(concept.title)
    print('\t'.join([
        ' '.join([concept_info['definition'], concept_info['language']])
        for concept_info in concept.data['concept_infos']
    ]))
    print('\t'.join([
        ' '.join([
            related_expression['expression'], related_expression['language'],
            related_expression['pos']
        ]) for related_expression in concept.related_expressions
    ]))
    print()


def read_dump():
    """Read the dump in to and expression and term entry index."""
    tw_expression_index = {}
    tw_index = {}

    dumphandler = DumpHandler()

    for title, content_elt in dumphandler.content_elements:
        title = title.replace(' ', '_')
        concept = read_termwiki.Concept()
        concept.title = title
        concept.from_termwiki(content_elt.text)
        tw_index[title] = concept

        for expression in concept.related_expressions:
            if expression.get('language'):
                if not tw_expression_index.get(expression['language']):
                    tw_expression_index[
                        expression['language']] = collections.defaultdict(set)
                tw_expression_index[expression['language']][
                    expression['expression']].add(title)
            else:
                print(title)
                print(concept)

    return tw_index, tw_expression_index


def read_pages(pages_filename):
    """Read the dump in to and expression and term entry index."""
    tw_expression_index = {}
    tw_index = {}

    pages = etree.parse(pages_filename)

    for page in pages.iter('page'):
        title = page.get('title').replace(' ', '_')
        page_concept = page.find('.//concept').text

        concept = read_termwiki.Concept()
        concept.title = title
        concept.from_termwiki(str(page_concept))
        tw_index[title] = concept

        for expression in concept.related_expressions:
            if expression.get('language'):
                if not tw_expression_index.get(expression['language']):
                    tw_expression_index[
                        expression['language']] = collections.defaultdict(set)
                tw_expression_index[expression['language']][
                    expression['expression']].add(title)
            else:
                print(concept)

    return tw_index, tw_expression_index


def merge_concept(concept: read_termwiki.Concept,
                  tw_concept: read_termwiki.Concept) -> None:
    """Merge concept into tw_concept."""
    if not tw_concept.collections:
        tw_concept.data['concept']['collection'] = set()
    for coll in concept.collections:
        tw_concept.data['concept']['collection'].add(coll)

    # merge concept_info
    for concept_info in concept.data['concept_infos']:
        for tw_concept_info in tw_concept.data['concept_infos']:
            if concept_info['language'] == tw_concept_info['language']:
                for key, value in concept_info.items():
                    if not tw_concept_info.get(key):
                        tw_concept_info[key] = value

    # update related expressions in tw_concept from concept
    for expression1 in concept.related_expressions:
        for expression2 in tw_concept.related_expressions:
            if expression1['expression'] == expression2[
                    'expression'] and expression1['language'] == expression2[
                        'language']:
                expression2['sanctioned'] = 'True'

    concept_set = {(expression['expression'], expression['language'])
                   for expression in concept.related_expressions}
    tw_concept_set = {(expression['expression'], expression['language'])
                      for expression in tw_concept.related_expressions}
    for expression, language in concept_set.difference(tw_concept_set):
        for expression1 in concept.related_expressions:
            if expression == expression1[
                    'expression'] and language == expression1['language']:
                try:
                    uxpression = expression1
                except TypeError as error:
                    raise SystemExit(expression1)
                uxpression['sanctioned'] = 'True'
                tw_concept.related_expressions.append(uxpression)


class DumpHandler(object):
    """Class that involves using the TermWiki dump.

    Attributes:
        termwiki_xml_root (str): path where termwiki xml files live.
        dump (str): path to the dump file.
        tree (etree.ElementTree): the parsed dump file.
        mediawiki_ns (str): the mediawiki name space found in the dump file.
    """

    termwiki_xml_root = os.path.join(os.getenv('GTHOME'),
                                     'words/terms/termwiki')
    dump = os.path.join(termwiki_xml_root, 'dump.xml')
    tree = etree.parse(dump)
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'

    def save_concept(self, tw_concept: read_termwiki.Concept,
                     main_title: str) -> None:
        """Save a concept to the dump file."""
        root = self.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
        title = root.xpath(f'.//mw:title[text()="{main_title}"]',
                           namespaces=namespace)[0]
        if title is not None:
            page = title.getparent()
            tuxt = page.xpath(f'.//mw:text', namespaces=namespace)[0]
            tuxt.text = str(tw_concept)
        else:
            raise SystemExit(f'did not find {main_title}')

    @property
    def pages(self):
        """Get the namespaced pages from dump.xml.

        Yields:
            tuple: The title and the content of a TermWiki page.
        """
        for page in self.tree.getroot().iter('{}page'.format(
                self.mediawiki_ns)):
            title = page.find('.//{}title'.format(self.mediawiki_ns)).text
            if title[:title.find(':')] in NAMESPACES:
                yield title, page

    @property
    def content_elements(self):
        """Get concept elements found in dump.xml.

        Yields:
            etree.Element: the content element found in a page element.
        """
        for title, page in self.pages:
            content_elt = page.find('.//{}text'.format(self.mediawiki_ns))
            if content_elt.text and '{{Concept' in content_elt.text:
                yield title, content_elt

    @property
    def concepts(self):
        """Get concepts found in dump.xml.

        Yields:
            read_termwiki.Concept: the content element found in a page element.
        """
        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            yield title, concept

    def expressions(self):
        """All expressions found in dumphandler."""
        return ((title, expression) for title, concept in self.concepts
                for expression in concept.related_expressions)

    def expressions_by_language_status(self, language, sanctioned):
        """Filter by language."""
        return ((title, expression)
                for title, expression in self.expressions()
                if expression['language'] == language
                and expression['sanctioned'] == sanctioned)

    def not_found_in_normfst(self, language, status):
        """Return expressions not found in normfst."""
        analyser_lang = 'sme' if language == 'se' else language
        not_founds = collections.defaultdict(set)
        norm_analyser = hfst.HfstInputStream(
            f'/usr/share/giella/{analyser_lang}/analyser-gt-norm.hfstol').read(
            )

        base_url = 'https://satni.uit.no/termwiki'
        for title, expression in self.expressions_by_language_status(
                language, status):
            for real_expression1 in expression['expression'].split():
                for real_expression in real_expression1.split('/'):
                    for invalid in [
                            '(', ')', ',', '?', '+', '*', '[', ']', '=', ';',
                            ':', '!'
                    ]:
                        real_expression = real_expression.replace(invalid, '')
                    if real_expression and not real_expression.startswith(
                        ('‑',
                         '-')) and not norm_analyser.lookup(real_expression):
                        not_founds[real_expression].add(
                            f'{base_url}/index.php?title={title.replace(" ", "_")}'
                        )

        return not_founds

    @staticmethod
    def known_to_descfst(language, not_in_norms):
        analyser_lang = 'sme' if language == 'se' else language
        desc_analyser = hfst.HfstInputStream(
            f'/usr/share/giella/{analyser_lang}/analyser-gt-desc.hfstol').read(
            )
        founds = collections.defaultdict(dict)

        for real_expression in not_in_norms:
            analyses = {
                ''.join([part for part in a[0].split('@') if '+' in part])
                for a in desc_analyser.lookup(real_expression)
            }
            without_cmp = {
                analysis
                for analysis in analyses if '+Cmp#' not in analysis
            }
            if analyses:
                founds[real_expression][
                    'analyses'] = without_cmp if without_cmp else analyses
                founds[real_expression]['sources'] = [
                    source for source in sorted(not_in_norms[real_expression])
                ]

        return founds

    def print_missing(self, language, status):
        """Find all expressions of the given language.

        Args:
            language (src): language of the terms.
        """
        def revsorted_expressions(not_founds):
            return [
                reverted[::-1] for reverted in sorted(
                    [not_found[::-1] for not_found in not_founds])
            ]

        terms = self.not_found_in_normfst(
            language if language != 'sme' else 'se', status)
        dicts = missing_dicts(language)

        not_in_norms = collections.defaultdict(set)

        for key in set(list(terms) + list(dicts)):
            not_in_norms[key] = set().union(dicts[key]).union(terms[key])

        descriptives = self.known_to_descfst(language, not_in_norms)
        norms = {
            expression: not_in_norms[expression]
            for expression in not_in_norms if expression not in descriptives
        }

        for descriptive in revsorted_expressions(descriptives):
            print(descriptive)
            print('\n'.join([
                f'{descriptive}\t{analysis}'
                for analysis in descriptives[descriptive]['analyses']
            ]))
            print('\n'.join([
                f'\t{source}'
                for source in descriptives[descriptive]['sources']
            ]))
            print()

        for norm in revsorted_expressions(norms):
            print(f'{norm}:{norm} TODO ; !', end='  ')
            print(' '.join([url for url in sorted(norms[norm])]))

    def auto_sanction(self, language):
        """Automatically sanction expressions that have no collection.

        The theory is that concept pages with no collections mostly are from
        the risten.no import, and if there are no typos found in an expression
        they should be sanctioned.

        Args:
            language (str): the language to sanction
        """
        ex = 1
        for _, content_elt in self.content_elements:
            print('.', end='')
            sys.stdout.flush()
            ex += 1
            concept = read_termwiki.Concept()
            concept.from_termwiki(content_elt.text)
            if concept.collections is None:
                concept.auto_sanction(language)
                content_elt.text = str(concept)

        self.tree.write(self.dump, pretty_print=True, encoding='utf-8')

    def sum_terms(self, language=None):
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        counter = collections.defaultdict(int)
        for _, concept in self.concepts:
            for expression in concept.related_expressions:
                if expression['language'] == language:
                    counter[expression['sanctioned']] += 1

        print('{}: {}: true, {}: false, {}: total'.format(
            language, counter['true'], counter['false'],
            counter['false'] + counter['true']))

    def print_invalid_chars(self, language, status):
        """Find terms with invalid characters, print the errors to stdout."""
        invalid_chars_re = re.compile(r'[()[\]?:;+*=]')
        base_url = 'https://satni.uit.no/termwiki'
        for title, expression in self.expressions_by_language_status(
                language, status):
            if invalid_chars_re.search(expression['expression']):
                print(
                    f'{expression["expression"]} {base_url}/index.php?title={title.replace(" ", "_")}'
                )

    def fix(self):
        """Check to see if everything works as expected."""
        for title, content_elt in self.content_elements:
            try:
                concept = read_termwiki.Concept()
                concept.from_termwiki(content_elt.text)
                content_elt.text = str(concept)
            except TypeError:
                print('empty element:\n{}\n{}\n'.format(
                    title, etree.tostring(content_elt, encoding='unicode')))

        self.tree.write(self.dump, pretty_print=True, encoding='utf8')

    def find_collections(self):
        """Check if collections are correctly defined."""
        for title, page in self.pages:
            if title.startswith('Collection:'):
                content_elt = page.find('.//{}text'.format(self.mediawiki_ns))
                text = content_elt.text
                if text:
                    if '{{Collection' not in text:
                        print('|collection={}\n{}'.format(title, text))
                        print()
                else:
                    print(title, etree.tostring(content_elt,
                                                encoding='unicode'))

    def sort_dump(self):
        """Sort the dump file by page title."""
        root = self.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}

        pages = root.xpath('.//mw:page', namespaces=namespace)
        pages[:] = sorted(pages,
                          key=lambda page: page.find(
                              './mw:title', namespaces=namespace).text)

        for page in root.xpath('.//mw:page', namespaces=namespace):
            page.getparent().remove(page)

        for page in pages:
            root.append(page)

        self.tree.write(self.dump, pretty_print=True, encoding='utf-8')

    def print_expression_pairs(self, lang1, lang2):
        """Print pairs of expressions, for use in making bidix files."""
        for title, concept in self.concepts:
            term = concept.data

            if concept.has_sanctioned_sami():
                langs = {lang1: set(), lang2: set()}
                for expression in term['related_expressions']:
                    if expression['language'] == lang1 or expression[
                            'language'] == lang2:
                        if expression['sanctioned'] == 'True':
                            langs[expression['language']].add(
                                expression['expression'])

                if langs[lang1] and langs[lang2]:
                    for expression in langs[lang1]:
                        print('{}\t{}'.format(expression,
                                              ', '.join(langs[lang2])))

    @staticmethod
    def get_site():
        """Get a mwclient site object.

        Returns:
            mwclient.Site
        """
        config_file = os.path.join(os.getenv('HOME'), '.config',
                                   'term_config.yaml')
        with open(config_file) as config_stream:
            config = yaml.load(config_stream)
            site = mwclient.Site('satni.uit.no', path='/termwiki/')
            site.login(config['username'], config['password'])

            print('Logging in to query …')

            return site

    @staticmethod
    def uff_key(concept):
        """Turn the expression references into a string"""
        return ''.join(
            sorted({
                r.get('expression_ref')
                for r in concept.iter('related_expression')
            }))

    def mergeable_pages(self, pages_filename: str, languages: list):
        tw_index, tw_expression_index = read_dump()
        sd_index, sd_expression_index = read_pages(pages_filename)
        sd_titles = collections.defaultdict(set)

        for sd_title, sd_concept in sd_index.items():
            potential_pages = {}
            for language in languages:
                sd_expressions = [
                    expression['expression']
                    for expression in sd_concept.related_expressions
                    if expression['language'] == language
                ]
                potential_pages[language] = {
                    title
                    for sd_expression in sd_expressions
                    for title in tw_expression_index[language][sd_expression]
                }
            total = potential_pages['nb'] & potential_pages[
                'sma'] & potential_pages['sv']
            sd_concept.title = sd_title

            if not total:
                print(f'no hits, saving to {sd_title}\n')
            elif len(total) == 1:
                print(list(total)[0])
                yield sd_concept, tw_index[list(total)[0]]
            else:
                for title in total:
                    print_entry(sd_concept)
                    print_entry(tw_index[title])
                    answer = input('enter merges, any other skips: ')
                    if answer == '':
                        yield sd_concept, tw_index[title]

    def merge_pages(self, pages_filename: str, summary: str,
                    languages) -> None:
        """Merge terms from the pages xml format into TermWiki."""
        counter = 0

        for concept1, concept2 in self.mergeable_pages(pages_filename,
                                                       languages):
            merge_concept(concept1, concept2)
            self.save_concept(concept2, concept2.title.replace('_', ' '))
            counter += 1
            print(f'Merging {concept1.title} into {concept2.title} {counter}')
            if counter > 99:
                break

        self.tree.write(self.dump, pretty_print=True, encoding='utf-8')
        print(f'Merged {counter} concepts into TermWiki')

    def statistics(self, languages):
        for language in languages:
            counter = {}
            for title, concept in self.concepts:
                if any([
                        expression['language'] == language
                        for expression in concept.related_expressions
                ]):
                    category = title[:title.find(':')]
                    if not counter.get(category):
                        counter[category] = collections.defaultdict(int)
                    counter[category]['concepts'] += 1
                    expression_with_lang = [
                        expression
                        for expression in concept.related_expressions
                        if expression['language'] == language
                    ]
                    counter[category]['expressions'] += len(
                        expression_with_lang)
                    counter[category]['true_expressions'] += len([
                        expression for expression in expression_with_lang
                        if expression['sanctioned'] == 'True'
                    ])
                    counter[category]['false_expressions'] += len([
                        expression for expression in expression_with_lang
                        if expression['sanctioned'] == 'False'
                    ])
                    counter[category]['invalid'] += len([
                        expression for expression in expression_with_lang
                        if concept.invalid_chars_re.search(
                            expression['expression'])
                    ])

            total = collections.defaultdict(int)
            print(language)
            for category in counter:
                print(category)
                for item in counter[category].items():
                    total[item[0]] += item[1]
                    print(f'{item[0]}\t{item[1]}')
                print()

            print(f'Totally for {language}')
            for item in total.items():
                total[item[0]] += item[1]
                print(f'{item[0]}\t{item[1]}')
            print()


class SiteHandler(object):
    """Class that involves using the TermWiki dump.

    Attributes:
        site (mwclient.Site): the TermWiki site
    """
    def __init__(self):
        """Initialise the SiteHandler class."""
        self.site = self.get_site()

    @staticmethod
    def get_site():
        """Get a mwclient site object.

        Returns:
            mwclient.Site
        """
        config_file = os.path.join(os.getenv('HOME'), '.config',
                                   'term_config.yaml')
        with open(config_file) as config_stream:
            config = yaml.load(config_stream, Loader=yaml.FullLoader)
            site = mwclient.Site('satni.uit.no', path='/termwiki/')
            site.login(config['username'], config['password'])

            print('Logging in to query …')

            return site

    @property
    def content_elements(self, verbose=False):
        """Get the concept pages in the TermWiki.

        Yields:
            mwclient.Page
        """
        for category in self.site.allcategories():
            if category.name.replace('Kategoriija:', '') in NAMESPACES:
                if verbose:
                    print(category.name)
                for page in category:
                    if self.is_concept_tag(page.text()):
                        yield page

    def del_expression(self):
        """Delete all expression pages."""
        for page in self.site.Categories['Expressions']:
            try:
                print('Deleting: {}'.format(page.name))
                page.delete(reason='Will be replaced by Stem page')
            except mwclient.APIError as error:
                if error.code != 'cantdelete':  # Okay if already deleted
                    print('Can not delete {}.\nError {}'.format(
                        page.name, error))

    @staticmethod
    def is_concept_tag(content):
        """Check if content is a TermWiki Concept page.

        Args:
            content (str): content of a TermWiki page.

        Returns:
            bool
        """
        return '{{Concept' in content

    @staticmethod
    def save_page(page, content, summary):
        """Save a given TermWiki page.

        Args:
            content (str): the new content to be saved.
            summary (str): the commit message.
        """
        try:
            page.save(content, summary=summary)
        except mwclient.errors.APIError as error:
            print(page.name, content, str(error), file=sys.stderr)

    def delete_redirects(self):
        dump = DumpHandler()
        root = dump.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
        redirects = {
            redirect_xml.getparent().getparent()
            for redirect_xml in root.xpath(
                f'.//mw:text[starts-with(text(), "#STIVREN")]',
                namespaces=namespace)
        }
        print('Redirects pages', len(redirects))
        for redirect in redirects:
            title1 = redirect.find('.//mw:title', namespace)
            page = self.site.pages[title1.text]
            if page.redirect:
                page.delete(reason="Redirect page is not needed")
            else:
                print(f'\tis not redirect {title1.text}')

    def fix_expression_pages(self):
        dump = DumpHandler()
        root = dump.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
        expressions = {
            expression_xml.text
            for expression_xml in root.xpath(
                f'.//mw:title[starts-with(text(), "Expression:")]',
                namespaces=namespace)
        }
        real_expressions = set()
        for title, concept in dump.concepts:
            for expression in concept.related_expressions:
                expression_title = f'Expression:{expression["expression"].replace("&amp;", "&")}'
                real_expressions.add(expression_title)
                if expression_title not in expressions:
                    self.make_expression_page(expression)

        print('Expression pages', len(expressions))
        print('Real expressions', len(real_expressions))

        for to_delete in expressions - real_expressions:
            page = self.site.Pages[to_delete]
            if page.exists:
                print(f'Removing {to_delete}')
                page.delete(reason="Is not found among related expressions")

    def delete_pages(self, part_of_title):
        dump = DumpHandler()
        root = dump.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}
        to_deletes = {
            expression_xml.text
            for expression_xml in root.xpath(
                f'.//mw:title[starts-with(text(), "{part_of_title}")]',
                namespaces=namespace)
        }
        print(f'{len(to_deletes)} pages to delete')
        for to_delete in to_deletes:
            page = self.site.Pages[to_delete]
            if page.exists:
                print(f'Removing {to_delete}')
                page.delete(reason="Pages is not needed anymore")

    def fix(self):
        """Make the bot fix all pages."""
        counter = collections.defaultdict(int)

        for page in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(page.text())
            if concept.related_expressions:
                self.save_page(page, str(concept), summary='Fixing content')
            else:
                page.delete(reason='Have no expressions')

        for key in sorted(counter):
            print(key, counter[key])

    def make_expression_page(self, expression):
        title = f'Expression:{expression["expression"]}'
        try:
            expression_page = self.site.Pages[title]
            print(f'Trying to make {title}', end=' ')
            if not expression_page.exists:
                strings = [
                    f'|{key}={expression[key]}' for key in ['language', 'pos']
                    if expression[key]
                ]
                strings.insert(0, '{{Expression')
                strings.append('}}')
                expression_page.save('\n'.join(strings),
                                     summary='Created by termbot')
                print('succeeded')
            else:
                print('already exists')
        except mwclient.errors.InvalidPageTitle:
            print(f'Invalid title {title}')

    def semantic_ask_results(self, query):
        for number, answer in enumerate(self.site.ask(query), start=1):
            print(answer)
            yield number, answer['fulltext']

    def add_extra_collection(self):
        visited_pages = set()
        dumphandler = DumpHandler()
        for title, content_elt in dumphandler.content_elements:
            concept1 = read_termwiki.Concept()
            concept1.from_termwiki(content_elt.text)
            if 'Collection:SD-terms' in concept1.collections:
                if title not in visited_pages:
                    visited_pages.add(title)
                    page = self.site.Pages[title]
                    concept = read_termwiki.Concept()
                    concept.from_termwiki(page.text())
                    name = title.split(':')[1]
                    extra_collection = f'Collection:SD-terms-{name[0].lower()}'
                    if extra_collection not in concept.collections:
                        concept.collections.add(extra_collection)
                        print(f'\n\t{title} {extra_collection}\n')
                        self.save_page(
                            page,
                            str(concept),
                            summary=f'Add collection: {extra_collection}')

        print(len(visited_pages))

    def query_replace_text(self, language):
        u"""Do a semantic media query and fix pages.

        Change the query and the actions when needed …

        http://mwclient.readthedocs.io/en/latest/reference/site.html#mwclient.client.Site.ask
        https://www.semantic-mediawiki.org/wiki/Help:API
        """
        query = ('[[Related expression::+]]'
                 '[[Language::{}]]'
                 '[[Sanctioned::False]]'.format(language))

        for number, concept in self.semantic_ask_results(query):
            if concept.collections is None:
                print('Hit no: {}, title: {}'.format(number, concept.title))
                concept.auto_sanction(language)
                self.save_page(
                    page,
                    str(concept),
                    summary='Sanctioned expressions not associated with any '
                    'collections that the normative {} fst '
                    'recognises.'.format(language))

    def auto_sanction(self, language):
        """Automatically sanction expressions that have no collection.

        The theory is that concept pages with no collections mostly are from
        the risten.no import, and if there are no typos found in an expression
        they should be sanctioned.

        Args:
            language (str): the language to sanction
        """
        ex = 1
        query = ('[[Related expression::+]]'
                 '[[Language::{}]]'
                 '[[Sanctioned::False]]'.format(language))

        for _, answer in enumerate(self.site.ask(query), start=1):
            for title, _ in answer.items():
                print('.', end='')
                sys.stdout.flush()
                ex += 1
                page = self.site.Pages[title]
                concept = read_termwiki.Concept()
                concept.from_termwiki(page.text())
                if concept.collections is None:
                    concept.auto_sanction(language)
                    self.save_page(
                        page,
                        str(concept),
                        summary='Sanctioned expressions not associated with any '
                        'collections that the normative {} fst '
                        'recognises.'.format(language))

    def revert(self):
        """Automatically sanction expressions that have no collection.

        The theory is that concept pages with no collections mostly are from
        the risten.no import, and if there are no typos found in an expression
        they should be sanctioned.

        Args:
            language (str): the language to sanction
        """
        rollback_token = self.site.get_token('rollback')
        for page in self.content_elements:
            try:
                self.site.api('rollback',
                              title=page.name,
                              user='SDTermImporter',
                              summary='Use Stempage in Related expression',
                              markbot='1',
                              token=rollback_token)
            except mwclient.errors.APIError as error:
                print(page.name, error)

    def remove_paren(self, old_title: str) -> str:
        """Remove parenthesis from termwiki page name.

        Args:
            old_title: a title containing a parenthesis

        Returns:
            A new unique page name without parenthesis
        """
        new_title = old_title[:old_title.find('(')].strip()
        my_title = new_title
        instance = 1
        page = self.site.pages[my_title]
        while page.exists:
            my_title = '{} {}'.format(new_title, instance)
            page = self.site.pages[my_title]
            instance += 1

        return my_title

    def move_page(self, old_name: str, new_name: str) -> None:
        """Move a termwiki page from old to new name."""
        orig_page = self.site.pages[old_name]
        try:
            print(f'Moving from {orig_page.name} to {new_name}')
            orig_page.move(new_name,
                           reason='Remove parenthesis from page names',
                           no_redirect=True)
        except mwclient.errors.InvalidPageTitle as error:
            print(old_name, error, file=sys.stderr)

    def fix_revisions(self) -> None:
        """Example on how to restore pages only touched by bots."""
        import time
        token = self.site.api('query', meta='tokens')
        start_time = time.strptime('15 Feb 19', '%d %b %y')

        dumphandler = DumpHandler()
        for title, content_elt in dumphandler.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)

            if 'Collection:JustermTana' in concept.collections:
                page = self.site.Pages[concept.title]
                users = {
                    revision['user']
                    for revision in page.revisions()
                    if revision['timestamp'] > start_time
                    and 'mporter' not in revision['user']
                }
                if users:
                    print(title, users)
                else:
                    print(f'Saving {title}')
                    self.save_page(page,
                                   str(concept),
                                   summary='Saved from backup')

    def improve_pagenames(self) -> None:
        """Remove characters that break eXist search from page names."""
        for page in self.content_elements:
            try:
                my_title = read_termwiki.fix_sms(
                    self.remove_paren(page.name) if '(' in
                    page.name else page.name)
                if page.name != my_title:
                    self.move_page(page.name, my_title)
            except mwclient.errors.InvalidPageTitle:
                print(f'Failed on {page.name}')

    def mergeable_pages(self, pages_filename: str, languages: list):
        tw_index, tw_expression_index = read_dump()
        sd_index, sd_expression_index = read_pages(pages_filename)
        sd_titles = collections.defaultdict(set)

        for sd_title, sd_concept in sd_index.items():
            potential_pages = {}
            for language in languages:
                sd_expressions = [
                    expression['expression']
                    for expression in sd_concept.related_expressions
                    if expression['language'] == language
                ]
                potential_pages[language] = {
                    title
                    for sd_expression in sd_expressions
                    for title in tw_expression_index[language][sd_expression]
                }
            total = potential_pages['nb'] & potential_pages[
                'sma'] & potential_pages['sv']
            sd_concept.title = sd_title

            if not total:
                print('zero')
                yield sd_concept, sd_concept
            elif len(total) == 1:
                yield sd_concept, tw_index[list(total)[0]]
            else:
                for title in total:
                    print_entry(sd_concept)
                    print_entry(tw_index[title])
                    answer = input('enter merges, any other skips: ')
                    if answer == '':
                        yield sd_concept, tw_index[title]

    def merge_pages(self, pages_filename: str, summary: str, languages: list):
        """Merge terms from the pages xml format into TermWiki."""
        counter = 0
        for concept1, concept2 in self.mergeable_pages(pages_filename,
                                                       languages):
            merge_concept(concept1, concept2)
            page = self.site.Pages[concept2.title]
            self.save_page(page, str(concept2), summary=f'{summary}')
            counter += 1
            print(f'Merging {concept1.title} into {concept2.title} {counter}')
        print(f'Merged {counter} concepts into TermWiki')


def handle_dump(arguments):
    """Act on the TermWiki dump.

    Args:
        argument (str): command line argument
    """
    dumphandler = DumpHandler()

    if arguments[0] == 'fix':
        dumphandler.fix()
    elif arguments[0] == 'missing':
        correct_sanctioned(arguments[2])
        dumphandler.print_missing(language=arguments[1], status=arguments[2])
    elif arguments[0] == 'collection':
        dumphandler.find_collections()
    elif arguments[0] == 'invalid':
        correct_sanctioned(arguments[2])
        dumphandler.print_invalid_chars(language=arguments[1],
                                        status=arguments[2])
    elif arguments[0] == 'sum':
        dumphandler.sum_terms(language=arguments[1])
    elif arguments[0] == 'auto':
        dumphandler.auto_sanction(language=arguments[1])
    elif arguments[0] == 'statistics':
        dumphandler.statistics(languages=arguments[1:])
    elif arguments[0] == 'sort':
        dumphandler.sort_dump()
    elif arguments[0] == 'merge_sdterms':
        dumphandler.merge_pages(pages_filename=arguments[1],
                                summary=arguments[2],
                                languages=['nb', 'sv', 'sma'])
    else:
        print(' '.join(arguments), 'is not supported')


def handle_site(arguments):
    """Act on the termwiki.

    Args:
        argument (str): command line argument
    """
    site = SiteHandler()
    if arguments[0] == 'fix':
        site.fix()
    elif arguments[0] == 'rev':
        site.fix_revisions()
    elif arguments[0] == 'query':
        site.add_extra_collection()
    elif arguments[0] == 'auto':
        site.auto_sanction(language=arguments[1])
    elif arguments[0] == 'revert':
        site.revert(page=arguments[1])
    elif arguments[0] == 'del_expression':
        site.del_expression()
    elif arguments[0] == 'improve_pagenames':
        site.improve_pagenames()
    elif arguments[0] == 'fix_expression_pages':
        site.fix_expression_pages()
    elif arguments[0] == 'delete_redirects':
        site.delete_redirects()
    elif arguments[0] == 'delete_pages':
        site.delete_pages(arguments[1])
    elif arguments[0] == 'merge_sdterms':
        site.merge_pages(pages_filename=arguments[1],
                         summary=arguments[2],
                         languages=['nb', 'sv', 'sma'])
    else:
        print(' '.join(arguments), 'is not supported')


def main():
    """Either fix a TermWiki site or test fixing routines on dump.xml."""
    if len(sys.argv) > 2:
        if sys.argv[1] == 'dump':
            handle_dump(sys.argv[2:])
        else:
            handle_site(sys.argv[2:])
    else:
        print('Usage:\ntermbot site to fix the TermWiki\n'
              'termbot test to run a test on dump.xml')
