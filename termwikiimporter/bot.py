# -*- coding: utf-8 -*-



import collections
import inspect
import os
import sys
import traceback

import mwclient
import yaml
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
        l = lines.popleft().strip()
        if l.startswith('|reviewed_'):
            lang = l.split('=')[0].replace('|reviewed_', '')
            bool = l.strip().split('=')[1]
            sanctioned[lang] = bool
        elif l.startswith('|'):
            if l.startswith('|reviewed=') or l.startswith('|no picture'):
                pass
            else:
                (key, info) = l[1:].split('=', 1)
                template_contents[key] = info
        elif l.startswith('}}'):
            return (template_contents, sanctioned)
        else:
            template_contents[key] = template_contents[key] + ' ' + l.strip()


def get_pos(expression, language):
    """Use lookup to determine the part of speech of an expression.

    Arguments:
        expression (str): an expression
        language (str): language of the expression

    Returns:
        str: the wordclass

    Raises:
        BotError: If the output of lookup is unknown, raise
            this exception.
    """
    command = ['lookup', '-q', '-flags', 'mbTT',
               os.path.join(os.getenv('GTHOME'), 'langs', language,
                            'src', 'analyser-gt-norm.xfst')]
    runner = importer.ExternalCommandRunner()
    runner.run(command, to_stdin=expression.encode('utf8'))

    for analysis in runner.stdout.split('\n'):
        if (analysis.endswith('+N+Sg+Nom') or
                analysis.endswith('+N+G3+Sg+Nom') or
                analysis.endswith('+N+NomAg+Sg+Nom') or
                analysis.endswith('+N+Pl+Nom') or
                analysis.endswith('+N+Prop+Sem/Plc+Sg+Nom') or
                analysis.endswith('+N+Prop+Sem/Plc+Pl+Nom') or
                analysis.endswith('+N+Prop+Sem/Plc+Der/lasj+A+Sg+Nom') or
                analysis.endswith('+N+Der/heapmi+A+Comp+Sg+Nom') or
                analysis.endswith('+N+ACR+Sg+Nom')):
            return 'N'
        elif (analysis.endswith('+V+TV+Inf') or
              analysis.endswith('+V+IV+Inf') or
              analysis.endswith('+V+IV+Pass+Inf') or
              analysis.endswith('+V+TV+Der/InchL+V+Inf')):
            return 'V'
        elif analysis.endswith('+A+Attr') or analysis.endswith('+A+Sg+Nom'):
            return 'A'
        elif analysis.endswith('+Adv'):
            return 'Adv'
        elif analysis.endswith('+Num+Sg+Nom'):
            return 'Num'
        elif analysis.endswith('?'):
            return '?'

    print('Unknown\n' + runner.stdout)
    return '?'


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
    template_contents['is_typo'] = 'No'
    template_contents['has_illegal_char'] = 'No'
    template_contents['collection'] = ''
    template_contents['status'] = ''
    template_contents['note'] = ''
    template_contents['equivalence'] = ''

    key = ''
    pos = 'N/A'
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith('|'):
            equal_splits = l[1:].split('=')
            key = equal_splits[0]
            info = '='.join(equal_splits[1:])
            if key == 'in_header':
                pass
            else:
                if key == 'wordclass' or key == 'pos':
                    pos = info
                else:
                    template_contents[key] = info

        elif l.startswith('}}'):
            set_sanctioned(template_contents, sanctioned)
            try:
                template_contents['expression']
            except KeyError:
                raise BotError('expression not set in Related expression template')
            else:
                if pos == 'N/A':
                    language = template_contents['language']
                    if language in ['se', 'sma', 'smj'] and ' ' not in template_contents['expression']:
                        if language == 'se':
                            language = 'sme'
                        ppos = get_pos(template_contents['expression'], language)
                        if ppos == '?':
                            template_contents['is_typo'] = 'Yes'
                        else:
                            pos = ppos
                return (importer.ExpressionInfo(**template_contents), pos)
        else:
            template_contents[key] = template_contents[key] + ' ' + l.strip()


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
        l = lines.popleft().strip()
        if l.startswith('|'):
            (key, info) = l[1:].split('=')
            template_contents[key] = info
        elif l.startswith('}}'):
            return importer.RelatedConceptInfo(**template_contents)
        else:
            template_contents[key] = template_contents[key] + ' ' + l.strip()


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
        l = lines.popleft().strip()
        if l.startswith('|pos'):
            (key, info) = l[1:].split('=')
            expression_contents[key] = info
            if info not in ['N', 'V', 'A', 'Adv', 'Pron', 'Interj']:
                raise BotError('wrong pos', info)
        elif l.startswith('|language'):
            (key, info) = l[1:].split('=')
            expression_contents[key] = info
            if info not in ['se', 'sma', 'smj', 'sms', 'sms', 'en', 'nb', 'nb', 'sv', 'lat', 'fi', 'smn', 'nn']:
                raise BotError('wrong language', info)
            # print(lineno(), l)
        elif l.startswith('|sources') or l.startswith('|monikko') or l.startswith('|sanamuoto') or l.startswith('|origin') or l.startswith('|perussanatyyppi') or l.startswith('|wordclass') or l.startswith('|sanaluokka'):
            (key, info) = l[1:].split('=')
            counter[key] += 1
            # print(lineno(), l)
        elif l.startswith('}}'):
            return counter
            # return importer.RelatedConceptInfo(**expression_contents)
        else:
            raise BotError('Unknown:', l)

    print(lineno())


