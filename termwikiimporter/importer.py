# -*- coding: utf-8 -*-


from lxml import etree
import collections
import openpyxl
import os
import re
import sys
import subprocess


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


class Concept(object):
    def __init__(self):
        self.concept_info = collections.defaultdict(set)
        self.expressions = collections.defaultdict(set)
        self.pages = set()

    def add_expression(self, lang, expression):
        self.expressions[lang].add(expression)

    def add_concept_info(self, key, info):
        self.concept_info[key].add(info)

    def add_page(self, page):
        self.pages.add(page)

    def __str__(self):
        strings = ['{{Concept']
        for key, values in self.concept_info.items():
            for value in values:
                if len(value.strip()) > 0:
                    strings.append('|' + key + '=' + value)
        strings.append('}}')

        for lang, expressions in self.expressions.items():
            for expression in expressions:
                strings.append('{{Related_expression')
                strings.append('|language=' + lang)
                strings.append('|expression=' + expression)
                strings.append('|sanctioned=Yes')
                strings.append('}}')

        return '\n'.join(strings)


ExcelInfo = collections.namedtuple('ExcelInfo', ['filename', 'worksheet',
                                                 'row'])

class ExcelConcept(Concept):
    '''Make it possible to trace where the Concept first appeared'''
    def __init__(self, filename='', worksheet='', row=0):
        self.excelinfo = ExcelInfo(filename, worksheet, row)
        super().__init__()


