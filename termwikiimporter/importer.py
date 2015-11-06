# -*- coding: utf-8 -*-


from __future__ import print_function


import argparse
import collections
from lxml import etree
import openpyxl
import os
import re
import subprocess
import sys
import yaml


class ExpressionException(Exception):
    pass


class ExternalCommandRunner(object):

    '''Class to run external command through subprocess

    Save output, error and returnvalue
    '''

    def __init__(self):
        self.stdout = None
        self.stderr = None
        self.returncode = None

    def run(self, command, cwd=None, to_stdin=None):
        '''Run the command, save the result'''
        try:
            subp = subprocess.Popen(command,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    cwd=cwd)
        except OSError:
            print(u'Please install {}'.format(command[0]))
            raise

        (self.stdout, self.stderr) = subp.communicate(to_stdin)
        self.returncode = subp.returncode


class ExpressionInfo(
    collections.namedtuple(
        u'ExpressionInfo',
        u'language expression is_typo has_illegal_char collection status note '
        u'sanctioned equivalence')):
    '''Information bound to an expression

    expression is a string

    is_typo, has_illegal_char and sanctioned are booleans

    is_typo is true if an fst does not recognize the expression
    has_illegal_char is true if the expression contains unwanted characters

    is_typo and has_illegal_char should only written if they are True, as
    they are only used for debugging/checking TermWiki pages

    sanctioned is true if expressions are recommended by a language organ

    collection is a string that points to the collection the expression belongs to
    pos is a string informing what part of speech the word is
    '''
    __slots__ = ()


class ExpressionInfos(object):
    def __init__(self):
        self.expressions = []
        self._pos = u'N/A'

    def __str__(self):
        strings = []
        for expression in self.expressions:
            strings.append(u'{{Related expression')
            for key, value in expression._asdict().items():
                if (value == u'' or
                    (value == 'No' and (key == 'is_typo' or
                                        key == 'has_illegal_char'))):
                    pass
                else:
                    strings.append(u'|' + key + u'=' + value)
            if ' ' in expression.expression:
                strings.append(u'|pos=MWE')
            else:
                strings.append(u'|pos=' + self.pos)

            strings.append(u'}}')

        return u'\n'.join(strings)

    def add_expression(self, expression_info):
        if expression_info not in self.expressions:
            self.expressions.append(expression_info)

    def get_expressions_set(self, lang):
        return set(
            [e.expression for e in self.expressions
             if e.language == lang])

    @property
    def lang_set(self):
        return set([e.language for e in self.expressions])

    @property
    def is_empty(self):
        return len(self.expressions) == 0

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if not pos in [u'N', u'A', u'Adv', u'V', u'Pron', u'CS', u'CC', u'Adp', u'Po',
                       u'Pr', u'Interj', u'Pcle', u'Num', u'ABBR', u'MWE', u'N/A']:
            raise ExpressionException(u'Illegal value', pos)
        elif pos in ['MWE', 'N/A']:
            pass
        elif self._pos == u'N/A':
            self._pos = pos
        elif self._pos != pos:
            raise ExpressionException(u'Trying to set conflicting pos', self.pos, pos)


class RelatedConceptInfo(collections.namedtuple(u'RelatedConceptInfo',
                                                u'concept relation')):
    __slots__ = ()

    def __str__(self):
        strings = [u'{{Related concept']
        for key, value in self._asdict().items():
                if value == u'':
                    pass
                else:
                    strings.append(u'|' + key + u'=' + value)

        strings.append(u'}}')

        return u'\n'.join(strings)


class OrderedDefaultDict(collections.OrderedDict, collections.defaultdict):
    '''https://gist.github.com/merwok/11268759'''
    pass


