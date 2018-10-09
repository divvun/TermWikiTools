# -*- coding: utf-8 -*-
"""Bot to fix syntax blunders in termwiki articles."""

import collections
import os
import sys
from datetime import date

import mwclient
import yaml
from lxml import etree

from termwikiimporter import read_termwiki

XI_NAMESPACE = 'http://www.w3.org/2001/XInclude'
XML_NAMESPACE = 'https://www.w3.org/XML/1998/namespace'
XI = '{%s}' % XI_NAMESPACE
XML = '{%s}' % XML_NAMESPACE
NSMAP = {'xi': XI_NAMESPACE, 'xml': XML_NAMESPACE}
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
    'Religion',
    'Teknihkka industriija duodji',
    'Álšateknihkka',
    'Ásttoáigi ja faláštallan',
    'Ávnnasindustriija',
]


class DumpHandler(object):
    """Class that involves using the TermWiki dump.

    Attributes:
        termwiki_xml_root (str): path where termwiki xml files live.
        dump (str): path to the dump file.
        tree (etree.ElementTree): the parsed dump file.
        mediawiki_ns (str): the mediawiki name space found in the dump file.
    """

    termwiki_xml_root = os.path.join(
        os.getenv('GTHOME'), 'words/terms/termwiki')
    dump = os.path.join(termwiki_xml_root, 'dump.xml')
    tree = etree.parse(dump)
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'

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

    def print_missing(self, language=None):
        """Find all expressions of the given language.

        Args:
            language (src): language of the terms.

        Yields:
            tuple: an expression, the collections and the title of a
                given concept.
        """
        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            concept.print_missing(language)

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

        self.tree.write(self.dump, pretty_print=True, encoding='utf8')

    def sum_terms(self, language=None):
        """Sum up sanctioned and none sanctioned terms.

        Args:
            language (str): the language to report on.
        """
        counter = collections.defaultdict(int)
        for _, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(content_elt.text)

            for expression in concept.related_expressions:
                if expression['language'] == language:
                    counter[expression['sanctioned']] += 1

        print('{}: {}: true, {}: false, {}: total'.format(
            language, counter['true'], counter['false'],
            counter['false'] + counter['true']))

    def print_invalid_chars(self, language):
        """Find terms with invalid characters, print the errors to stdout."""
        invalids = collections.defaultdict(int)

        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(content_elt.text)

            for expression in concept.find_invalid(language):
                invalids[language] += 1
                print('{} https://satni.uit.no/termwiki/index.php/{}'.format(
                    expression, title))

        for language, number in invalids.items():
            print(language, number)

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
                    print(title, etree.tostring(
                        content_elt, encoding='unicode'))

    def to_termcenter(self):
        def sort_by_id(termroot):
            return sorted(termroot, key=lambda child: child.get('id'))

        def write_termfile(filename, root_element):
            path = os.path.join(self.termwiki_xml_root,
                                'terms/{}.xml'.format(filename))
            with open(path, 'wb') as termstream:
                root_element[:] = sort_by_id(root_element)
                termstream.write(
                    etree.tostring(
                        root_element,
                        encoding='utf-8',
                        pretty_print=True,
                        xml_declaration=True))

        termcenter = etree.Element('r', nsmap=NSMAP)
        termcenter.attrib['id'] = 'termwiki'
        termcenter.attrib['timestamp'] = str(date.today())
        terms = {}

        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)

            termcenter.append(concept.termcenter_entry)

            for lang, e_entry in concept.terms_entries:
                if terms.get(lang) is None:
                    terms[lang] = etree.Element('r', nsmap=NSMAP)
                    terms[lang].attrib['id'] = 'termwiki'
                    terms[lang].attrib['timestamp'] = str(date.today())

                terms[lang].append(e_entry)

        write_termfile('termcenter', termcenter)

        for lang in terms:
            if lang:
                write_termfile('terms-{}'.format(lang), terms[lang])

    def sort_dump(self):
        root = self.tree.getroot()
        namespace = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}

        pages = root.xpath('.//mw:page', namespaces=namespace)
        pages[:] = sorted(
            pages,
            key=lambda page: page.find('./mw:title', namespaces=namespace).text
        )

        for page in root.xpath('.//mw:page', namespaces=namespace):
            page.getparent().remove(page)

        for page in pages:
            root.append(page)

        self.tree.write(self.dump, pretty_print=True, encoding='utf-8')


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
        config_file = os.path.join(
            os.getenv('HOME'), '.config', 'term_config.yaml')
        with open(config_file) as config_stream:
            config = yaml.load(config_stream)
            site = mwclient.Site(('http', 'localhost'), path='/termwiki/')
            site.login(config['username'], config['password'])

            print('Logging in to query …')

            return site

    @property
    def content_elements(self):
        """Get the concept pages in the TermWiki.

        Args:
            site (mwclient.Site): A site object.

        Yields:
            mwclient.Page
        """
        for category in self.site.allcategories():
            if category.name.replace('Kategoriija:', '') in NAMESPACES:
                print(category.name)
                for page in category:
                    if self.is_concept_tag(page.text()):
                        yield page
                print()

    def del_expression(self):
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

    def fix(self):
        """Make the bot fix all pages."""
        counter = collections.defaultdict(int)

        for page in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(page.text())
            self.save_page(page, str(concept), summary='Fixing content')

        for key in sorted(counter):
            print(key, counter[key])

    def query_replace_text(self):
        u"""Do a semantic media query and fix pages.

        Change the query and the actions when needed …

        http://mwclient.readthedocs.io/en/latest/reference/site.html#mwclient.client.Site.ask
        https://www.semantic-mediawiki.org/wiki/Help:API
        """
        query = ('[[Related expression::+]]'
                 '[[Language::{}]]'
                 '[[Sanctioned::False]]'.format(language))

        for number, answer in enumerate(self.site.ask(query), start=1):
            for title, _ in answer.items():
                page = self.site.Pages[title]
                concept = read_termwiki.Concept()
                concept.from_termwiki(page.text())
                if concept.collections is None:
                    print('Hit no: {}, title: {}'.format(number, title))
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

        for number, answer in enumerate(self.site.ask(query), start=1):
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

    def revert(self, page):
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
                self.site.api(
                    'rollback',
                    title=page.name,
                    user='SDTermImporter',
                    summary='Use Stempage in Related expression',
                    markbot='1',
                    token=rollback_token)
            except mwclient.errors.APIError as error:
                print(page.name, error)


def handle_dump(arguments):
    """Act on the TermWiki dump.

    Args:
        argument (str): command line argument
    """
    dumphandler = DumpHandler()

    if arguments[0] == 'fix':
        dumphandler.fix()
    elif arguments[0] == 'missing':
        dumphandler.print_missing(language=arguments[1])
    elif arguments[0] == 'collection':
        dumphandler.find_collections()
    elif arguments[0] == 'invalid':
        dumphandler.print_invalid_chars(language=arguments[1])
    elif arguments[0] == 'sum':
        dumphandler.sum_terms(language=arguments[1])
    elif arguments[0] == 'auto':
        dumphandler.auto_sanction(language=arguments[1])
    elif arguments[0] == 'terms':
        dumphandler.to_termcenter()
    elif arguments[0] == 'sort':
        dumphandler.sort_dump()
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
    elif arguments[0] == 'query':
        site.query_replace_text()
    elif arguments[0] == 'auto':
        site.auto_sanction(language=arguments[1])
    elif arguments[0] == 'revert':
        site.revert(page=arguments[1])
    elif arguments[0] == 'del_expression':
        site.del_expression()
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