class TermWiki(object):
    '''
    1. liste over ord laget fra terms-xxx.xml
    2. hvert ord peker til en liste av id'er der de finnes
    3. en dict med id, og set av ord for hvert språk som hører til den id'en

    for å slå opp, så sjekker man om ordet er i 1. Om det finnes, slår man opp id i 2, sjekker om man har treff i 3.
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
        for lang, expressions in concept.expressions.items():
            if not self.get_expressions_set(lang).isdisjoint(expressions):
                hits += 1

        if hits > 1:
            termwiki_pages = collections.defaultdict(set)
            for lang, expressions in concept.expressions.items():
                for expression in expressions:
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

    def do_expressions_exist(self, expressions, language):
        existing_expressions = []
        for expression in expressions:
            if expression in self.expressions[language]:
                existing_expressions.append(expression)

        return existing_expressions

    def are_expressions_typos(self, expressions):
        typos = []
        for expression in expressions:
            for e in expression.split():
                if self.is_expression_typo(e):
                    typos.append(e)

        return typos

    def run_external_command(self, command, input):
        '''Run the command with input using subprocess'''
        runner = ExternalCommandRunner()
        runner.run(command, to_stdin=input)

        return runner.stdout

    def is_expression_typo(self, expression):
        """Runs lookup on the expression

        Returns the output of preprocess
        """
        lookup_command = ['lookup', '-q', '-flags', 'mbTT',
                          os.path.join(os.getenv('GTHOME'), 'langs', 'sme',
                                       'src', 'analyser-gt-norm.xfst')]

        if b'?' in self.run_external_command(lookup_command, expression.encode('utf8')):
            return True
        else:
            return False


class ExcelImportException(Exception):
    pass

class ExcelImporter(Importer):
    @staticmethod
    def collect_expressions(startline):
        if re.search(r'[()-]', startline) is not None:
            raise ExcelImportException('Illegal char in {}'.format(startline))

        finaltokens = set()
        splitters = re.compile(r'[,;\n\/]')

        for token in splitters.split(startline):
            finaltoken = re.sub('\(.+\)', '', token).strip().lower()
            if len(finaltoken) > 0:
                finaltokens.add(finaltoken)

        return finaltokens

    def get_concepts(self, fileinfo):
        totalcounter = collections.defaultdict(int)

        for filename, worksheets in fileinfo.items():
            shortname = os.path.basename(filename)
            counter = collections.defaultdict(int)
            workbook = openpyxl.load_workbook(filename)

            for ws_title, lang_column in worksheets.items():
                ws = workbook.get_sheet_by_name(ws_title)
                max_column = ws.max_column
                typos_column = max_column + 1

                for row in range(2, ws.max_row + 1):
                    counter['totals'] += 1
                    c = ExcelConcept(filename=filename, worksheet=ws.title, row=row)

                    for language, col in lang_column.items():
                        if ws.cell(row=row, column=col).value is not None:
                            if language.startswith('definition') or language.startswith('explanation') or language.startswith('more_info'):
                                c.concept_info[language] = ws.cell(row=row, column=col).value.strip()
                            else:
                                expression_line = ws.cell(row=row, column=col).value.strip()
                                try:
                                    c.expressions[language] = self.collect_expressions(
                                        expression_line)
                                    if language in ['smj', 'se', 'sma']:
                                        typos = self.are_expressions_typos(c.expressions[language])
                                        if len(typos) > 0:
                                            counter['typos'] += 1
                                            c.typos = typos
                                except ExcelImportException as e:
                                    counter['illegal_char'] += 1
                                    c.expressions[language] = expression_line
                                    c.illegal_char = True


                    common_pages = self.termwiki.get_pages_where_concept_probably_exists(c)
                    if len(common_pages) > 0:
                        c.possible_duplicate = common_pages
                        counter['possible_duplicate'] += 1

                    self.concepts.append(c)

            print(shortname)
            for key, count in counter.items():
                print('\t', key, count, )
                totalcounter[key] += count
            print()

        print('Total')
        for key, count in totalcounter.items():
            print('\t', key, count, )


    def write(self, path, lang_column, to_file=sys.stdout):
        for concept in self.get_concepts(path, lang_column):
            print('xxxxxx', file=to_file)
            print(concept, file=to_file)
            print('yyyyyy', file=to_file)


class ArbeidImporter(Importer):
    def __init__(self):
        super().__init__()

    def get_arbeid_concepts(self):
        with open('sgl_dohkkehuvvon_listtut/arbeidsliv_godkjent_av_termgr.txt') as arbeid:
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
                        c.concepts['se'].expressions = self.collect_expressions(line[len('se: '):].strip())
                        self.do_expressions_exist(c.concepts['se'].expressions, 'se')
                    elif line.startswith('MRKN: '):
                        c.concepts['se'].explanation = line[len('MRKN: '):].strip()
                    elif line.startswith('DEF1: '):
                        c.concepts['se'].definition = line[len('DEF1: '):].strip()
                    elif line.startswith('nb: '):
                        c.concepts['nb'].expressions = self.collect_expressions(line[len('nb: '):].strip())
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
        tokens = startline.split(',')
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

    def write(self, path, lang_column, to_file=sys.stdout):
        for concepts in self.get_arbeid_concepts(path, lang_column):
            print(concepts.__str__(), file=to_file)
            print(concepts.related_expressions_string(), file=to_file)


#ai = ArbeidImporter()
#ai.write()


def main():
    prefix = os.path.join(os.getenv('GTHOME'), 'words', 'terms', 'from_GG',
                          'orig', 'sme', 'sgl_dohkkehuvvon_listtut')
    fileinfos = {
        os.path.join(prefix, 'Terminologiens terminologi.xlsx'):
             {'Sheet1':
                  {'fi': 2, 'nb': 4, 'se': 5, 'sv': 6, 'definition_fi': 7, 'explanation_nn': 8, 'nn': 9, 'sma': 10}},
        os.path.join(prefix, 'teknisk ordliste SG 10-03.xlsx'):
            {'Sheet1':
                 {'nb': 1, 'se': 2}},
         os.path.join(prefix, 'Skolelinux SG 12-05.xlsx'):
              {'Sheet1':
                   {'en': 1, 'nb': 3, 'se': 2, 'explanation_se': 7, 'explanation_nb': 8}},
         os.path.join(prefix, 'servodatfága tearbmalistu.xlsx'):
              {'RIEKTESÁNIT':
                   {'nb': 1, 'fi': 6, 'se': 2, 'more_info_se': 3, 'explanation_nb': 5}},
         os.path.join(prefix, 'njuorjjotearpmat.xlsx'):
             {'Sheet1':
                  {'se': 1, 'definition_se': 2, 'definition_nb': 3, 'more_info_se': 4, 'more_info_nb': 5}},
         os.path.join(prefix, 'mielladearvvašvuođalága tearbmalistu.xlsx'):
             {'Sheet1':
                  {'nb': 1, 'se': 2, 'more_info_se': 3}},
         os.path.join(prefix, 'Mearra ja mearragáttenámahusat.xlsx'):
             {'Sheet1':
                  {'se': 1, 'explanation_nb': 2}},
         os.path.join(prefix, 'matematihkkalistugarvvisABC  D.xlsx'):
             {'sátnelistu':
                  {'se': 1, 'fi': 2, 'nb': 3}},
         os.path.join(prefix, 'Jurdihkalaš_tearbmalistu_2011-SEG.xlsx'):
             {'Sheet1':
                  {'nb': 1, 'se': 2, 'fi': 3, 'more_info_se': 5, 'explanation_se': 7, 'explanation_nb': 8}},
         os.path.join(prefix, 'Batnediksuntearpmat godkjent sgl 2011.xlsx'):
             {'Ark1':
                  {'nb': 1, 'se': 2, 'explanation_nb': 8, 'explanation_se': 9}},
         os.path.join(prefix, 'askeladden-red tg-møte 17.2.11.xlsx'):
             {'KMB_OWNER_ARTERData':
                  {'nb': 2, 'se': 4, 'explanation_nb': 5, 'more_info_nb': 6}},
    }

    excel = ExcelImporter()
    excel.get_concepts(fileinfos)
