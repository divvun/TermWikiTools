# -*- coding: utf-8 -*-
"""Bot to fix syntax blunders in termwiki articles."""
import collections
import json
import os
import sys
import uuid
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
    'Beaivvalaš giella',
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


def delete_sdterm(sd_title, termfiles):
    for filename in termfiles:
        if filename.endswith('termcenter.xml'):
            entry = termfiles[filename].find(f'.//entry[@id="{sd_title}"]')
            if entry is not None:
                entry.getparent().remove(entry)
        else:
            sense = termfiles[filename].find(f'.//sense[@idref="{sd_title}"]')
            if sense is not None:
                sense.getparent().remove(sense)


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
        not_found = collections.defaultdict(set)

        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            concept.print_missing(not_found, language)

        for real_expression in sorted(not_found):
            wanted = [f'{real_expression}:{real_expression} TODO ! ']
            for title in not_found[real_expression]:
                wanted.append(
                    f'https://satni.uit.no/termwiki/index.php?title={title.replace(" ", "_")}'
                )
            print(''.join(wanted))

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

        def make_termcenter():
            termcenter = etree.Element('r', nsmap=NSMAP)
            termcenter.attrib['id'] = 'termwiki'

            for title, content_elt in self.content_elements:
                concept = read_termwiki.Concept()
                concept.title = title
                concept.from_termwiki(content_elt.text)

                if concept.has_sanctioned_sami():
                    termcenter.append(concept.termcenter_entry)

            write_termfile('termcenter', termcenter)

        def make_termfiles():
            terms = {}
            for title, content_elt in self.content_elements:
                concept = read_termwiki.Concept()
                concept.title = title
                concept.from_termwiki(content_elt.text)
                if concept.has_sanctioned_sami():
                    for e_entry in concept.related_expressions:
                        lang = e_entry.get('language')
                        if lang and e_entry.get('sanctioned') == 'True':
                            if terms.get(lang) is None:
                                terms[lang] = collections.defaultdict(set)

                            terms[lang]['{}\\{}'.format(
                                e_entry['expression'],
                                e_entry['pos'])].add(title)

            turms = {}
            for lang in terms:
                if not turms.get(lang):
                    turms[lang] = etree.Element('r', nsmap=NSMAP)
                    turms[lang].attrib['id'] = 'termwiki'

                for id in terms[lang]:
                    entry = etree.Element('e')
                    entry.attrib['id'] = id

                    lg = etree.SubElement(entry, 'lg')
                    l = etree.SubElement(lg, 'l')
                    l.text, l.attrib['pos'] = id.split('\\')

                    status = etree.SubElement(entry, 'status')
                    sanctioned = etree.SubElement(entry, 'sanctioned')
                    sanctioned.text = 'True'

                    for title in sorted(terms[lang][id]):
                        mg = etree.SubElement(entry, 'mg')
                        mg.attrib['idref'] = title

                        xi = etree.SubElement(mg, XI + 'include', nsmap=NSMAP)
                        xi.attrib[
                            'xpointer'] = "xpointer(//e[@id='{}']/tg)".format(
                                title)
                        xi.attrib['href'] = 'termcenter.xml'

                    turms[lang].append(entry)

            for lang in turms:
                if lang:
                    write_termfile('terms-{}'.format(lang), turms[lang])

        make_termcenter()
        make_termfiles()

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

    def print_expression_pairs(self, lang1, lang2):
        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
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
                    print('{}\t{}'.format(', '.join(langs[lang1]),
                                          ', '.join(langs[lang2])))

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

    def merger(self, merge_candidate):
        site = self.get_site()

        termwiki, uxpresssions = self.dump2xml()
        old_id = collections.defaultdict(set)  #

        for concept in termwiki.xpath(
                './/collection[text()="Collection:SosDearv_sánit_SD"]/../..'):
            old_id[self.uff_key(concept)].add(concept.get('id'))

        expressions = termwiki.find('./expressions')

        x = 0
        z = 0

        for page in etree.parse(merge_candidate).iter('page'):
            z += 1
            concept = read_termwiki.Concept()
            concept.from_termwiki(page.find('.//concept').text)
            print(z)
            xml_concept = etree.Element('concept')
            self.concept2xml(concept, xml_concept, uxpresssions, expressions)

            a = self.uff_key(xml_concept)
            if a in old_id.keys():
                x += 1
                site_page = site.Pages[old_id[a]]
                site_page.save(
                    page.find('.//concept').text,
                    summary='Update SosDearv sánit SD collection')
                print(f'boaris {old_id[a]}')
            else:
                new_title = f"Servodatdieđa:{concept.data['related_expressions'][0]['expression']}"
                my_title = new_title
                site_page = site.Pages[my_title]
                y = 0
                while site_page.exists:
                    my_title = '{} {}'.format(new_title, y)
                    site_page = site.pages[my_title]
                    y += 1
                print(f'ođđa {my_title}')
                site_page.save(
                    page.find('.//concept').text,
                    summary='Update SosDearv sánit SD collection')

        print(x)
        #with open('termwiki.xml', 'wb') as term_stream:
        #term_stream.write(etree.tostring(termwiki, encoding='utf-8', pretty_print=True))

    @staticmethod
    def concept2xml(concept, xml_concept, expression_dict, expressions):
        """Append the different parts of a concept into an xml_concept."""
        for con_xml in concept.concept_xml():
            xml_concept.append(con_xml)

        for rel_con in concept.related_concepts_xml():
            xml_concept.append(rel_con)

        for con_inf in concept.concept_info_xml():
            xml_concept.append(con_inf)

        for related_expression, exp in concept.related_expressions_xml():
            expression_key = json.dumps(sorted(exp.items()))

            if expression_key not in expression_dict:
                expression_ref = str(uuid.uuid4())
                expression_dict[expression_key] = expression_ref
                expression = etree.Element('expression')
                expression.set(f'{XML}lang', exp['language'])
                expression.set('pos', exp['pos'])
                expression.set('string', exp['expression'])
                expression.set('id', str(expression_ref))
                expressions.append(expression)

            related_expression.set('expression_ref',
                                   expression_dict[expression_key])
            xml_concept.append(related_expression)

    def dump2xml(self):
        """Turn semantic wiki concepts from dump into xml."""
        termwiki = etree.Element('termwiki', nsmap=NSMAP)
        expression_dict = {}

        expressions = etree.SubElement(termwiki, 'expressions')
        concepts = etree.SubElement(termwiki, 'concepts')

        for title, content_elt in self.content_elements:
            concept = read_termwiki.Concept()
            concept.from_termwiki(content_elt.text)

            xml_concept = etree.SubElement(concepts, 'concept')
            xml_concept.set('id', title)

            self.concept2xml(concept, xml_concept, expression_dict,
                             expressions)

        return termwiki, expression_dict


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
            site = mwclient.Site('satni.uit.no', path='/termwiki/')
            site.login(config['username'], config['password'])

            print('Logging in to query …')

            return site

    @property
    def content_elements(self):
        """Get the concept pages in the TermWiki.

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

    def remove_paren(self, old_title: str) -> str:
        """Remove parenthesis from termwiki page name.

        Args:
            old_title: a title containing a parenthesis

        Returns:
            A new unique page name without parenthesis
        """
        new_title = old_title[:old_title.find('(')].strip()
        my_title = new_title
        x = 1
        page = self.site.pages[my_title]
        while page.exists:
            my_title = '{} {}'.format(new_title, x)
            page = self.site.pages[my_title]
            x += 1

        return my_title

    def move_page(self, old_name: str, new_name: str) -> None:
        """Move a termwiki page from old to new name."""
        orig_page = self.site.pages[old_name]
        try:
            print('Moving from {orig_page.name} to {new_name}'.format(
                orig_page.name, new_name))
            orig_page.move(
                new_name,
                reason='Remove parenthesis from page names',
                no_redirect=True)
        except mwclient.errors.InvalidPageTitle as error:
            print(old_name, error, file=sys.stderr)

    def improve_pagenames(self) -> None:
        """Remove characters that break eXist search from page names."""
        for page in self.content_elements:
            my_title = read_termwiki.fix_sms(
                self.remove_paren(page.name) if '(' in page.name else page.
                name)
            if page.name != my_title:
                self.move_page(page.name, my_title)

    def read_sdterm(self):
        termfiles = {}
        title_index = {}
        expression_index = collections.defaultdict(set)
        # Change the given languages to something wikimedia digests
        langs = {
            'eng': 'en',
            'fin': 'fi',
            'lat': 'lat',
            'nor': 'nb',
            'sma': 'sma',
            'sme': 'se',
            'smj': 'smj',
            'smn': 'smn',
            'sms': 'sms',
            'swe': 'sv',
        }

        # Change the pos element to the ones found in $GTHOME/gt/sme/src
        pos = {
            'A': 'A',
            'Adjektiv': 'A',
            'a': 'A',
            'ABBR': 'ABBR',
            'Adv': 'Adv',
            'adv': 'Adv',
            'PP': 'N',
            'Pron': 'Pron',
            'S': 'N',
            's': 'N',
            'd': 'N',
            'V': 'V',
            'v': 'V',
        }

        srcdir = os.path.join(
            os.getenv('GTHOME'), 'words/terms/SD-terms/newsrc')

        filename = f'{srcdir}/termcenter.xml'
        termfiles[filename] = etree.parse(filename)
        blacklist = [
            entry.get('id') for entry in termfiles[filename].iter('entry')
            if len(entry.xpath('.//entryref')) < 2
        ]
        for entry_id in blacklist:
            entry = termfiles[filename].find(f'.//entry[@id="{entry_id}"]')
            entry.getparent().remove(entry)

        for lang in langs:
            filename = f'{srcdir}/terms-{lang}.xml'
            termfiles[filename] = etree.parse(filename)
            for sense in termfiles[filename].iter('sense'):
                identifier = sense.get('idref')
                if identifier in blacklist:
                    sense.getparent().remove(sense)
                else:
                    concept = title_index.get(identifier,
                                              read_termwiki.Concept())

                    definition = sense.find('.//def')
                    if definition is not None and definition.text is not None:
                        concept.data['concept_infos'].append({
                            'language':
                            langs[lang],
                            'definition':
                            ' '.join(definition.text.split())
                        })

                    head = sense.getparent().getparent().find('.//head')
                    expression = {
                        'pos': pos[head.get('pos')],
                        'language': langs[lang],
                        'expression': head.text,
                        'sanctioned': 'True'
                    }
                    key = '_'.join(
                        [expression['expression'], expression['language']])
                    expression_index[key].add(identifier)
                    concept.clean_up_expression(expression)

                    title_index[identifier] = concept

        return title_index, expression_index, termfiles

    @staticmethod
    def print_entry(title, index):
        if ':' not in title:
            print(f'\n==={title}===')
        else:
            print(title)
        print('\t'.join([
            ' '.join([concept_info['definition'], concept_info['language']])
            for concept_info in index[title].data['concept_infos']
        ]))
        print('\t'.join([
            ' '.join([
                related_expression['expression'],
                related_expression['language'], related_expression['pos']
            ]) for related_expression in index[title].related_expressions
        ]))

    def merge_concept(self, concept, main_title):
        concept.data['concept']['collection'] = set()
        concept.data['concept']['collection'].add('Collection:SD-terms')

        page = self.site.Pages[main_title]
        self.save_page(
            page, str(concept), summary='Merging content from SD-terms')

    @staticmethod
    def write_termfiles(termfiles):
        for termfilename in termfiles:
            with open(termfilename, 'wb') as turm:
                turm.write(
                    etree.tostring(
                        termfiles[termfilename],
                        pretty_print=True,
                        encoding='utf8',
                        xml_declaration=True))

    def merge_sdterms(self):
        """Find all expressions of the given language.

        Args:
            language (src): language of the terms.

        Yields:
            tuple: an expression, the collections and the title of a
                given concept.
        """
        tw_expression_index = collections.defaultdict(set)
        tw_index = {}

        dumphandler = DumpHandler()

        for title, content_elt in dumphandler.content_elements:
            title = title.replace(' ', '_')
            concept = read_termwiki.Concept()
            concept.title = title
            concept.from_termwiki(content_elt.text)
            tw_index[title] = concept

            for expression in concept.related_expressions:
                key = '_'.join(
                    [expression['expression'], expression['language']])
                tw_expression_index[key].add(title)

        sd_index, sd_expression_index, termfiles = self.read_sdterm()

        for expression in sd_expression_index:
            if expression in tw_expression_index:
                print(f'Expression: {expression}\n')
                for sd_title in sd_expression_index[expression]:
                    try:
                        self.print_entry(sd_title, sd_index)
                        for tw_title in tw_expression_index[expression]:
                            self.print_entry(tw_title, tw_index)
                        main_title = input('merge to: ')

                        if main_title == 'q':
                            self.write_termfiles(termfiles)
                            raise SystemExit('quitting')
                        elif main_title == 'd':
                            try:
                                delete_sdterm(sd_title, termfiles)
                            except Exception as error:
                                print(str(error))
                        elif main_title:
                            self.merge_concept(sd_index[sd_title],
                                               main_title.replace('_', ' '))
                            delete_sdterm(sd_title, termfiles)
                            self.write_termfiles(termfiles)
                        else:
                            print(f'Not merging {sd_title}')
                    except Exception as error:
                        self.write_termfiles(termfiles)
                        raise SystemExit('quitting', str(error))


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
    elif arguments[0] == 'new_xml':
        dumphandler.merger(merge_candidate=arguments[1])
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
    elif arguments[0] == 'improve_pagenames':
        site.improve_pagenames()
    elif arguments[0] == 'merge_sdterms':
        site.merge_sdterms()
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
