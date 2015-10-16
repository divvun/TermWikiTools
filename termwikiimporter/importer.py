# -*- coding: utf-8 -*-


import collections
from lxml import etree
import openpyxl
import os
import re
import subprocess
import sys


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
    def __init__(self):
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
        e_set = set()
        for e in self.expressions:
            if e.language == lang:
                e_set.add(e.expression)

        return e_set

    def get_lang_set(self):
        lang_set = set()
        for e in self.expressions:
            lang_set.add(e.language)

        return lang_set

    def __str__(self):
        strings = ['{{Concept']
        for key, values in self.concept_info.items():
            for value in values:
                if len(value.strip()) > 0:
                    strings.append('|' + key + '=' + value)
            if len(self.pages) > 0:
                dupe = '|duplicate_pages='
                for page in self.pages:
                    dupe += '[' + page + ']'
                strings.append(dupe)
        strings.append('}}')

        for expression in sorted(self.expressions):
            strings.append(str(expression))

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
        for lang in concept.get_lang_set():
            if not self.get_expressions_set(lang).isdisjoint(
                    concept.get_expressions_set(lang)):
                hits += 1

        if hits > 1:
            termwiki_pages = collections.defaultdict(set)
            for lang in concept.get_lang_set():
                for expression in concept.get_expressions_set(lang):
                    termwiki_pages[lang].update(self.expressions[lang][expression])

            for lang1, pages1 in termwiki_pages.items():
                for lang2, pages2 in termwiki_pages.items():
                    if lang1 != lang2:
                        common_pages.update(pages1.intersection(pages2))

        return common_pages


class Importer(object):
    def __init__(self):
        self.termwiki = TermWiki()
        self.termwiki.get_expressions()
        self.termwiki.get_pages()
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

    def write(self, to_file=sys.stdout):
        for concept in self.concepts:
            print('<concept>', file=to_file)
            print(str(concept), file=to_file)
            print('</end_concept>', file=to_file)


class ExcelImporter(Importer):
    def collect_expressions(self, startline, language, counter, collection='', wordclass='N/A'):
        '''Insert expressions found in startline into a list of ExpressionInfo

        startline: the content of an expression line
        language: the language of the expression line
        collection: the basename of the file where the expression comes from
        '''
        expressions = []
        if re.search(r'[()-]', startline) is not None:
            counter['has_illegal_char'] += 1
            expressions.append(
                ExpressionInfo(
                    expression=startline,
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

    def get_concepts(self, fileinfo):
        totalcounter = collections.defaultdict(int)

        for filename, worksheets in fileinfo.items():
            shortname = os.path.splitext(os.path.basename(filename))[0]
            counter = collections.defaultdict(int)
            workbook = openpyxl.load_workbook(filename)

            print(shortname)
            for ws_title, lang_column in worksheets.items():
                ws = workbook.get_sheet_by_name(ws_title)

                for row in range(2, ws.max_row + 1):
                    counter['concepts'] += 1
                    c = Concept()

                    for language, col in lang_column.items():
                        if ws.cell(row=row, column=col).value is not None:
                            if (language.startswith('definition') or
                                    language.startswith('explanation') or
                                    language.startswith('more_info')):
                                c.concept_info[language] = ws.cell(
                                    row=row, column=col).value.strip()
                            elif not language.startswith('wordclass'):
                                wordclass = 'N/A'

                                try:
                                    wordclass = ws.cell(row=row,
                                                        column=lang_column[wordclass]
                                                        ).value.strip()
                                except KeyError:
                                    pass

                                expression_line = ws.cell(row=row,
                                                          column=col).value.strip()
                                for e in self.collect_expressions(
                                        expression_line, language, counter,
                                        collection=shortname,
                                        wordclass=wordclass):
                                    c.add_expression(e)

                    common_pages = \
                        self.termwiki.get_pages_where_concept_probably_exists(c)
                    if len(common_pages) > 0:
                        c.possible_duplicate = common_pages
                        counter['possible_duplicate'] += 1

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


def main():
    prefix = os.path.join(os.getenv('GTHOME'), 'words', 'terms', 'from_GG',
                          'orig', 'sme', 'sgl_dohkkehuvvon_listtut')
    fileinfos = {
        os.path.join(prefix, 'Terminologiens terminologi.xlsx'): {
                'Sheet1': {
                    'fi': 2, 'nb': 4, 'se': 5, 'sv': 6, 'definition_fi': 7,
                    'explanation_nn': 8, 'nn': 9, 'sma': 10
                }
            },
        os.path.join(prefix, 'teknisk ordliste SG 10-03.xlsx'): {
            'Sheet1': {
                'nb': 1, 'se': 2
                }
            },
        os.path.join(prefix, 'Skolelinux SG 12-05.xlsx'): {
            'Sheet1': {
                'en': 1, 'nb': 3, 'se': 2, 'explanation_se': 7, 'explanation_nb': 8
                }
            },
        os.path.join(prefix, 'servodatfága tearbmalistu.xlsx'): {
            'RIEKTESÁNIT': {
                'nb': 1, 'fi': 6, 'se': 2, 'more_info_se': 3, 'explanation_nb': 5
                }
            },
        os.path.join(prefix, 'njuorjjotearpmat.xlsx'): {
            'Sheet1': {
                'se': 1, 'definition_se': 2, 'definition_nb': 3, 'more_info_se': 4,
                'more_info_nb': 5
                }
            },
        os.path.join(prefix, 'mielladearvvašvuođalága tearbmalistu.xlsx'): {
            'Sheet1': {
                'nb': 1, 'se': 2, 'more_info_se': 3
                }
            },
        os.path.join(prefix, 'Mearra ja mearragáttenámahusat.xlsx'): {
            'Sheet1': {
                'se': 1, 'explanation_nb': 2
                }
            },
        os.path.join(prefix, 'matematihkkalistugarvvisABC  D.xlsx'): {
            'sátnelistu': {
                'se': 1, 'fi': 2, 'nb': 3
                }
            },
        os.path.join(prefix, 'Jurdihkalaš_tearbmalistu_2011-SEG.xlsx'): {
            'Sheet1': {
                'nb': 1, 'se': 2, 'fi': 3, 'more_info_se': 5, 'explanation_se': 7,
                'explanation_nb': 8
                }
            },
        os.path.join(prefix, 'Batnediksuntearpmat godkjent sgl 2011.xlsx'): {
            'Ark1': {
                'nb': 1, 'se': 2, 'wordclass': 3, 'explanation_nb': 8,
                'explanation_se': 9
                }
            },
        os.path.join(prefix, 'askeladden-red tg-møte 17.2.11.xlsx'): {
            'KMB_OWNER_ARTERData': {
                'nb': 2, 'se': 4, 'explanation_nb': 5, 'more_info_nb': 6
                }
            },
        }

    excel = ExcelImporter()
    excel.get_concepts(fileinfos)
    excel.write(sys.argv[1])
