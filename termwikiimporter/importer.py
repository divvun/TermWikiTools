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
        self.idref = set()

    def add_expression(self, lang, expression):
        self.expressions[lang].add(expression)

    def add_concept_info(self, key, info):
        self.concept_info[key].add(info)

    def add_idref(self, idref):
        self.idref.add(idref)

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


class TermWiki(object):
    '''
    1. liste over ord laget fra terms-xxx.xml
    2. hvert ord peker til en liste av id'er der de finnes
    3. en dict med id, og set av ord for hvert språk som hører til den id'en

    for å slå opp, så sjekker man om ordet er i 1. Om det finnes, slår man opp id i 2, sjekker om man har treff i 3.
    '''
    def __init__(self):
        self.expressions = collections.defaultdict(dict)
        self.idrefs = collections.defaultdict(dict)

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
                    expression = l.text
                    idrefs = [mg.get('idref') for mg in l.getparent().getparent().xpath('.//mg')]
                    for idref in idrefs:
                        expressions[expression].add(idref)

                self.expressions[lang] = expressions

    def get_idrefs(self):
        for term_file in os.listdir(self.term_home):
            if term_file.startswith('terms-'):
                lang = term_file[term_file.find('-') + 1:term_file.find('.')]
                mg_elements = etree.parse(
                    os.path.join(self.term_home,
                                 term_file)).xpath('.//e/mg')
                for mg in mg_elements:
                    idref = mg.get('idref')
                    expressions = [l.text for l in mg.getparent().xpath('./lg/l')]
                    for expression in expressions:
                        self.idrefs[idref].setdefault(lang, set()).add(expression)

class Importer(object):
    def __init__(self):
        self.termwiki = TermWiki()
        self.termwiki.get_terms_expression()

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


class ExcelImporter(Importer):
    @staticmethod
    def collect_expressions(startline):
        tokens = startline.split(',')
        finaltokens = set()
        for commatoken in startline.split(','):
            for semicolontoken in commatoken.split(';'):
                for newlinetoken in semicolontoken.split('\n'):
                    for slashtoken in newlinetoken.split('/'):
                        finaltoken = re.sub('\(.+\)', '', slashtoken).strip().lower()
                        if len(finaltoken) > 0:
                            finaltokens.add(finaltoken)

        return finaltokens

    @staticmethod
    def int_range(i1, i2):
        '''Generates the ints as strings'''
        for i in range(i1, i2):
            yield str(i)

    @staticmethod
    def int_range(i1, i2):
        '''Generates the ints as strings'''
        for i in range(i1, i2):
            yield str(i)

    def write_existing_expressions_to_excel(self, filename, lang_column):
        workbook = openpyxl.load_workbook(filename)
        all_concepts = []

        for ws in workbook:
            max_column = ws.max_column
            typos_column = max_column + 1

            for row in range(2, ws.max_row + 1):
                existing_expressions = []
                c = Concepts({'nb': Concept(), 'se': Concept()})

                for language, col in lang_column.items():
                    if ws.cell(row=row, column=col).value is not None:
                        c.concepts[language].expressions = self.collect_expressions(
                            ws.cell(row=row, column=col).value.strip())
                        existing_expressions += self.do_expressions_exist(c.concepts[language].expressions, language)
                        if language == 'se':
                            ws.cell(row=1, column=typos_column).value = 'Vejolaš čállinmeattáhusat'
                            typos = self.are_expressions_typos(c.concepts[language].expressions)
                            if len(typos) > 0:
                                ws.cell(row=row, column=typos_column).value = ', '.join(typos)

                expression_column = typos_column + 1
                for ee in existing_expressions:
                    ws.cell(row=1, column=expression_column).value = 'Liŋka TermWikii'
                    ws.cell(row=row, column=expression_column).value = ee
                    ws.cell(row=row, column=expression_column).hyperlink = 'http://gtsvn.uit.no/termwiki/index.php/Expression:' + ee
                    expression_column += 1

                all_concepts.append(c)

        workbook.save(filename.replace('.xlsx', '.more.xlsx'))

    def get_concepts(self, filename, lang_column):
        workbook = openpyxl.load_workbook(filename)
        all_concepts = []

        exists = 0
        totals = 0
        for ws in workbook:
            max_column = ws.max_column
            typos_column = max_column + 1

            for row in range(2, ws.max_row + 1):
                totals += 1
                existing_expressions = []
                c = Concept()

                for language, col in lang_column.items():
                    if ws.cell(row=row, column=col).value is not None:
                        if language.startswith('definition') or language.startswith('explanation') or language.startswith('more_info'):
                            c.concept_info[language] = ws.cell(row=row, column=col).value.strip()
                        else:
                            c.expressions[language] = self.collect_expressions(
                                ws.cell(row=row, column=col).value.strip())
                            if language == 'se':
                                typos = self.are_expressions_typos(c.expressions[language])
                                if len(typos) > 0:
                                    print('Vejolaš čállinmeattáhusat:', 'row:', row, ','.join(typos), file=sys.stderr)

                if len(existing_expressions) > 0:
                    exists += 1
                    print('Check:', filename, ' row:', row, '\n', c, file=sys.stderr)
                all_concepts.append(c)

        print('Existing vs totals', exists, ':', totals, file=sys.stderr)
        return all_concepts

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

