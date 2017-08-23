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


def fixed_collection_line(line):
    """Add Collection: to collection line if needed.

    Args:
        line (str): a line found in a termwiki page.

    Returns:
        str
    """
    if '|collection' in line and 'Collection:' not in line:
        return line.replace('=', '=Collection:')
    else:
        return line


def fix_collection(orig_text):
    """Add Collection: to collection line if needed.

    Args:
        orig_text

    Returns:
        str
    """
    return '\n'.join(
        [fixed_collection_line(line) for line in orig_text.split('\n')])


def remove_unwanted_tag(orig_text):
    """Remove unwanted attributes from a termwiki page.

    Args:
        orig_text

    Returns:
        str
    """
    unwanteds = ['is_typo', 'has_illegal_char']
    new_text = orig_text

    for unwanted in unwanteds:
        new_text = '\n'.join(
            [line for line in new_text.split('\n')
             if not line.startswith('|{}'.format(unwanted))])

    return new_text


def termwiki_concepts(site):
    namespaces = [
        'Boazodoallu',
        'Dihtorteknologiija ja diehtoteknihkka',
        'Dáidda ja girjjálašvuohta',
        'Eanandoallu',
        'Education',
        'Ekologiija ja biras',
        'Ekonomiija ja gávppašeapmi',
        'Geografiija',
        'Gielladieđa',
        'Gulahallanteknihkka',
        'Guolástus',
        'Huksenteknihkka',
        'Juridihkka',
        'Luonddudieđa ja matematihkka',
        'Medisiidna',
        'Mášenteknihkka',
        'Ođđa sánit',
        'Servodatdieđa',
        'Stáda almmolaš hálddašeapmi',
        'Teknihkka industriija duodji',
        'Álšateknihkka',
        'Ásttoáigi ja faláštallan',
        'Ávnnasindustriija',
    ]
    for category in site.allcategories():
        if category.name.replace('Kategoriija:', '') in namespaces:
            for page in category:
                yield page


def fix_content(orig_text):
    new_text = orig_text
    for fixer in [remove_unwanted_tag, fix_collection, concept_parser,
                  read_termwiki.handle_page]:
        new_text = fixer(new_text)

    return new_text


def fix_site():
    """Make the bot fix all pages."""
    counter = collections.defaultdict(int)
    print('Logging in …')
    site = get_site()

    print('About to iterate categories')
    for page in termwiki_concepts(site):

        orig_text = page.text()
        new_text = fix_content(orig_text)

        if orig_text != new_text:
            try:
                page.save(new_text, summary='Fixing content')
            except mwclient.errors.APIError as error:
                print(page.name, new_text, str(error), file=sys.stderr)

    for key in sorted(counter):
        print(key, counter[key])


def fix_dump():
    """Check to see if everything works as expected."""
    dump = os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml')
    mediawiki_ns = '{http://www.mediawiki.org/xml/export-0.10/}'
    tree = etree.parse(dump)

    for page in tree.getroot().iter('{}page'.format(mediawiki_ns)):
        title = page.find('.//{}text'.format(mediawiki_ns))
        if title is not None and title.text is not None and '|is_typo' in title.text:
            try:
                title.text = fix_content(title.text)
            except TypeError:
                print(lineno(),
                      page.find('.//{}title'.format(mediawiki_ns)).text,
                      title.text)

    tree.write(dump, pretty_print=True, encoding='utf8')


def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        fix_dump()
    elif len(sys.argv) == 2 and sys.argv[1] == 'site':
        fix_site()
    else:
        print(
            'Usage:\ntermbot site to fix the TermWiki\n'
            'termbot test to run a test on dump.xml')
