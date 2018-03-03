# -*- coding: utf-8 -*-
"""Import/convert term files to termwiki."""


import argparse
import os
import re
import sys
from collections import defaultdict, namedtuple
import yaml

from lxml import etree
import attr
import openpyxl

from termwikiimporter.ordereddefaultdict import OrderedDefaultDict
from termwikiimporter import read_termwiki


class ExpressionError(Exception):
    pass


@attr.s
class ExpressionInfo(object):
    """Information bound to an expression.

    Attributes:
        languge (str): Indicate which language the expression is.
        expression (str): The expression.
        pos (str): The part of speech
        status (str): Indicate if the expression is recommended, outdated,
            etc.
        sanctioned (boolean): Indicate whether norm groups have sanctioned
            the expression.
        note (str): Ad hoc note about the expression
        collection (str): Indicates which collection the expression belongs
            to.
        source (str): source of the expression
    """
    language = attr.ib('')
    expression = attr.ib('')
    pos = attr.ib('')
    status = attr.ib('')
    sanctioned = attr.ib(default='No')
    note = attr.ib('')
    collection = attr.ib('')
    source = attr.ib('')


class ExpressionInfos(object):

    """Collection of expressions.

    Attributes:
        expressions (list of ExpressionInfo):
        _pos (str): part of speech.
    """
    def __init__(self):
        self.expressions = []
        self._pos = 'N/A'

    def __str__(self):
        strings = []
        for expression in self.expressions:
            strings.append('{{Related expression')
            strings.append('|language={}'.format(expression.language))
            strings.append('|expression={}'.format(expression.expression))
            if ' ' in expression.expression:
                strings.append('|pos=MWE')
            elif expression.pos:
                strings.append('|pos={}'.format(expression.pos))
            else:
                strings.append('|pos={}'.format(self.pos))
            if expression.status:
                strings.append('|status={}'.format(expression.status))
            strings.append('|sanctioned={}'.format(expression.sanctioned))
            if expression.note:
                strings.append('|note={}'.format(expression.note))
            if expression.collection:
                strings.append('|collection={}'.format(expression.collection))
            if expression.source:
                strings.append('|source={}'.format(expression.source))
            strings.append('}}')

        return '\n'.join(strings)

    def add_expression(self, expression_info):
        """Add an expression.

        Arguments:
            expression_info (ExpressionInfo): The expression and its
                attributes.
        """
        if expression_info not in self.expressions:
            self.expressions.append(expression_info)

    def get_expressions_set(self, lang):
        """Get the expressions for a specific language.

        Arguments:
            lang (str): the language of the wanted expressions.

        Returns:
            set of ExpressionInfo: The expressions of the specified language.
        """
        return set(
            [e.expression for e in self.expressions
             if e.language == lang])

    @property
    def lang_set(self):
        """Get info on which languages are in self.expressions.

        Returns:
            set of str: each string represent a language.
        """
        return set([e.language for e in self.expressions])

    @property
    def is_empty(self):
        """True if there are no expression, otherwise false.

        Returns:
            boolean
        """
        return len(self.expressions) == 0

    @property
    def pos(self):
        """The part of speech.

        Returns:
            str
        """
        return self._pos

    @pos.setter
    def pos(self, pos):
        """Set the part of speech.

        Arguments:
            pos (str): The part of speech.
        """
        if pos not in ['N', 'A', 'Adv', 'V', 'Pron', 'CS', 'CC', 'Adp', 'Po',
                       'Pr', 'Interj', 'Pcle', 'Num', 'ABBR', 'MWE', 'N/A',
                       'A/N']:
            raise ExpressionError('Illegal value: {}'.format(pos))

        if pos in ['MWE', 'N/A']:
            return

        if self._pos == 'N/A':
            self._pos = pos
        elif self._pos != pos:
            raise ExpressionError('Trying to set conflicting pos {} {}'.format(
                self.pos, pos))


class RelatedConceptInfo(namedtuple('RelatedConceptInfo',
                                    ['concept', 'relation'])):
    __slots__ = ()

    def __str__(self):
        strings = ['{{Related concept']
        for key, value in list(self._asdict().items()):
            if value == '':
                pass
            else:
                strings.append('|' + key + '=' + value)

        strings.append('}}')

        return '\n'.join(strings)