def check_files():
    '''Check the files that giellagáldu is to go through'''
    prefix = os.path.join(os.getenv('HOME'), 'tmp', 'python-excel')
    mapping = [
        (os.path.join(prefix, 'BUP-Ordliste SG 12-04.xlsx'), {'nb': 1, 'se': 2}),
        (os.path.join(prefix, 'giellalisttu_sátnelistu_(1)(1).xlsx'), {'nb': 2, 'se': 1}),
        (os.path.join(prefix, 'láhkatearpmat-dearvvašvuohta.xlsx'), {'nb': 1, 'se': 4}),
        (os.path.join(prefix, 'oadjosanit SG 52-05.xlsx'), {'nb': 1, 'se': 2}),
        (os.path.join(prefix, 'Ped-Psyk.satnelistu SG 24-02.xlsx'), {'nb': 1, 'se': 2}),
        (os.path.join(prefix, 'SEG bálvalusválddahuslistu.xlsx'), {'nb': 2, 'se': 1}),
        (os.path.join(prefix, 'Syklus birrajohtu -godkjent SGL 2009 til publisering.xlsx'), {'nb': 1, 'se': 2}),
    ]

    excel = ExcelImporter()
    for (path, lang_column) in mapping:
        print(path, lang_column)
        excel.write_existing_expressions_to_excel(path, lang_column)

def export_to_mediawiki():
    prefix = os.path.join(os.getenv('GTHOME'), 'words', 'terms', 'from_GG',
                          'orig', 'sme', 'sgl_dohkkehuvvon_listtut')
    mapping = [
        #(os.path.join(prefix, 'Terminologiens terminologi.xlsx'),
         #{'fi': 2, 'nb': 4, 'se': 5, 'sv': 6, 'definition_fi': 7, 'explanation_nn': 8, 'nn': 9, 'sma': 10}),
        #(os.path.join(prefix, 'teknisk ordliste SG 10-03.xlsx'),
         #{'nb': 1, 'se': 2}),
         (os.path.join(prefix, 'Skolelinux SG 12-05.xlsx'),
         {'en': 1, 'nb': 3, 'se': 2, 'explanation_se': 7, 'explanation_nb': 8}),
         #(os.path.join(prefix, 'servodatfága tearbmalistu.xlsx'),
         #{'nb': 1, 'fi': 6, 'se': 2, 'more_info_se': 3, 'explanation_nb': 5}),
         #(os.path.join(prefix, 'servodatfága tearbmalistu.xlsx'),
         #{'nb': 1, 'fi': 6, 'se': 2, 'more_info_se': 3, 'explanation_nb': 5}),
    ]

    excel = ExcelImporter()
    for (path, lang_column) in mapping:
        excel.write(path, lang_column)

#export_to_mediawiki()

import glob

def print_termcenter():
    term_prefix = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/terms')
    terms_trees = {}
    for terms in glob.glob(term_prefix + '/terms*.xml'):
        lang = terms[terms.rfind('-') + 1:terms.rfind('.xml')]
        terms_trees[lang] = etree.parse(terms)

    tree = etree.parse(os.path.join(term_prefix, 'termcenter.xml'))

    ids = tree.xpath('.//e[@id=100830]')
    for id in ids[:2]:
        print('id', id.get('id'))
        for tg in id.xpath('./tg'):
            lang = tg.get('{http://www.w3.org/XML/1998/namespace}lang')
            mgs = terms_trees[lang].xpath('./e/mg[@idref=' + id.get('id') + ']')
            for mg in mgs:
                print('\t', lang, mg.getparent().find('./lg/l').text)
            #tgtree = tg.getroottree()
            #print('before')
            #tgtree.xinclude()
            #print('after')
    print('#concepts', len(ids))


#tw = TermWiki()
#tw.get_terms_expression()

'''Sammenligne et concept med TermWiki

Gå gjennom expressions
For hvert expression sjekk om den eksisterer i expressions
Sjekk om vi har vært innom samme idref i expression_id
Hvis ikke, sjekk om expression finnes i idref_expressions.
Hvis ja, lagre idref
'''