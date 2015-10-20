# -*- coding: utf-8 -*-


import argparse
import collections
from lxml import etree
import openpyxl
import os
import re
import subprocess
import sys
import yaml


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
            print('Please install {}'.format(command[0]))
            raise

        (self.stdout, self.stderr) = subp.communicate(to_stdin)
        self.returncode = subp.returncode


class ExpressionInfo(
    collections.namedtuple(
        'ExpressionInfo',
        'expression language is_typo has_illegal_char collection wordclass sanctioned')):
    '''Information bound to an expression

    expression is a string

    is_typo, has_illegal_char and sanctioned are booleans

    is_typo is true if an fst does not recognize the expression
    has_illegal_char is true if the expression contains unwanted characters

    is_typo and has_illegal_char should only written if they are True, as
    they are only used for debugging/checking TermWiki pages

    sanctioned is true if expressions are recommended by a language organ

    collection is a string that points to the collection the expression belongs to
    wordclass is a string informing what part of speech the word is
    '''
    __slots__ = ()

    def __str__(self):
        strings = ['{{Related_expression']
        for key, value in self._asdict().items():
            if key in ['is_typo', 'has_illegal_char']:
                if value is True:
                    strings.append('|' + key + '=Yes')
            else:
                if value is True:
                    strings.append('|' + key + '=Yes')
                elif value is False:
                    strings.append('|' + key + '=No')
                else:
                    strings.append('|' + key + '=' + value)

        strings.append('}}')

        return '\n'.join(strings)


class Concept(object):
    '''Model the TermWiki concept

    concept_info is a dict
    The concept information is key, the value is a set containing the
    definitions, explanations and more_infos

    expressions is a list containing ExpressionInfos

    pages is a set of TermWiki pages that may be duplicates of this concept
    '''
    def __init__(self, main_category):
        self.main_category = main_category
        self.concept_info = collections.defaultdict(set)
        self.expressions = []
        self.pages = set()

    def add_expression(self, expression_info):
        if expression_info not in self.expressions:
            self.expressions.append(expression_info)

    def add_concept_info(self, key, info):
        self.concept_info[key].add(info)

    def add_page(self, page):
        self.pages.add(page)

    def get_expressions_set(self, lang):
        return set(
            [e.expression for e in self.expressions
             if e.language == lang])

    def get_pagename(self, pagenames):
        for lang in ['sms', 'smn', 'sma', 'smj', 'se', 'fi', 'nb', 'sv', 'en', 'lat']:
            if lang in self.lang_set:
                for expression in sorted(self.get_expressions_set(lang)):
                    pagename = ':'.join([self.main_category, expression])
                    if pagename not in pagenames:
                        return pagename

    @property
    def lang_set(self):
        return set([e.language for e in self.expressions])

    @property
    def dupe_string(self):
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

        strings.extend([str(expression)
                        for expression in sorted(self.expressions)])

        return '\n'.join(strings)


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
        return os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/terms')

    @property
    def pagenames(self):
        return sorted(self.pages.keys())

    def get_expressions(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith('terms-'):
                lang = term_file[term_file.find('-') + 1:term_file.find('.')]
                expressions = collections.defaultdict(set)
                l_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath('.//e/lg/l')
                for l in l_elements:
                    expressions[l.text].update(
                        set([mg.get('idref')
                             for mg in l.getparent().getparent().xpath('.//mg')]))

                self.expressions[lang] = expressions

    def get_pages(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith('terms-'):
                lang = term_file[term_file.find('-') + 1:term_file.find('.')]
                mg_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath('.//e/mg')
                for mg in mg_elements:
                    page = mg.get('idref')
                    self.pages[page].setdefault(lang, set()).update(
                        set([l.text for l in mg.getparent().xpath('./lg/l')]))

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
        if lang in ['se', 'sma', 'smj']:
            if lang == 'se':
                lang = 'sme'
            lookup_command = ['lookup', '-q', '-flags', 'mbTT',
                              os.path.join(os.getenv('GTHOME'), 'langs', lang,
                                           'src', 'analyser-gt-norm.xfst')]

            if b'?' in self.run_external_command(lookup_command,
                                                 expression.encode('utf8')):
                return True

        return False

    def write(self):
        with open(self.resultname, 'w') as to_file:
            for concept in self.concepts:
                print('{{-start-}}', file=to_file)
                try:
                    print("'''" + concept.get_pagename(self.termwiki.pagenames) + "'''",
                        file=to_file)
                except TypeError:
                    print('error in', str(concept), file=sys.stderr)
                print(str(concept), file=to_file)
                print('{{-stop-}}', file=to_file)


class ExcelImporter(Importer):
    @property
    def resultname(self):
        return self.filename.replace('.xlsx', '.txt')

    def collect_expressions(self, startline, language, counter, collection='',
                            wordclass='N/A'):
        '''Insert expressions found in startline into a list of ExpressionInfo

        startline: the content of an expression line
        language: the language of the expression line
        collection: the basename of the file where the expression comes from
        '''
        expressions = []
        if '~' in startline or '?' in startline or re.search('[()-]', startline) is not None:
            counter['has_illegal_char'] += 1
            expressions.append(
                ExpressionInfo(
                    expression=startline.replace('\n', ' '),
                    language=language,
                    is_typo=False,
                    has_illegal_char=True,
                    collection=collection,
                    wordclass='N/A',
                    sanctioned=False))
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
                                is_typo=False,
                                has_illegal_char=False,
                                collection=collection,
                                wordclass='MWE',
                                sanctioned=True))
                    elif self.is_expression_typo(finaltoken, language):
                        counter['is_typo'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                is_typo=True,
                                has_illegal_char=False,
                                collection=collection,
                                wordclass=wordclass,
                                sanctioned=False))
                    else:
                        counter['non_typo'] += 1
                        expressions.append(
                            ExpressionInfo(
                                expression=finaltoken,
                                language=language,
                                is_typo=False,
                                has_illegal_char=False,
                                collection=collection,
                                wordclass=wordclass,
                                sanctioned=True))

        return expressions

    @property
    def fileinfo(self):
        yamlname = self.filename.replace('.xlsx', '.yaml')
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
                counter['concepts'] += 1
                c = Concept(ws_info['main_category'])
                wordclass = 'N/A'
                if (ws_info['wordclass'] != 0 and
                        ws.cell(row=row, column=ws_info['wordclass']).value is not None):
                    wordclass = ws.cell(row=row,
                                        column=ws_info['wordclass']).value.strip()
                for language, col in ws_info['terms'].items():
                    if ws.cell(row=row, column=col).value is not None:
                        expression_line = ws.cell(row=row,
                                                    column=col).value.strip()
                        for e in self.collect_expressions(
                                expression_line, language, counter,
                                collection=shortname,
                                wordclass=wordclass):
                            c.add_expression(e)

                for info, col in ws_info['other_info'].items():
                    if ws.cell(row=row, column=col).value is not None:
                        c.add_concept_info(info,
                                           ws.cell(row=row, column=col).value.strip())

                common_pages = \
                    self.termwiki.get_pages_where_concept_probably_exists(c)
                if len(common_pages) > 0:
                    c.possible_duplicate = common_pages
                    counter['possible_duplicates'] += 1

                self.concepts.append(c)

            for key, count in counter.items():
                print('\t', key, count, )
                totalcounter[key] += count
            print()

        print('Total')
        for key, count in totalcounter.items():
            print('\t', key, count, )