class Concept(object):
    """Model the TermWiki concept.

    Attributes:
        main_category (str): the main category of the concept.
        concept_info (OrderedDefaultDict): The information that represents
            the concept.
        expression_infos (ExpressionInfos): The expression that represent
            this concept.
        related_concepts (list of RelatedConceptInfo): Information on
            related concepts.
        pages (set): TermWiki pages that may be duplicates of this concept.
    """

    def __init__(self, main_category=''):
        self.main_category = main_category
        self.concept_info = OrderedDefaultDict()
        self.concept_info.default_factory = set
        self.expression_infos = ExpressionInfos()
        self.related_concepts = []
        self.pages = set()

    def add_expression(self, expression_info):
        """Add an expression to the set.

        Arguments:
            expression_info (ExpressionInfo): The expression.
        """
        self.expression_infos.add_expression(expression_info)

    def add_related_concept(self, concept_info):
        """Add a related concept.

        Arguments:
            concept_info (ConceptInfo): The related concept.
        """
        if concept_info not in self.related_concepts:
            self.related_concepts.append(concept_info)

    def add_concept_info(self, key, info):
        """Add concept info.

        Arguments:
            key (str): The key to add info to.
            value (str): The information that should be added.
        """
        self.concept_info[key].add(info)

    def add_page(self, page):
        """Add a termwiki page.

        Arguments:
            page: A termwiki page.
        """
        self.pages.add(page)

    def get_expressions_set(self, lang):
        """Get the expression of a specific languge.

        Arguments:
            lang (str): the language of the wanted expressions.

        Returns:
            set of ExpressionInfo.
        """
        return self.expression_infos.get_expressions_set(lang)

    def get_pagename(self, pagenames):
        """Termwiki pagename of the concept.

        Arguments:
            pagenames (list of str): names of existing pages.

        Returns:
            str: The termwiki pagename.
        """
        for lang in ['sms', 'smn', 'sma', 'smj', 'se', 'fi', 'nb', 'sv', 'en', 'lat']:
            if lang in self.lang_set:
                for expression in self.get_expressions_set(lang):
                    pagename = ':'.join([self.main_category, expression])
                    if pagename not in pagenames:
                        return pagename

    @property
    def lang_set(self):
        """A set containing the languages of the expressions."""
        return self.expression_infos.lang_set

    @property
    def dupe_string(self):
        """Pages that may be duplicates of this concept.

        Returns:
            str: wiki links to possible duplicate pages.
        """
        dupe = '|duplicate_pages='
        dupe += ', '.join(
            ['[' + page + ']' for page in sorted(self.pages)])

        return dupe

    def __str__(self):
        strings = ['{{Concept']
        for key, values in self.concept_info.items():
            strings.extend(
                ['|' + key + '=' + value
                 for value in values
                 if len(value.strip()) > 0])

        if len(self.pages) > 0:
            strings.append(self.dupe_string)

        strings.append('}}')

        expressions = str(self.expression_infos)
        if len(expressions) > 0:
            strings.append(expressions)

        strings.extend([str(related_concept)
                        for related_concept in sorted(self.related_concepts)])

        return '\n'.join(strings)

    @property
    def is_empty(self):
        return self.expression_infos.is_empty and len(self.concept_info) == 0


class Importer(object):
    """The import class.

    Attributes:
        filename (str): path to the file that should be imported
            to the termwiki
        termwiki (str): url to the termwiki
        concepts (list of ConceptInfo): all the concepts that have been
            found in filename
    """
    def __init__(self, filename, termwiki):
        """Initialise the Importer class."""
        self.filename = filename
        self.termwiki = termwiki
        self.concepts = []

    def write(self, pagecounter):
        """Write the result of the conversion.

        Write the concepts found to an xml file.

        Arguments:
            pagecounter ():
        """
        pages = etree.Element('pages')
        for concept in self.concepts:
            content = etree.Element('content')
            content.text = read_termwiki.term_to_string(concept)

            page = etree.Element('page')
            try:
                page.set('title', ':'.join(
                    [concept['concept']['main_category'],
                     concept['related_expressions'][0]['expression']]))
            except TypeError:
                page.set('title', ':'.join([concept.main_category,
                                            'page_' + str(pagecounter.number)]))
            page.append(content)
            pages.append(page)

        with open(self.resultname, 'w') as to_file:
            to_file.write(etree.tostring(pages, pretty_print=True,
                                         encoding='unicode'))

    @property
    def resultname(self):
        return self.filename.replace('.xlsx', '.xml')