class Concept(object):
    '''Model the TermWiki concept

    concept_info is a dict
    The concept information is key, the value is a set containing the
    definitions, explanations and more_infos

    expressions is a list containing ExpressionInfos

    pages is a set of TermWiki pages that may be duplicates of this concept
    '''
    def __init__(self, main_category=''):
        self.main_category = main_category
        self.concept_info = OrderedDefaultDict()
        self.concept_info.default_factory = set
        self.expression_infos = ExpressionInfos()
        self.related_concepts = []
        self.pages = set()

    def add_expression(self, expression_info):
        self.expression_infos.add_expression(expression_info)

    def add_related_concept(self, concept_info):
        if concept_info not in self.related_concepts:
            self.related_concepts.append(concept_info)

    def add_concept_info(self, key, info):
        self.concept_info[key].add(info)

    def add_page(self, page):
        self.pages.add(page)

    def get_expressions_set(self, lang):
        return self.expression_infos.get_expressions_set(lang)

    def get_pagename(self, pagenames):
        for lang in [u'sms', u'smn', u'sma', u'smj', u'se', u'fi', u'nb', u'sv', u'en', u'lat']:
            if lang in self.lang_set:
                for expression in self.get_expressions_set(lang):
                    pagename = u':'.join([self.main_category, expression])
                    if pagename not in pagenames:
                        return pagename

    @property
    def lang_set(self):
        return self.expression_infos.lang_set

    @property
    def dupe_string(self):
        dupe = u'|duplicate_pages='
        dupe += u', '.join(
            [u'[' + page + u']' for page in sorted(self.pages)])

        return dupe

    def __str__(self):
        strings = [u'{{Concept']
        for key, values in self.concept_info.iteritems():
            strings.extend(
                [u'|' + key + u'=' + value
                 for value in values
                 if len(value.strip()) > 0])

        if len(self.pages) > 0:
            strings.append(self.dupe_string)

        strings.append(u'}}')

        strings.append(unicode(self.expression_infos))

        strings.extend([unicode(related_concept)
                        for related_concept in sorted(self.related_concepts)])

        return u'\n'.join(strings)

    @property
    def is_empty(self):
        return (self.expression_infos.is_empty and len(self.concept_info) == 0)