class ArbeidImporter(Importer):
    def __init__(self):
        super().__init__()

    def get_arbeid_concepts(self):
        filename = 'sgl_dohkkehuvvon_listtut/arbeidsliv_godkjent_av_termgr.txt'
        with open(filename) as arbeid:
            all_concepts = []
            c = Concepts({'nb': Concept(), 'se': Concept()})
            start = re.compile('\w\w\w$')
            i = 0
            total = 0
            for line in arbeid:
                if start.match(line):
                    all_concepts.append(c)
                    c = Concepts({'nb': Concept(), 'se': Concept()})
                else:
                    if line.startswith('se: '):
                        c.concepts['se'].expressions = self.collect_expressions(
                            line[len('se: '):].strip())
                        self.do_expressions_exist(c.concepts['se'].expressions, 'se')
                    elif line.startswith('MRKN: '):
                        c.concepts['se'].explanation = line[len('MRKN: '):].strip()
                    elif line.startswith('DEF1: '):
                        c.concepts['se'].definition = line[len('DEF1: '):].strip()
                    elif line.startswith('nb: '):
                        c.concepts['nb'].expressions = self.collect_expressions(
                            line[len('nb: '):].strip())
                        self.do_expressions_exist(c.concepts['nb'].expressions, 'nb')
                    elif line.startswith('nbMRKN: '):
                        c.concepts['nb'].explanation = line[len('nbMRKN: '):].strip()
                    elif line.startswith('nbDEF1: '):
                        c.concepts['nb'].definition = line[len('nbDEF1: '):].strip()
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


def parse_options():
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki format')

    parser.add_argument('termfiles',
                        nargs='+',
                        help='One or more files containing terms. Each file must have a \
                        yaml file that inform how they should be treated.')

    args = parser.parse_args()

    return args


def main():
    args = parse_options()

    termwiki = TermWiki()
    termwiki.get_expressions()
    termwiki.get_pages()

    for termfile in args.termfiles:
        excel = ExcelImporter(termfile, termwiki)
        excel.get_concepts()
        excel.write()
