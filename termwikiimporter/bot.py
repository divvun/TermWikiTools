# -*- coding: utf-8 -*-
"""Bot to fix syntax blunders in termwiki articles."""

import collections
import os
import re
import sys

import yaml
from lxml import etree

import mwclient
from termwikiimporter import read_termwiki
from corpustools import util

NAMESPACES = [
    'Boazodoallu',
    'Collection',
    'Dihtorteknologiija ja diehtoteknihkka',
    'Dáidda ja girjjálašvuohta',
    'Eanandoallu',
    'Education',
    'Ekologiija ja biras',
    'Ekonomiija ja gávppašeapmi',
    'Expression',
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
        dump (str): path to the dump file.
        tree (etree.ElementTree): the parsed dump file.
        mediawiki_ns (str): the mediawiki name space found in the dump file.
    """

    dump = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')
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

    def expressions(self, language):
        """Find all expressions of the given language.

        Arguments:
            language (src): language of the terms.

        Yields:
            tuple: an expression, the collections and the title of a
                given concept.
        """
        for title, page in self.pages:
            content_elt = page.find('.//{}text'.format(self.mediawiki_ns))
            if content_elt.text and '{{Concept' in content_elt.text:
                concept = read_termwiki.handle_page(content_elt.text)
                for expression in concept['related_expressions']:
                    if expression['language'] == language:
                        yield expression, concept['concept'].get(
                            'collection'), title

    def print_missing(self, language=None):
        """Print lemmas not found in the languages lexicon.

        Arguments:
            language (src): language of the terms.
        """
        runner = util.ExternalCommandRunner()
        command = 'hfst-lookup --quiet {}'.format(
            os.path.join(
                os.getenv('GTHOME'), 'langs', language,
                'src/analyser-gt-norm.hfstol'))

        for expression, term_collections, title in self.expressions(language):
            runner.run(
                command.split(), to_stdin=bytes(expression, encoding='utf8'))

            if b'?' in runner.stdout:
                wanted = []
                wanted.append('{0}:{0} TermWiki ; !'.format(
                    expression['expression']))

                if term_collections:
                    for collection in term_collections:
                        wanted.append('«{}»'.format(collection))

                wanted.append('«{}»'.format(title))

                print(' '.join(wanted))

    def auto_confirm_term(self, language):
        runner = util.ExternalCommandRunner()
        command = 'hfst-lookup --quiet {}'.format(
            os.path.join(
                os.getenv('GTHOME'), 'langs', language,
                'src/analyser-gt-norm.hfstol'))

        hits = collections.defaultdict(int)
        for title, page in self.pages:
            content_elt = page.find('.//{}text'.format(self.mediawiki_ns))
            if content_elt.text and '{{Concept' in content_elt.text:
                concept = read_termwiki.handle_page(content_elt.text)
                for expression in concept['related_expressions']:
                    if expression['language'] == language:
                        runner.run(
                            command.split(),
                            to_stdin=bytes(
                                expression['expression'], encoding='utf8'))
                        hits['total'] += 1

                        if b'?' not in runner.stdout and concept['concept'].get(
                                'collection'
                        ) is None and expression['sanctioned'] == 'False':
                            hits['sanction'] += 1
                            print(hits)
                            expression['sanctioned'] = 'True'
                            ct = read_termwiki.term_to_string(
                                concept)
                            content_elt.text = ct

        self.tree.write(self.dump, pretty_print=True, encoding='utf8')
        print(language, hits)

    def sum_terms(self, language=None):
        counter = collections.defaultdict(int)
        for expression, term_collections, title in self.expressions(language):
            if expression.get(
                    'sanctioned') and expression['sanctioned'] == 'True':
                counter['true'] += 1
            else:
                counter['false'] += 1

        print('{}: {}: true, {}: false, {}: total'.format(
            language, counter['true'], counter['false'],
            counter['false'] + counter['true']))

    def print_invalid_chars(self):
        invalids = collections.defaultdict(int)
        invalid_chars_re = re.compile(r'[,\(\)]')

        for language in [
                'en', 'fi', 'lat', 'nb', 'nn', 'se', 'sma', 'smj', 'smn', 'sms'
        ]:
            for expression, _, title in self.expressions(language):
                if invalid_chars_re.search(expression['expression']):
                    invalids[language] += 1
                    print(
                        '{} https://satni.uit.no/termwiki/index.php/{}'.format(
                            expression['expression'], title))

        for language, number in invalids.items():
            print(language, number)

    def fix_dump(self):
        """Check to see if everything works as expected."""
        for title, page in self.pages:
            content_elt = page.find('.//{}text'.format(self.mediawiki_ns))
            try:
                if '{{Concept' in content_elt.text:
                    content_elt.text = read_termwiki.term_to_string(
                        read_termwiki.handle_page(content_elt.text))
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


def get_site():
    """Get a mwclient site object.

    Returns:
        mwclient.Site
    """
    config_file = os.path.join(
        os.getenv('HOME'), '.config', 'term_config.yaml')
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


def is_concept_tag(content):
    """Check if content is a TermWiki Concept page.

    Args:
        content (str): content of a TermWiki page.

    Returns:
        bool
    """
    return ('{{Concept' in content and ('{{Related expression' in content
                                        or '{{Related_expression' in content))


def write_expressions(expressions, site):
    """Make Expression pages.

    Args:
        expressions (list of importer.OrderDefaultDict): The expressions found
            in the Concept page.
        site (mwclient.Site): The site object
    """
    for expression in expressions:
        page = site.Pages['Expression:{}'.format(expression['expression'])]
        if not page.exists:
            print('Creating page: {}'.format(page.name))
            page.save(
                to_page_content(expression),
                summary='Creating new Expression page')
        else:
            existings = parse_expression(page.text(), expression['expression'])
            for existing in existings:
                try:
                    if (existing['language'] == expression['language']
                            and existing['pos'] == expression['pos']):
                        break
                except TypeError:
                    print(existing, expression)
                    sys.exit(18)
            else:
                existings.append({
                    'language': expression['language'],
                    'pos': expression['pos']
                })

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
    text_lines.extend(
        ['|{}={}'.format(key, expression[key]) for key in expression])
    text_lines.append('}}')

    return '\n'.join(text_lines)


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

            write_expressions(concept['related_expressions'], site)

    for key in sorted(counter):
        print(key, counter[key])


def query_and_fix():
    u"""Do a semantic media query and fix pages.

    Change the query and the actions when needed …

    http://mwclient.readthedocs.io/en/latest/reference/site.html#mwclient.client.Site.ask
    https://www.semantic-mediawiki.org/wiki/Help:API
    """
    print('Logging in to query …')
    site = get_site()

    query = ('[[Category:Servodatdieđa]]|'
             '[[Collection::Collection:arbeidsliv_godkjent_av_termgr]]')
    for number, answer in enumerate(site.ask(query), start=1):
        for title, _ in answer.items():
            print('Hit no: {}, title: {}'.format(number, title))
            page = site.Pages[title]
            concept = read_termwiki.handle_page(page.text())
            new_text = read_termwiki.term_to_string(concept)
            try:
                page.save(
                    new_text.replace('|language=sma', '|language=se'),
                    summary='This is North Saami, not South Saami')
            except mwclient.errors.APIError as error:
                print(page.name, new_text, str(error), file=sys.stderr)


def handle_dump(arguments):
    """Act on the TermWiki dump.

    Arguments:
        argument (str): command line argument
    """
    dumphandler = DumpHandler()

    if arguments[0] == 'test':
        dumphandler.fix_dump()
    elif arguments[0] == 'missing':
        dumphandler.print_missing(language=arguments[1])
    elif arguments[0] == 'collection':
        dumphandler.find_collections()
    elif arguments[0] == 'invalid':
        dumphandler.print_invalid_chars()
    elif arguments[0] == 'sum':
        dumphandler.sum_terms(language=arguments[1])
    elif arguments[0] == 'auto':
        dumphandler.auto_confirm_term(language=arguments[1])


def handle_site(argument):
    """Act on the termwiki.

    Arguments:
        argument (str): command line argument
    """
    if argument == 'site':
        fix_site()
    elif argument == 'query':
        query_and_fix()


def main():
    """Either fix a TermWiki site or test fixing routines on dump.xml."""
    if len(sys.argv) > 1:
        if sys.argv[1] in [
                'test', 'missing', 'collection', 'invalid', 'sum', 'auto'
        ]:
            handle_dump(sys.argv[1:])
        else:
            handle_site(sys.argv[1])
    else:
        print('Usage:\ntermbot site to fix the TermWiki\n'
              'termbot test to run a test on dump.xml')