class ExcelImporter(Importer):

    def collect_expressions(self, startline):
        """Find expressions found in startline.

        Arguments:
            startline (str): the content of an expression line

        Returns:
            list of str: the expression found in startline
        """
        expressions = []

        if ('~' in startline or
                '?' in startline or
                re.search('[()-]', startline) is not None):
            expressions.append(startline.replace('\n', ' '))
        else:
            splitters = re.compile(r'[,;\n\/]')

            for token in splitters.split(startline):
                finaltoken = token.strip().lower()
                if len(finaltoken) > 0:
                    expressions.append(finaltoken)

        return expressions

    @property
    def fileinfo(self):
        yamlname = self.filename.replace('.xlsx', '.yaml')
        with open(yamlname) as yamlfile:
            return yaml.load(yamlfile)

    def get_concepts(self):
        shortname = os.path.splitext(os.path.basename(self.filename))[0]
        counter = defaultdict(int)
        workbook = openpyxl.load_workbook(self.filename)

        print(shortname)
        for ws_title, ws_info in list(self.fileinfo.items()):
            sheet = workbook[ws_title]

            for row in range(2, sheet.max_row + 1):
                counter['concepts'] += 1

                concept = {
                    'concept': {
                        'collection': set(),
                        'main_category': ws_info['main_category'],
                    },
                    'concept_infos': [],
                    'related_expressions': []
                }
                concept['concept']['collection'].add(shortname)

                pos = ''
                if (ws_info['wordclass'] != 0 and
                        sheet.cell(
                            row=row,
                            column=ws_info['wordclass']).value is not None):
                    pos = sheet.cell(
                        row=row, column=ws_info['wordclass']).value.strip()

                for language, col in list(ws_info['terms'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        expression_line = sheet.cell(
                            row=row, column=col).value.strip()
                        for expression in self.collect_expressions(expression_line):
                            concept['related_expressions'].append({
                                'expression': expression,
                                'pos': pos,
                                'language': language,
                            })

                for info, col in list(ws_info['other_info'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        concept['concept'][info] = sheet.cell(
                            row=row, column=col).value.strip()

                #common_pages = \
                    #self.termwiki.get_pages_where_concept_probably_exists(
                        #concept)
                #if len(common_pages) > 0:
                    #concept.possible_duplicate = common_pages
                    #counter['possible_duplicates'] += 1
                read_termwiki.to_concept_info(concept)
                if (len(concept['related_expressions']) or
                        len(concept['concept_infos'])):
                    self.concepts.append(concept)

        for key, count in list(counter.items()):
            print('\t', key, count, )


class ArbeidImporter(Importer):

    def __init__(self):
        super().__init__()

    def get_arbeid_concepts(self):
        filename = 'sgl_dohkkehuvvon_listtut/arbeidsliv_godkjent_av_termgr.txt'
        with open(filename) as arbeid:
            all_concepts = []
            concepts = Concepts({'nb': Concept(), 'se': Concept()})
            start = re.compile(r'\w\w\w$')
            for line in arbeid:
                if start.match(line):
                    all_concepts.append(concepts)
                    concepts = Concepts({'nb': Concept(), 'se': Concept()})
                else:
                    if line.startswith('se: '):
                        concepts.concepts['se'].expressions = self.collect_expressions(
                            line[len('se: '):].strip())
                        self.do_expressions_exist(
                            concepts.concepts['se'].expressions, 'se')
                    elif line.startswith('MRKN: '):
                        concepts.concepts['se'].explanation = line[
                            len('MRKN: '):].strip()
                    elif line.startswith('DEF1: '):
                        concepts.concepts['se'].definition = line[
                            len('DEF1: '):].strip()
                    elif line.startswith('nb: '):
                        concepts.concepts['nb'].expressions = self.collect_expressions(
                            line[len('nb: '):].strip())
                        self.do_expressions_exist(
                            concepts.concepts['nb'].expressions, 'nb')
                    elif line.startswith('nbMRKN: '):
                        concepts.concepts['nb'].explanation = line[
                            len('nbMRKN: '):].strip()
                    elif line.startswith('nbDEF1: '):
                        concepts.concepts['nb'].definition = line[
                            len('nbDEF1: '):].strip()
                    elif not line.startswith('klass'):
                        print(line.strip())

            return all_concepts

    @staticmethod
    def collect_expressions(startline):
        finaltokens = []
        for commatoken in startline.split(','):
            for semicolontoken in commatoken.split(';'):
                if '<STE>' not in semicolontoken and '<FRTE>' not in semicolontoken:
                    finaltoken = semicolontoken.replace('<SY>', '').strip()
                    finaltoken = re.sub('<GRAM.+>', '', finaltoken)
                    if '<' in finaltoken or '>' in finaltoken:
                        print(finaltoken, file=sys.stderr)
                    finaltokens.append(finaltoken)

        return finaltokens


class PageCounter(object):

    def __init__(self):
        self.counter = 0

    @property
    def number(self):
        self.counter += 1
        return self.counter


def parse_options():
    """Parse options given to the script."""
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument('termfiles',
                        nargs='+',
                        help='One or more files containing terms. Each file must have a \
                        yaml file that inform how they should be treated.')

    args = parser.parse_args()

    return args


def main():
    """Convert files to termwiki format."""
    args = parse_options()

    pagecounter = PageCounter()

    termwiki = TermWiki()
    termwiki.get_expressions()
    termwiki.get_pages()

    for termfile in args.termfiles:
        excel = ExcelImporter(termfile, termwiki)
        excel.get_concepts()
        excel.write(pagecounter)
