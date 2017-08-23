# -*- coding: utf-8 -*-
"""Import/convert term files to termwiki."""


import argparse
import os
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict, namedtuple
import yaml

import attr
import openpyxl
from lxml import etree


class ExpressionError(Exception):
    pass


@attr.s
class ExpressionInfo(object):
    """Information bound to an expression.


    Attributes:
        languge (str): Indicate which language the expression is.
        expression (str): The expression.
        has_illegal_char (boolean): Indicate whether the expression contains
            an unwanted character. Should only written if it is True, as it
            is only used for debugging/checking TermWiki pages.
        collection (str): Indicates which collection the expression belongs
            to.
        sanctioned (boolean): Indicate whether norm groups have sanctioned
            the expression.
        status (str): Indicate if the expression is recommended, outdated,
            etc.
        note (str): Ad hoc note about the expression
        source (str): source of the expression
    """
    language = attr.ib('')
    expression = attr.ib('')
    has_illegal_char = attr.ib(default='No')
    collection = attr.ib('')
    sanctioned = attr.ib(default='No')
    status = attr.ib('')
    note = attr.ib('')
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
            for key, value in sorted(attr.asdict(expression).items()):
                if (value == '' or
                        (value == 'No' and (key == 'has_illegal_char'))):
                    pass
                else:
                    strings.append('|' + key + '=' + value)
            if ' ' in expression.expression:
                strings.append('|pos=MWE')
            else:
                strings.append('|pos=' + self.pos)

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


class OrderedDefaultDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769

    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
                not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))


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


class TermWiki(object):

    """Represent the termwiki xml files.

    expressions is a dict where language is the key and the value is a dict
    The key in this subdict an expression and the value is a set containing
    the concept pages where the expression appears. This effectively mimics
    the Expression pages on the TermWiki.

    pages is a dict where the termwiki pagename is the key and the value is a dict
    The key in this subdict is language and the value is the set of expressions on
    that page. This effectively mimics the Concept pages on the TermWiki.
    """

    def __init__(self):
        self.expressions = defaultdict(dict)
        self.pages = defaultdict(dict)

    @property
    def term_home(self):
        return os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/terms')

    @property
    def pagenames(self):
        return sorted(self.pages.keys())

    def get_expressions(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith('terms-'):
                lang = term_file[term_file.find('-') + 1:term_file.find('.')]
                expressions = defaultdict(set)
                l_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath('.//e/lg/l')
                for lemma in l_elements:
                    expressions[lemma.text].update(
                        set([mg.get('idref')
                             for mg in lemma.getparent().getparent().xpath('.//mg')]))

                self.expressions[lang] = expressions

    def get_pages(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith('terms-'):
                lang = term_file[term_file.find('-') + 1:term_file.find('.')]
                mg_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath('.//e/mg')
                for meaning_group in mg_elements:
                    page = meaning_group.get('idref')
                    self.pages[page].setdefault(lang, set()).update(
                        set([l.text for l in meaning_group.getparent().xpath('./lg/l')]))

    def get_expressions_set(self, lang):
        return set(self.expressions[lang].keys())

    def get_pages_where_concept_probably_exists(self, concept):
        """Check if a Concept already exists in TermWiki.

        A concept is possibly part of the termwiki if one expression from two
        different languages is part of a page.

        concept: is a Concept
        return: a set of the pages containing at least one expression from two
        different languages
        """
        common_pages = set()
        hits = 0
        for lang in concept.lang_set:
            if not self.get_expressions_set(lang).isdisjoint(
                    concept.get_expressions_set(lang)):
                hits += 1

        if hits > 1:
            termwiki_pages = defaultdict(set)
            for lang in concept.lang_set:
                for expression in concept.get_expressions_set(lang):
                    termwiki_pages[lang].update(
                        self.expressions[lang][expression])

            for lang1, pages1 in list(termwiki_pages.items()):
                for lang2, pages2 in list(termwiki_pages.items()):
                    if lang1 != lang2:
                        common_pages.update(pages1.intersection(pages2))

        return common_pages


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
            content.text = str(concept)

            page = etree.Element('page')
            try:
                page.set('title', concept.get_pagename(self.termwiki.pagenames))
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

    def collect_expressions(self, startline, language, counter, collection=''):
        """Insert expressions found in startline into a list of ExpressionInfo.

        startline: the content of an expression line
        language: the language of the expression line
        collection: the basename of the file where the expression comes from
        """
        expressions = []
        if '~' in startline or '?' in startline or re.search('[()-]', startline) is not None:
            counter['has_illegal_char'] += 1
            expressions.append(
                ExpressionInfo(
                    expression=startline.replace('\n', ' '),
                    language=language,
                    has_illegal_char='Yes',
                    collection=collection,
                    status='',
                    note='',
                    source='',
                    sanctioned='No'))
        else:
            splitters = re.compile(r'[,;\n\/]')

            for token in splitters.split(startline):
                finaltoken = token.strip().lower()
                if len(finaltoken) > 0:
                    if ' ' in finaltoken:
                        counter['mwe'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                has_illegal_char='No',
                                collection=collection,
                                status='',
                                note='',
                                source='',
                                sanctioned='Yes'))
                    else:
                        counter['non_typo'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                has_illegal_char='No',
                                collection=collection,
                                status='',
                                note='',
                                source='',
                                sanctioned='Yes'))

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
            sheet = workbook.get_sheet_by_name(ws_title)

            for row in range(2, sheet.max_row + 1):
                counter['concepts'] += 1
                concept = Concept(ws_info['main_category'])
                pos = 'N/A'
                if (ws_info['wordclass'] != 0 and
                        sheet.cell(
                            row=row,
                            column=ws_info['wordclass']).value is not None):
                    pos = sheet.cell(
                        row=row, column=ws_info['wordclass']).value.strip()
                    concept.expression_infos.pos = pos
                for language, col in list(ws_info['terms'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        expression_line = sheet.cell(
                            row=row, column=col).value.strip()
                        for expression in self.collect_expressions(
                                expression_line, language, counter,
                                collection=shortname):
                            concept.add_expression(expression)

                for info, col in list(ws_info['other_info'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        concept.add_concept_info(
                            info, sheet.cell(row=row,
                                             column=col).value.strip())

                common_pages = \
                    self.termwiki.get_pages_where_concept_probably_exists(concept)
                if len(common_pages) > 0:
                    concept.possible_duplicate = common_pages
                    counter['possible_duplicates'] += 1

                if not concept.is_empty:
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
