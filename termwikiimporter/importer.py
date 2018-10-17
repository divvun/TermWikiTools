# -*- coding: utf-8 -*-
"""Convert term files to termwiki parsable xml."""

import argparse
import os
import re
from collections import defaultdict

import openpyxl
import yaml
from lxml import etree

from termwikiimporter import read_termwiki


class Importer(object):
    """Convert files containing concepts to xml files.

    Attributes:
        filename (str): path to the file that should be imported
            to the termwiki
        concepts (list of concepts): all the concepts that have been
            found in filename
    """

    concepts = []
    pagecounter = 0

    def __init__(self, filename):
        """Initialise the Importer class."""
        self.filename = filename

    def write(self, ):
        """Write the result of the conversion.

        Write the concepts found to an xml file.
        """
        pages = etree.Element('pages')
        for concept in self.concepts:
            content = etree.Element('content')
            content.text = str(concept)

            page = etree.Element('page')
            try:
                page.set('title', ':'.join([
                    concept.category,
                    concept.data['related_expressions'][0]['expression']
                ]))
            except TypeError:
                self.pagecounter += 1
                page.set('title', ':'.join(
                    [concept.category, 'page_' + str(self.pagecounter)]))
            page.append(content)
            pages.append(page)

        with open(self.resultname, 'w') as to_file:
            to_file.write(
                etree.tostring(pages, pretty_print=True, encoding='unicode'))

    @property
    def resultname(self):
        """Name of the xml output file."""
        return os.path.splitext(self.filename)[0] + '.xml'

    def fresh_concept(self):
        """Make a dict that represents a termwiki concept."""
        concept = read_termwiki.Concept()
        concept.data['concept']['collection'].add(
            os.path.splitext(os.path.basename(self.filename))[0])

        return concept

    def add_concept(self, concept):
        """Add a concept to all concepts.

        Args:
            concept (dict): A termwiki concept
        """
        concept.to_concept_info()
        if (len(concept.data['related_expressions'])
                or len(concept.data['concept_infos'])):
            self.concepts.append(concept)