class TermWiki(object):
    '''Represent the termwiki xml files

    expressions is a dict where language is the key and the value is a dict
    The key in this subdict an expression and the value is a set containing
    the concept pages where the expression appears. This effectively mimics
    the Expression pages on the TermWiki.

    pages is a dict where the termwiki pagename is the key and the value is a dict
    The key in this subdict is language and the value is the set of expressions on
    that page. This effictively mimics the Concept pages on the TermWiki.
    '''
    def __init__(self):
        self.expressions = collections.defaultdict(dict)
        self.pages = collections.defaultdict(dict)

    @property
    def term_home(self):
        return os.path.join(os.getenv(u'GTHOME'), u'words/terms/termwiki/terms')

    @property
    def pagenames(self):
        return sorted(self.pages.keys())

    def get_expressions(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith(u'terms-'):
                lang = term_file[term_file.find(u'-') + 1:term_file.find(u'.')]
                expressions = collections.defaultdict(set)
                l_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath(u'.//e/lg/l')
                for l in l_elements:
                    expressions[l.text].update(
                        set([mg.get(u'idref')
                             for mg in l.getparent().getparent().xpath(u'.//mg')]))

                self.expressions[lang] = expressions

    def get_pages(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith(u'terms-'):
                lang = term_file[term_file.find(u'-') + 1:term_file.find(u'.')]
                mg_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath(u'.//e/mg')
                for mg in mg_elements:
                    page = mg.get(u'idref')
                    self.pages[page].setdefault(lang, set()).update(
                        set([l.text for l in mg.getparent().xpath(u'./lg/l')]))

    def get_expressions_set(self, lang):
        return set(self.expressions[lang].keys())

    def get_pages_where_concept_probably_exists(self, concept):
        '''Check if a Concept already exists in TermWiki

        A concept is possibly part of the termwiki if one expression from two
        different languages is part of a page.

        concept: is a Concept
        return: a set of the pages containing at least one expression from two
        different languages
        '''
        common_pages = set()
        hits = 0
        for lang in concept.lang_set:
            if not self.get_expressions_set(lang).isdisjoint(
                    concept.get_expressions_set(lang)):
                hits += 1

        if hits > 1:
            termwiki_pages = collections.defaultdict(set)
            for lang in concept.lang_set:
                for expression in concept.get_expressions_set(lang):
                    termwiki_pages[lang].update(self.expressions[lang][expression])

            for lang1, pages1 in termwiki_pages.items():
                for lang2, pages2 in termwiki_pages.items():
                    if lang1 != lang2:
                        common_pages.update(pages1.intersection(pages2))

        return common_pages


class Importer(object):
    def __init__(self, filename, termwiki):
        self.filename = filename
        self.termwiki = termwiki
        self.concepts = []

    def run_external_command(self, command, input):
        '''Run the command with input using subprocess'''
        runner = ExternalCommandRunner()
        runner.run(command, to_stdin=input)

        return runner.stdout

    def is_expression_typo(self, expression, lang):
        """Runs lookup on the expression

        Returns the output of preprocess
        """
        if lang in [u'se', u'sma', u'smj']:
            if lang == u'se':
                lang = u'sme'
            lookup_command = ['lookup', u'-q', u'-flags', u'mbTT',
                              os.path.join(os.getenv(u'GTHOME'), u'langs', lang,
                                           u'src', u'analyser-gt-norm.xfst')]

            if b'?' in self.run_external_command(lookup_command,
                                                 expression.encode(u'utf8')):
                return True

        return False

    def write(self, pagecounter):
        pages = etree.Element(u'pages')
        for concept in self.concepts:
            content = etree.Element(u'content')
            content.text = str(concept)

            page = etree.Element(u'page')
            try:
                page.set(u'title', concept.get_pagename(self.termwiki.pagenames))
            except TypeError:
                page.set(u'title', u':'.join([concept.main_category,
                                              u'page_' + str(pagecounter.number)]))
            page.append(content)
            pages.append(page)

        with open(self.resultname, u'w') as to_file:
            to_file.write(etree.tostring(pages, pretty_print=True,
                                         encoding='unicode'))

    @property
    def resultname(self):
        return self.filename.replace(u'.xlsx', u'.xml')


class ExcelImporter(Importer):
    def collect_expressions(self, startline, language, counter, collection=''):
        '''Insert expressions found in startline into a list of ExpressionInfo

        startline: the content of an expression line
        language: the language of the expression line
        collection: the basename of the file where the expression comes from
        '''
        expressions = []
        if u'~' in startline or u'?' in startline or re.search(u'[()-]', startline) is not None:
            counter[u'has_illegal_char'] += 1
            expressions.append(
                ExpressionInfo(
                    expression=unicode(startline.replace(u'\n', u' ')),
                    language=language,
                    is_typo='No',
                    has_illegal_char='Yes',
                    collection=collection,
                    status='',
                    note=u'',
                    equivalence=u'',
                    sanctioned='No'))
        else:
            splitters = re.compile(r'[,;\n\/]')

            for token in splitters.split(startline):
                finaltoken = unicode(token.strip().lower())
                if len(finaltoken) > 0:
                    if u' ' in finaltoken:
                        counter[u'mwe'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                is_typo=u'No',
                                has_illegal_char=u'No',
                                collection=collection,
                                status='',
                                note=u'',
                                equivalence=u'',
                                sanctioned=u'Yes'))
                    elif self.is_expression_typo(finaltoken, language):
                        counter[u'is_typo'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                is_typo=u'Yes',
                                has_illegal_char=u'No',
                                collection=collection,
                                status='',
                                note=u'',
                                equivalence=u'',
                                sanctioned=u'No'))
                    else:
                        counter[u'non_typo'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                is_typo=u'No',
                                has_illegal_char=u'No',
                                collection=collection,
                                status='',
                                note=u'',
                                equivalence=u'',
                                sanctioned=u'Yes'))

        return expressions

    @property
    def fileinfo(self):
        yamlname = self.filename.replace(u'.xlsx', u'.yaml')
        with open(yamlname) as yamlfile:
            return yaml.load(yamlfile)

    def get_concepts(self):
        totalcounter = collections.defaultdict(int)

        shortname = os.path.splitext(os.path.basename(self.filename))[0]
        counter = collections.defaultdict(int)
        workbook = openpyxl.load_workbook(self.filename)

        print(shortname)
        for ws_title, ws_info in self.fileinfo.items():
            ws = workbook.get_sheet_by_name(ws_title)

            for row in range(2, ws.max_row + 1):
                counter[u'concepts'] += 1
                c = Concept(ws_info[u'main_category'])
                pos = u'N/A'
                if (ws_info[u'wordclass'] != 0 and
                        ws.cell(row=row,
                                column=ws_info[u'wordclass']).value is not None):
                    pos = ws.cell(row=row,
                                  column=ws_info[u'wordclass']).value.strip()
                    c.expression_infos.pos = pos
                for language, col in ws_info[u'terms'].items():
                    if ws.cell(row=row, column=col).value is not None:
                        expression_line = ws.cell(row=row,
                                                  column=col).value.strip()
                        for e in self.collect_expressions(
                                expression_line, language, counter,
                                collection=shortname):
                            c.add_expression(e)

                for info, col in ws_info[u'other_info'].items():
                    if ws.cell(row=row, column=col).value is not None:
                        c.add_concept_info(info,
                                           ws.cell(row=row, column=col).value.strip())

                common_pages = \
                    self.termwiki.get_pages_where_concept_probably_exists(c)
                if len(common_pages) > 0:
                    c.possible_duplicate = common_pages
                    counter[u'possible_duplicates'] += 1

                if not c.is_empty:
                    self.concepts.append(c)

        for key, count in counter.items():
            print(u'\t', key, count, )


