# -*- coding: utf-8 -*-



import collections
import inspect
import os
import sys
import traceback
import yaml

import mwclient
from lxml import etree

from termwikiimporter import importer, read_termwiki


class BotError(Exception):
    pass


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def parse_concept(lines):
    """Parse a concept.

    Arguments:
        lines (list of str): the content of the termwiki page.

    Returns:
        tuple (OrderedDict, dict): The OrderedDict contains the concept,
            sanctioned contains the langs that have been reviewed.
    """
    template_contents = collections.OrderedDict()
    sanctioned = {}
    key = ''

    while len(lines) > 0:
        line = lines.popleft().strip()
        if line.startswith('|reviewed_'):
            lang = line.split('=')[0].replace('|reviewed_', '')
            is_reviewed = line.strip().split('=')[1]
            sanctioned[lang] = is_reviewed
        elif line.startswith('|'):
            if line.startswith('|reviewed=') or line.startswith('|no picture'):
                pass
            else:
                (key, info) = line[1:].split('=', 1)
                template_contents[key] = info
        elif line.startswith('}}'):
            return (template_contents, sanctioned)
        else:
            template_contents[key] = template_contents[key] + ' ' + line.strip()


def set_sanctioned(template_contents, sanctioned):
    """Set the sanctioned key.

    Arguments:
        template_contents (dict): the content of related expressions of
            a termwiki page.
        sanctioned (dict): a dict containing the languages that have been
            reviewed in a termwiki concept.
    """
    if template_contents['sanctioned'] == 'No':
        try:
            if sanctioned[template_contents['language']] == 'Yes':
                template_contents['sanctioned'] = 'Yes'
        except KeyError:
            pass


def parse_related_expression(lines, sanctioned):
    """Parse a Related expression template.

    Determine the part of speech if it is not set inside the template.

    Arguments:
        lines (list of str): contains the related expressions found
            in a concept page of a termwiki page.
        sanctioned (dict): The set of languages that have been
            reviewed in the concept of the termwiki page.

    Returns:
        importer.ExpressionInfo: The content of the related expression.

    Raises:
        BotError: Raised when the expression is not set.
    """
    template_contents = {}
    template_contents['sanctioned'] = 'No'
    template_contents['has_illegal_char'] = 'No'
    template_contents['collection'] = ''
    template_contents['status'] = ''
    template_contents['note'] = ''
    template_contents['source'] = ''

    key = ''
    pos = 'N/A'
    while len(lines) > 0:
        line = lines.popleft().strip()
        if line.startswith('|'):
            equal_splits = line[1:].split('=')
            key = equal_splits[0]
            info = '='.join(equal_splits[1:])
            if key == 'in_header':
                pass
            else:
                if key == 'wordclass' or key == 'pos':
                    pos = info
                else:
                    template_contents[key] = info

        elif line.startswith('}}'):
            set_sanctioned(template_contents, sanctioned)
            try:
                template_contents['expression']
            except KeyError:
                raise BotError('expression not set in Related expression template')
            else:
                return (importer.ExpressionInfo(**template_contents), pos)
        else:
            template_contents[key] = template_contents[key] + ' ' + line.strip()


def parse_related_concept(lines):
    """Parse the related concept part of a termwiki concept page.

    Arguments:
        lines (list of str): the content of the termwiki page.

    Returns:
        importer.RelatedConceptInfo: The content of the related concept.
    """
    template_contents = {}
    template_contents['relation'] = ''

    key = ''
    while len(lines) > 0:
        line = lines.popleft().strip()
        if line.startswith('|'):
            (key, info) = line[1:].split('=')
            template_contents[key] = info
        elif line.startswith('}}'):
            return importer.RelatedConceptInfo(**template_contents)
        else:
            template_contents[key] = template_contents[key] + ' ' + line.strip()


def parse_expression(lines):
    """Parse the content of an expression page.

    Arguments:
        lines (list of str): the content of the expression page

    Raises:
        BotError: raised when there is either
            * an invalid part-of-speech is encountered
            * an unknown language is encountered
            * an potential invalid line is encountered

    """
    expression_contents = {}
    counter = collections.defaultdict(int)

    key = ''
    while len(lines) > 0:
        line = lines.popleft().strip()
        if line.startswith('|pos'):
            (key, info) = line[1:].split('=')
            expression_contents[key] = info
            if info not in ['N', 'V', 'A', 'Adv', 'Pron', 'Interj']:
                raise BotError('wrong pos', info)
        elif line.startswith('|language'):
            (key, info) = line[1:].split('=')
            expression_contents[key] = info
            if info not in ['se', 'sma', 'smj', 'sms', 'en', 'nb',
                            'sv', 'lat', 'fi', 'smn', 'nn']:
                raise BotError('wrong language', info)
            # print(lineno(), l)
        elif (line.startswith('|sources') or
              line.startswith('|monikko') or
              line.startswith('|sanamuoto') or
              line.startswith('|origin') or
              line.startswith('|perussanatyyppi') or
              line.startswith('|wordclass') or
              line.startswith('|sanaluokka')):
            (key, info) = line[1:].split('=')
            counter[key] += 1
            # print(lineno(), l)
        elif line.startswith('}}'):
            return counter
            # return importer.RelatedConceptInfo(**expression_contents)
        else:
            raise BotError('Unknown:', line)

    print(lineno())


def expression_parser(text):
    """Parse an expression page.

    Arguments:
        text (str): The content of an expression page.
    """
    lines = collections.deque(text.split('\n'))
    counter = collections.defaultdict(int)
    while len(lines) > 0:
        line = lines.popleft().strip()
        if line.startswith('{{Expression'):
            content = parse_expression(lines)
            if content is not None:
                for key, value in content.items():
                    counter[key] += value

    return counter