def expression_parser(text):
    """Parse an expression page.

    Arguments:
        text (str): The content of an expression page.
    """
    lines = collections.deque(text.split('\n'))
    counter = collections.defaultdict(int)
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith('{{Expression'):
            c = parse_expression(lines)
            if c is not None:
                for key, value in c.items():
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

    l = lines.popleft()
    if l.startswith('{{Concept'):
        if not l.endswith('}}'):
            (concept_info, sanctioned) = parse_concept(lines)
            for key, info in concept_info.items():
                concept.add_concept_info(key, info)
        #print(lineno())
        while len(lines) > 0:
            l = lines.popleft()
            if (l.startswith('{{Related expression') or
                    l.startswith('{{Related_expression')):
                (expression_info, pos) = parse_related_expression(lines, sanctioned)
                concept.add_expression(expression_info)
                concept.expression_infos.pos = pos
            elif l.startswith('{{Related concept'):
                concept.add_related_concept(parse_related_concept(lines))
            else:
                raise BotError('unhandled', l.strip())
        #print(lineno())
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
        if ('|collection') in line and 'Collection:' not in line:
            yield line.replace('=', '=Collection:')
        else:
            yield line


def fix_collection(category, counter):
    if 'Expression' not in category.name:
        for page in category:
            counter['total'] += 1
            orig_text = page.text()
            if 'collection=' in orig_text and not '=Collection:' in orig_text:
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
                except mwclient.errors.APIError as e:
                    print(page.name, text, str(e), file=sys.stderr)

            else:
                sys.stdout.write('|')
            sys.stdout.flush()
        except importer.ExpressionError as e:
            print('\n', lineno(), page.name, str(e), '\n', text,
                  file=sys.stderr)
        except KeyError as e:
            print('\n', lineno(), page.name, str(e), '\n', text,
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
        except BotError as e:
            if 'Expression' not in page.name:
                print('\n', lineno(), page.name, str(e), '\n', text,
                      file=sys.stderr)
        except ValueError as e:
            print('\n', lineno(), page.name, str(e), '\n', text,
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
        except TypeError as error:
            print('\n', lineno(), page.name, page.text)


def main():
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
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))

    with open(os.path.join('termwikiimporter', 'test', 'abba.abc'), 'w') as abc:
        for page in abba.xpath('./page'):
            c = page.find('content')
            botted_text = concept_parser(c.text)
            if botted_text is not None:
                abc.write(botted_text.encode('utf8'))
                abc.write('\n')
            else:
                print(etree.tostring(page, encoding='utf8'))