class ArbeidImporter(Importer):
    def __init__(self):
        super().__init__()

    def get_arbeid_concepts(self):
        filename = u'sgl_dohkkehuvvon_listtut/arbeidsliv_godkjent_av_termgr.txt'
        with open(filename) as arbeid:
            all_concepts = []
            c = Concepts({'nb': Concept(), u'se': Concept()})
            start = re.compile(u'\w\w\w$')
            i = 0
            total = 0
            for line in arbeid:
                if start.match(line):
                    all_concepts.append(c)
                    c = Concepts({'nb': Concept(), u'se': Concept()})
                else:
                    if line.startswith(u'se: '):
                        c.concepts[u'se'].expressions = self.collect_expressions(
                            line[len(u'se: '):].strip())
                        self.do_expressions_exist(c.concepts[u'se'].expressions, u'se')
                    elif line.startswith(u'MRKN: '):
                        c.concepts[u'se'].explanation = line[len(u'MRKN: '):].strip()
                    elif line.startswith(u'DEF1: '):
                        c.concepts[u'se'].definition = line[len(u'DEF1: '):].strip()
                    elif line.startswith(u'nb: '):
                        c.concepts[u'nb'].expressions = self.collect_expressions(
                            line[len(u'nb: '):].strip())
                        self.do_expressions_exist(c.concepts[u'nb'].expressions, u'nb')
                    elif line.startswith(u'nbMRKN: '):
                        c.concepts[u'nb'].explanation = line[len(u'nbMRKN: '):].strip()
                    elif line.startswith(u'nbDEF1: '):
                        c.concepts[u'nb'].definition = line[len(u'nbDEF1: '):].strip()
                    elif not line.startswith(u'klass'):
                        print(line.strip())

            return all_concepts

    @staticmethod
    def collect_expressions(startline):
        finaltokens = []
        for commatoken in startline.split(u','):
            for semicolontoken in commatoken.split(u';'):
                if u'<STE>' not in semicolontoken and u'<FRTE>' not in semicolontoken:
                    finaltoken = semicolontoken.replace(u'<SY>', u'').strip()
                    finaltoken = re.sub(u'<GRAM.+>', u'', finaltoken)
                    if u'<' in finaltoken or u'>' in finaltoken:
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
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument(u'termfiles',
                        nargs='+',
                        help='One or more files containing terms. Each file must have a \
                        yaml file that inform how they should be treated.')

    args = parser.parse_args()

    return args


def main():
    args = parse_options()

    pagecounter = PageCounter()

    termwiki = TermWiki()
    termwiki.get_expressions()
    termwiki.get_pages()

    for termfile in args.termfiles:
        excel = ExcelImporter(termfile, termwiki)
        excel.get_concepts()
        excel.write(pagecounter)