def concept_parser(text):
    """Parse a wiki page.

    Arguments:
        text (str): content of a wiki page

    Returns:
        str: the content of the page or the string representation
            of the concept
    """
    sanctioned = {}
    concept = importer.Concept()
    lines = collections.deque(text.split('\n'))

    line = lines.popleft()
    if line.startswith('{{Concept'):
        if not line.endswith('}}'):
            (concept_info, sanctioned) = parse_concept(lines)
            for key, info in concept_info.items():
                concept.add_concept_info(key, info)
        # print(lineno())
        while len(lines) > 0:
            line = lines.popleft()
            if (line.startswith('{{Related expression') or
                    line.startswith('{{Related_expression')):
                (expression_info, pos) = parse_related_expression(lines, sanctioned)
                concept.add_expression(expression_info)
                concept.expression_infos.pos = pos
            elif line.startswith('{{Related concept'):
                concept.add_related_concept(parse_related_concept(lines))
            else:
                raise BotError('unhandled', line.strip())
        # print(lineno())
        if not concept.is_empty:
            return str(concept)
    else:
        return text


def get_site():
    config_file = os.path.join(os.getenv('HOME'), '.config', 'term_config.yaml')
    with open(config_file) as config_stream:
        config = yaml.load(config_stream)
        site = mwclient.Site('satni.uit.no', path='/termwiki/')
        site.login(config['username'], config['password'])

        return site


def text_yielder(text):
    for line in text.split('\n'):
        if '|collection' in line and 'Collection:' not in line:
            yield line.replace('=', '=Collection:')
        else:
            yield line


def fix_collection(category, counter):
    if 'Expression' not in category.name:
        for page in category:
            counter['total'] += 1
            orig_text = page.text()
            if 'collection=' in orig_text and '=Collection:' not in orig_text:
                counter['collection'] += 1
                print('+', end='')
            else:
                print('.', end='')
            sys.stdout.flush()

            new_text = '\n'.join([line for line in text_yielder(page.text())])
            if new_text != orig_text:
                print()
                print('\t' + page.name)
                print()
                page.save(new_text,
                          summary='Add Collection: to collection lines')


def fix_other_issues(category, counter):
    for page in category:
        try:
            text = page.text()
            botted_text = concept_parser(text)
            cleaned_botted_text = read_termwiki.handle_page(
                botted_text, counter)
            if text != cleaned_botted_text:
                sys.stdout.write('-')
                counter['saves'] += 1
                try:
                    page.save(cleaned_botted_text, summary='Fixing content')
                except mwclient.errors.APIError as error:
                    print(page.name, text, str(error), file=sys.stderr)

            else:
                sys.stdout.write('|')
            sys.stdout.flush()
        except importer.ExpressionError as error:
            print('\n', lineno(), page.name, str(error), '\n', text,
                  file=sys.stderr)
        except KeyError as error:
            print('\n', lineno(), page.name, str(error), '\n', text,
                  file=sys.stderr)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("*** print_tb:")
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            print("*** print_exception:")
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            print("*** print_exc:")
            traceback.print_exc(limit=2, file=sys.stdout)
            print("*** format_exc, first and last line:")
            formatted_lines = traceback.format_exc().splitlines()
            print(formatted_lines[0])
            print(formatted_lines[-1])
            print("*** format_exception:")
            print(repr(traceback.format_exception(exc_type, exc_value,
                                                  exc_traceback)))
            print("*** extract_tb:")
            print(repr(traceback.extract_tb(exc_traceback)))
            print("*** format_tb:")
            print(repr(traceback.format_tb(exc_traceback)))
            print("*** tb_lineno:", exc_traceback.tb_lineno)
        except BotError as error:
            if 'Expression' not in page.name:
                print('\n', lineno(), page.name, str(error), '\n', text,
                      file=sys.stderr)
        except ValueError as error:
            print('\n', lineno(), page.name, str(error), '\n', text,
                  file=sys.stderr)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("*** print_tb:")
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
            print("*** print_exception:")
            traceback.print_exception(exc_type, exc_value, exc_traceback,
                                      limit=2, file=sys.stdout)
            print("*** print_exc:")
            traceback.print_exc(limit=2, file=sys.stdout)
            print("*** format_exc, first and last line:")
            formatted_lines = traceback.format_exc().splitlines()
            print(formatted_lines[0])
            print(formatted_lines[-1])
            print("*** format_exception:")
            print(repr(traceback.format_exception(exc_type, exc_value,
                                                  exc_traceback)))
            print("*** extract_tb:")
            print(repr(traceback.extract_tb(exc_traceback)))
            print("*** format_tb:")
            print(repr(traceback.format_tb(exc_traceback)))
            print("*** tb_lineno:", exc_traceback.tb_lineno)
        except TypeError:
            print('\n', lineno(), page.name, page.text)


def main():
    """Make the bot fix all pages."""
    counter = collections.defaultdict(int)
    print('Logging in …')
    site = get_site()
    print('About to iterate categories')
    for category in site.allcategories():
        print()
        print(category.name)
        if 'Expression' not in category.name:
            # fix_collection(category, counter)
            fix_other_issues(category, counter)

    for key in sorted(counter):
        print(key, counter[key])


def test():
    """Check to see if everything works as expected."""
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))

    with open(os.path.join('termwikiimporter', 'test', 'abba.abc'), 'w') as abc:
        for page in abba.xpath('./page'):
            content = page.find('content')
            botted_text = concept_parser(content.text)
            if botted_text is not None:
                abc.write(botted_text.encode('utf8'))
                abc.write('\n')
            else:
                print(etree.tostring(page, encoding='utf8'))