class ExcelImporter(Importer):
    """Convert excel files to xml."""

    splitters = re.compile(r'[,;\n\/]')
    counter = defaultdict(int)

    def collect_expressions(self, startline):
        """Find expressions found in startline.

        Args:
            startline (str): the content of an expression line

        Returns:
            list of str: the expression found in startline
        """
        expressions = []

        if ('~' in startline or '?' in startline
                or re.search('[()-]', startline) is not None):
            expressions.append(startline.replace('\n', ' '))
        else:
            for token in self.splitters.split(startline):
                finaltoken = token.strip().lower()
                if len(finaltoken) > 0:
                    expressions.append(finaltoken)

        return expressions

    @property
    def fileinfo(self):
        """Parse information about excel files from a yaml file."""
        yamlname = self.filename.replace('.xlsx', '.yaml')
        with open(yamlname) as yamlfile:
            return yaml.load(yamlfile)

    def get_concepts(self):
        """Extract concepts from excel files."""
        workbook = openpyxl.load_workbook(self.filename)

        for ws_title, ws_info in list(self.fileinfo.items()):
            sheet = workbook[ws_title]

            for row in range(2, sheet.max_row + 1):
                self.counter['concepts'] += 1

                concept = self.fresh_concept()
                concept.data['concept']['main_category'] = ws_info['main_category']

                pos = ''
                if (ws_info['wordclass'] != 0 and
                        sheet.cell(row=row, column=ws_info['wordclass']).value
                        is not None):
                    pos = sheet.cell(
                        row=row, column=ws_info['wordclass']).value.strip()

                for language, col in list(ws_info['terms'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        expression_line = sheet.cell(
                            row=row, column=col).value.strip()
                        for expression in self.collect_expressions(
                                expression_line):
                            concept.data['related_expressions'].append({
                                'expression':
                                expression,
                                'pos':
                                pos,
                                'language':
                                language,
                            })

                for info, col in list(ws_info['other_info'].items()):
                    if sheet.cell(row=row, column=col).value is not None:
                        concept.data['concept'][info] = sheet.cell(
                            row=row, column=col).value.strip()

                self.add_concept(concept)

        for key, count in list(self.counter.items()):
            print(
                '\t',
                key,
                count,
            )


class ArbeidImporter(Importer):
    """Convert database dumps in text format to xml."""

    gram_re = re.compile('<GRAM (.+)>')
    no_concepts = 0
    definitions = defaultdict(list)
    explanations = defaultdict(list)
    expressions = []
    current_lang = 'nb'

    def reset_concept(self):
        """Reset internal concept structures."""
        self.definitions = defaultdict(list)
        self.explanations = defaultdict(list)
        self.expressions = []

    def to_concept(self):
        """Turn dump concept to termwiki concept."""
        self.no_concepts += 1
        term = self.fresh_concept()
        term['concept']['main_category'] = 'HUPPSANN'
        for lang in self.definitions:
            concept_info = defaultdict(str)
            concept_info['language'] = lang
            concept_info['definition'] = '\n'.join(self.definitions[lang])
            concept_info['explanation'] = '\n'.join(self.explanations[lang])
            term['concept_infos'].append(concept_info)
        term['related_expressions'] = self.expressions
        self.add_concept(term)
        self.reset_concept()

    def parse_line(self, line, number):
        """Parse lines.

        Args:
            line (str): line that should be parsed
            number (int): the number of the line to be parsed
        """
        if line.startswith('smi →'):
            self.current_lang = 'sma'
            self.expressions.extend(
                self.parse_expression_line(line[len('smi →'):].strip(),
                                           self.current_lang))
        elif line.startswith('nb	'):
            self.current_lang = 'nb'
            self.expressions.extend(
                self.parse_expression_line(line[len('nb	'):].strip(),
                                           self.current_lang))
        elif line.startswith('nbDEF '):
            self.definitions[self.current_lang].append(
                line[len('nbDEF '):].strip())
        elif line.startswith('nbMRKN '):
            self.explanations[self.current_lang].append(
                line[len('nbMRKN '):].strip())
        elif line.startswith('klass	'):
            pass
        else:
            print('lineno {}: «{}»'.format(number, line))

    def get_concepts(self):
        """Find concepts in a database dump in text format."""
        start = re.compile(r'^\w\w\w$')
        with open(self.filename) as arbeid:
            for number, line in enumerate(arbeid, start=1):
                line = line.strip()
                if line:
                    if start.match(line):
                        self.to_concept()
                    else:
                        self.parse_line(line, number)

        print(self.no_concepts)

    def parse_expression_line(self, expression_line, language):
        """Parse a line containing expressions.

        Args:
            expression_line (str): string containing expressions
            language (str): language of the expressions

        Returns:
            list of dict: expressions as a list of dicts
        """
        expressions = []
        has_synonym = '<SY>' in expression_line
        for semicolontoken in expression_line.split(';'):
            if '<STE>' not in semicolontoken:
                not_synonym_block = '<SY>' not in semicolontoken
                semicolontoken = semicolontoken.replace('<SY>', '')

                found_gram = self.gram_re.search(semicolontoken)
                pos = found_gram.group(1) if found_gram else ''
                if found_gram:
                    semicolontoken = semicolontoken[:found_gram.start()]

                for commatoken in semicolontoken.split(','):
                    expression = {
                        'language': language,
                        'expression': commatoken.strip(),
                    }

                    if pos:
                        if pos in [
                                'm', 'n', 'c', 'm pl', 'n pl', 'm n', 'c pl',
                                'pl'
                        ]:
                            expression['pos'] = 'N'
                        elif pos == 'v':
                            expression['pos'] = 'V'
                        elif pos == 'adj':
                            expression['pos'] = 'Adj'
                        else:
                            print('«{}»: {}'.format(pos,
                                                    expression['expression']))

                    if has_synonym and not_synonym_block:
                        expression['status'] = 'recommended'

                    expressions.append(expression)

        return expressions


def parse_options():
    """Parse options given to the script."""
    parser = argparse.ArgumentParser(
        description='Convert files containing terms to TermWiki mediawiki '
        'format')

    parser.add_argument(
        'termfiles',
        nargs='+',
        help='One or more files containing terms. Each file must have a '
        'yaml file that inform how they should be treated.')

    args = parser.parse_args()

    return args


def init_file(filename):
    """Produce the correct Importer according to filename."""
    if filename.endswith('.xlsx'):
        return ExcelImporter(filename)
    else:
        return ArbeidImporter(filename)


def main():
    """Convert files to termwiki format."""
    args = parse_options()

    for termfile in args.termfiles:
        importer = init_file(termfile)
        importer.get_concepts()
        importer.write()
