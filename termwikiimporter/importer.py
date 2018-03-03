# -*- coding: utf-8 -*-
"""Import/convert term files to termwiki."""


import argparse
import os
import re
import sys
from collections import defaultdict
import yaml

from lxml import etree
import openpyxl

from termwikiimporter import read_termwiki


class ExpressionError(Exception):
    pass


class Importer(object):
    """The import class.

    Attributes:
        filename (str): path to the file that should be imported
            to the termwiki
        termwiki (str): url to the termwiki
        concepts (list of ConceptInfo): all the concepts that have been
            found in filename
    """
    def __init__(self, filename):
        """Initialise the Importer class."""
        self.filename = filename
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

    for termfile in args.termfiles:
        excel = ExcelImporter(termfile)
        excel.get_concepts()
        excel.write(pagecounter)
