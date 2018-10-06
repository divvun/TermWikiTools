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
#   Copyright © 2016-2018 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Read termwiki pages."""

import inspect
import re
from operator import itemgetter
from lxml import etree

from termwikiimporter import analyser
from termwikiimporter.ordereddefaultdict import OrderedDefaultDict


XI_NAMESPACE = 'http://www.w3.org/2001/XInclude'
XML_NAMESPACE = 'https://www.w3.org/XML/1998/namespace'
XI = '{%s}' % XI_NAMESPACE
XML = '{%s}' % XML_NAMESPACE
NSMAP = {'xi': XI_NAMESPACE, 'xml': XML_NAMESPACE}


def lineno():
    """Return the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


class Concept(object):
    """Class that represents a TermWiki concept."""

    def __init__(self):
        """Initialise the Concept class."""
        self.title = ''
        self.data = {
            'concept': {},
            'concept_infos': [],
            'related_expressions': [],
            'related_concepts': []
        }

    @property
    def related_expressions(self):
        """Get related_expressions."""
        return self.data['related_expressions']

    @property
    def collections(self):
        """Get collections."""
        return self.data['concept'].get('collection')

    def clean_up_concept(self):
        """Clean up concept data."""
        if self.data['concept'].get('language'):
            del self.data['concept']['language']
        if self.data['concept'].get('collection'):
            self.data['concept']['collection'] = set([
                self.fix_collection_line(concept)
                for concept in self.data['concept']['collection'].split('@@')
            ])

    def clean_up_expression(self, expression):
        """Clean up expression."""
        if 'expression' in expression:
            if (('sanctioned' in expression
                 and expression['sanctioned'] == 'No')
                    or 'sanctioned' not in expression):
                expression['sanctioned'] = 'False'
            if ('sanctioned' in expression
                    and expression['sanctioned'] == 'Yes'):
                expression['sanctioned'] = 'True'

            if ' ' in expression['expression']:
                expression['pos'] = 'mwe'

            if 'collection' in expression:
                if not self.data.get('collection'):
                    self.data['concept']['collection'] = set()
                self.data['concept']['collection'].add(
                    expression['collection'].replace('_', ' '))
                del expression['collection']

            self.data['related_expressions'].append(expression)

    def from_termwiki(self, text):
        """Parse a termwiki page.

        Args:
            text (str): content of the termwiki page.
            counter (collections.defaultdict(int)): keep track of things

        Returns:
            dict: contains the content of the termwiki page.
        """
        text_iterator = iter(text.splitlines())

        for line in text_iterator:
            line = line.replace('\xa0', ' ').strip()  # replace nbsp
            if self.is_empty_template(line):
                continue

            elif line.startswith('{{Concept info'):
                self.data['concept_infos'].append(
                    self.read_semantic_form(text_iterator))

            elif line.startswith('{{Concept'):
                self.data['concept'] = self.read_semantic_form(text_iterator)
                self.clean_up_concept()

            elif self.is_related_expression(line):
                expression = self.read_semantic_form(text_iterator)
                self.clean_up_expression(expression)

            elif line.startswith('{{Related'):
                self.data['related_concepts'].append(
                    self.read_semantic_form(text_iterator))

        self.to_concept_info()

    def to_concept_info(self):
        """Turn old school Concept to new school Concept.

        Args:
            term (dict): A representation of a TermWiki Concept
        """
        langs = {}
        concept = {}
        concept.update(self.data['concept'])

        if concept:
            for key in list(concept.keys()):
                pos = key.rfind('_')
                if pos > 0:
                    lang = key[pos + 1:]
                    if lang in [
                            'se', 'sv', 'fi', 'en', 'nb', 'nn', 'sma', 'smj',
                            'smn', 'sms', 'lat'
                    ]:
                        if not langs.get(lang):
                            langs[lang] = {}
                            langs[lang]['language'] = lang
                        new_key = key[:pos]
                        langs[lang][new_key] = concept[key]
                        del concept[key]

        self.data['concept'] = concept
        for lang in langs:
            self.data['concept_infos'].append(langs[lang])

    @staticmethod
    def read_semantic_form(text_iterator):
        """Turn a template into a dict.

        Args:
            text_iterator (str_iterator): the contents of the termwiki article.

        Returns:
            importer.OrderedDefaultDict
        """
        wiki_form = OrderedDefaultDict()
        wiki_form.default_factory = str
        for line in text_iterator:
            if line == '}}':
                return wiki_form
            elif line.startswith('|reviewed=') or line.startswith(
                    '|is_typo') or line.startswith(
                        '|has_illegal_char') or line.startswith(
                            '|in_header') or line.startswith('|no picture'):
                pass
            elif line.startswith('|'):
                equality = line.find('=')
                key = line[1:equality]
                if line[equality + 1:]:
                    wiki_form[key] = line[equality + 1:].strip()
            else:
                wiki_form[key] = '\n'.join([wiki_form[key], line.strip()])

    @staticmethod
    def is_empty_template(line):
        """Check if a line represents an empty template."""
        return (line == '{{Related expression}}' or line == '{{Concept info}}'
                or line == '{{Concept}}')

    @staticmethod
    def fix_collection_line(line):
        """Add Collection: to collection line if needed.

        Args:
            line (str): a line found in a termwiki page.

        Returns:
            str
        """
        if 'Collection:' not in line:
            return '{}:{}'.format('Collection', line)
        else:
            return line

    @staticmethod
    def is_related_expression(line):
        """Check if line is the start of a TermWiki Related expression.

        Args:
            line (str): TermWiki line

        Returns:
            bool
        """
        return (line.startswith('{{Related expression')
                or line.startswith('{{Related_expression'))

    def concept_info_str(self, term_strings):
        """Append concept_info to a list of strings."""
        for concept_info in sorted(
                self.data['concept_infos'], key=itemgetter('language')):
            term_strings.append('{{Concept info')
            for key in ['language', 'definition', 'explanation', 'more_info']:
                if concept_info.get(key):
                    term_strings.append('|{}={}'.format(
                        key, concept_info[key]))
            term_strings.append('}}')

    def related_expressions_str(self, term_strings):
        """Append related_expressions to a list of strings."""
        for expression in self.related_expressions:
            term_strings.append('{{Related expression')
            for key, value in expression.items():
                term_strings.append('|{}={}'.format(key, value))
            term_strings.append('}}')

    def related_concepts_str(self, term_strings):
        """Append related_concepts to a list of strings."""
        if self.data.get('related_concepts'):
            for related_concept in self.data['related_concepts']:
                term_strings.append('{{Related concept')
                for key, value in related_concept.items():
                    term_strings.append('|{}={}'.format(key, value))
                term_strings.append('}}')

    def concept_str(self, term_strings):
        """Append concept to a list of strings."""
        if self.data['concept']:
            term_strings.append('{{Concept')
            for key, value in self.data['concept'].items():
                if key == 'collection':
                    term_strings.append('|{}={}'.format(
                        key, '@@ '.join(value)))
                else:
                    term_strings.append('|{}={}'.format(key, value))
            term_strings.append('}}')
        else:
            term_strings.append('{{Concept}}')

    def __str__(self):
        """Turn a term dict into a semantic wiki page.

        Args:
            term (dict): the result of clean_up_concept

        Returns:
            str: term formatted as a semantic wiki page.
        """
        term_strings = []
        self.concept_info_str(term_strings)
        self.related_expressions_str(term_strings)
        self.related_concepts_str(term_strings)
        self.concept_str(term_strings)

        return '\n'.join(term_strings)

    @property
    def category(self):
        colon = self.title.find(':')
        return self.title[:colon]

    @property
    def termcenter_entry(self):
        """Turn a concept info a termcenter entry."""
        entry = etree.Element('e')
        entry.attrib['id'] = self.title
        entry.attrib['category'] = self.category

        for expression in self.related_expressions:
            translation_group = etree.SubElement(entry, 'tg')
            translation_group.attrib[XML + 'lang'] = expression['language']

            translation = etree.SubElement(translation_group, 't')
            translation.attrib['pos'] = expression['pos']

            xi = etree.SubElement(translation, XI + 'include', nsmap=NSMAP)
            xi.attrib['href'] = 'terms-{}.xml'.format(expression['language'])
            xi.attrib['xpointer'] = "xpointer(//e[@id='{}\\{}']/lg/l/text())".format(expression['expression'], expression['pos'])

        return entry

    @property
    def terms_entries(self):
        def make_entry(expression):
            entry = etree.Element('e')
            entry.attrib['id'] = '{}\\{}'.format(expression['expression'], expression['pos'])

            lg = etree.SubElement(entry, 'lg')
            l = etree.SubElement(lg, 'l')
            l.attrib['pos'] = expression['pos']
            l.text = expression['expression']

            status = etree.SubElement(entry, 'status')
            if expression.get('status'):
                status.text = expression['status']

            sanctioned = etree.SubElement(entry, 'sanctioned')
            sanctioned.text = 'True'

            mg = etree.SubElement(entry, 'mg')
            mg.attrib['idref'] = self.title

            xi = etree.SubElement(mg, XI + 'include', nsmap=NSMAP)
            xi.attrib['xpointer'] = "xpointer(//e[@id='{}']/tg)".format(self.title)
            xi.attrib['href'] = 'termcenter.xml'

            return expression['language'], entry

        return [make_entry(expression)
                for expression in self.related_expressions
                if expression['sanctioned'] and expression.get('language') is not None]

    def auto_sanction(self, language):
        """Automatically sanction expressions in the given language.

        Args:
            language (str): the language to handle
        """
        for expression in self.related_expressions:
            if expression['language'] == language:
                if (analyser.is_known(language, expression['expression'])
                        and expression['sanctioned'] == 'False'):
                    expression['sanctioned'] = 'True'

    def print_missing(self, language=None):
        """Print lemmas not found in the languages lexicon.

        Args:
            language (src): language of the terms.
        """
        for expression in self.related_expressions:
            if expression['language'] == language:
                if analyser.is_known(language, expression['expression']):
                    wanted = []
                    wanted.append('{0}:{0} TermWiki ; !'.format(
                        expression['expression']))

                    if self.collections:
                        for collection in self.collections:
                            wanted.append('«{}»'.format(collection))

                    wanted.append('«{}»'.format(self.title))

                    print(' '.join(wanted))

    def find_invalid(self, language):
        """Find expressions with invalid characters.

        Args:
            language (str): the language of the expressions

        Yields:
            str: an offending expression
        """
        invalid_chars_re = re.compile(r'[,\(\)]')

        for expression in self.related_expressions:
            if expression['language'] == language:
                if invalid_chars_re.search(expression['expression']):
                    yield expression['expression']
