# -*- coding: utf-8 -*-


from __future__ import print_function
import collections
from lxml import etree
import inspect
import mwclient
import os
import sys
from termwikiimporter import importer
import yaml

import importer

class BotException(Exception):
    pass


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def parse_concept(lines):
    '''Parse a concept.

    Arguments:
        lines (list of str): the content of the termwiki page.
    '''
    template_contents = collections.OrderedDict()
    sanctioned = {}
    key = ''

    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith(u'|reviewed_'):
            lang = l.split(u'=')[0].replace(u'|reviewed_', u'')
            bool = l.strip().split(u'=')[1]
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
            template_contents[key] = template_contents[key] + u' ' + l.strip()


def get_pos(expression, language):
    '''Use lookup to determine the part of speech of an expression

    Arguments:
        expression (str): an expression
        language (str): language of the expression

    Returns:
        str: the wordclass

    Raises:
        BotException: If the output of lookup is unknown, raise
            this exception.
    '''
    command = ['lookup', u'-q', u'-flags', u'mbTT',
               os.path.join(os.getenv(u'GTHOME'), u'langs', language,
                            u'src', u'analyser-gt-norm.xfst')]
    runner = importer.ExternalCommandRunner()
    runner.run(command, to_stdin=expression)

    for analysis in runner.stdout.split('\n'):
        if (analysis.endswith('+N+Sg+Nom') or
                analysis.endswith('+N+G3+Sg+Nom') or
                analysis.endswith('+N+NomAg+Sg+Nom') or
                analysis.endswith('+N+Pl+Nom') or
                analysis.endswith('+N+Prop+Sem/Plc+Sg+Nom') or
                analysis.endswith('+N+Der/heapmi+A+Comp+Sg+Nom')):
            return u'N'
        elif (analysis.endswith('+V+TV+Inf') or
              analysis.endswith('+V+IV+Inf') or
              analysis.endswith('+V+IV+Pass+Inf')):
            return u'V'
        elif analysis.endswith('+A+Attr') or analysis.endswith('+A+Sg+Nom'):
            return u'A'
        elif analysis.endswith('+Adv'):
            return u'Adv'
        elif analysis.endswith('+Num+Sg+Nom'):
            return u'Num'
        elif analysis.endswith('?'):
            return u'?'

    raise BotException(u'Unknown\n' + runner.stdout.decode('utf8'))


def set_sanctioned(template_contents, sanctioned):
    if template_contents['sanctioned'] == 'No':
        try:
            if sanctioned[template_contents['language']] == 'Yes':
                template_contents['sanctioned'] = 'Yes'
        except KeyError:
            pass


def parse_related_expression(lines, sanctioned):
    '''Parse a Related expression template

    Determine the part of speech if it is not set inside the template.
    '''
    template_contents = {}
    template_contents[u'sanctioned'] = 'No'
    template_contents[u'is_typo'] = 'No'
    template_contents[u'has_illegal_char'] = 'No'
    template_contents[u'collection'] = ''
    template_contents[u'status'] = ''
    template_contents[u'note'] = ''
    template_contents[u'equivalence'] = ''

    key = ''
    pos = 'N/A'
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith('|'):
            (key, info) = l[1:].split('=')
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
                raise BotException('expression not set in Related expression template')
            else:
                #if pos == 'N/A':
                    #language = template_contents['language']
                    #if language in ['se', 'sma', 'smj'] and ' ' not in template_contents['expression']:
                        #if language == 'se':
                            #language = 'sme'
                        #ppos = get_pos(template_contents['expression'].encode('utf8'), language.encode('utf8'))
                        #if ppos == u'?':
                            #template_contents[u'is_typo'] = 'Yes'
                        #else:
                            #pos = ppos
                return (importer.ExpressionInfo(**template_contents), pos)
        else:
            template_contents[key] = template_contents[key] + u' ' + l.strip()


def parse_related_concept(lines):
    '''Parse the related concept part of a termwiki concept page.

    Arguments:
        lines (list of str): the content of the termwiki page.
    '''
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
            template_contents[key] = template_contents[key] + u' ' + l.strip()


def parse_expression(lines):
    '''Parse the content of an expression page.

    Arguments:
        lines (list of str): the content of the expression page
    '''
    expression_contents = {}
    counter = collections.defaultdict(int)

    key = ''
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith(u'|pos'):
            (key, info) = l[1:].split(u'=')
            expression_contents[key] = info
            if info not in ['N', 'V', 'A', 'Adv', 'Pron', 'Interj']:
                raise BotException('wrong pos', info)
        elif l.startswith(u'|language'):
            (key, info) = l[1:].split(u'=')
            expression_contents[key] = info
            if info not in ['se', 'sma', 'smj', 'sms', 'sms', 'en', 'nb', 'nb', 'sv', 'lat', 'fi', 'smn', 'nn']:
                raise BotException('wrong language', info)
            # print(lineno(), l)
        elif l.startswith(u'|sources') or l.startswith(u'|monikko') or l.startswith(u'|sanamuoto') or l.startswith(u'|origin') or l.startswith(u'|perussanatyyppi') or l.startswith(u'|wordclass') or l.startswith('|sanaluokka'):
            (key, info) = l[1:].split(u'=')
            counter[key] += 1
            # print(lineno(), l)
        elif l.startswith(u'}}'):
            return counter
            # return importer.RelatedConceptInfo(**expression_contents)
        else:
            raise BotException(u'Unknown:', l)

    print(lineno())


def expression_parser(text):
    '''Parse a expression page.

    Arguments:
        text (str): The content of an expression page.
    '''
    lines = collections.deque(text.split(u'\n'))
    counter = collections.defaultdict(int)
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith(u'{{Expression'):
            c = parse_expression(lines)
            if c is not None:
                for key, value in c.iteritems():
                    counter[key] += value

    return counter


def concept_parser(text):
    '''Parse a wiki page.

    Arguments:
        text (str): content of a wiki page

    Returns:
        str: the content of the page or the string representation
            of the concept
    '''
    sanctioned = {}
    concept = importer.Concept()
    lines = collections.deque(text.split(u'\n'))

    l = lines.popleft()
    if l.startswith(u'{{Concept'):
        (concept_info, sanctioned) = parse_concept(lines)
        for key, info in concept_info.iteritems():
            concept.add_concept_info(key, info)
        #print(lineno())
        while len(lines) > 0:
            l = lines.popleft()
            if (l.startswith(u'{{Related expression') or
                    l.startswith(u'{{Related_expression')):
                (expression_info, pos) = parse_related_expression(lines, sanctioned)
                concept.add_expression(expression_info)
                concept.expression_infos.pos = pos
            elif l.startswith(u'{{Related concept'):
                concept.add_related_concept(parse_related_concept(lines))
            else:
                raise BotException('unhandled', l.strip())
        #print(lineno())
        if not concept.is_empty:
            return unicode(concept)
    else:
        return text


def get_site():
    config_file = os.path.join(os.getenv('HOME'), '.config', 'term_config.yaml')
    with open(config_file) as config_stream:
        config = yaml.load(config_stream)
        site = mwclient.Site('gtsvn.uit.no', path='/termwiki/')
        site.login(config['username'], config['password'])

        return site


def main():
    print('Logging in …')
    site = get_site()
    categories = [
        u'Boazodoallu', u'Dihtorteknologiija ja diehtoteknihkka',
        u'Dáidda ja girjjálašvuohta', u'Eanandoallu',
        u'Ekologiija ja biras', u'Ekonomiija ja gávppašeapmi',
        u'Geografiija', u'Gielladieđa', u'Gulahallanteknihkka',
        u'Guolástus', u'Huksenteknihkka', u'Juridihkka',
        u'Luonddudieđa ja matematihkka', u'Medisiidna',
        u'Mášenteknihkka', u'Ođđa sánit', u'Servodatdieđa',
        u'Stáda, almmolaš hálddašeapmi', u'Teknihkka, industriija, duodji',
        u'Álšateknihkka', u'Ásttoáigi ja faláštallan', u'Ávnnasindustriija']

    print('About to iterate categories')
    for category in categories:
        print(category, end=' ')
        saves = 0
        total = 0
        for page in site.Categories[category]:
            total += 1
            text = page.text()
            try:
                botted_text = concept_parser(text)
                if text != botted_text:
                    sys.stdout.write('-')
                    sys.stdout.flush()
                    saves += 1
                    try:
                        page.save(botted_text, summary='Fixing content')
                    except mwclient.errors.APIError as e:
                        print(page.name, text, unicode(e), file=sys.stderr)

                else:
                    sys.stdout.write('|')
                    sys.stdout.flush()
            except importer.ExpressionException as e:
                print(page.name, str(e), file=sys.stderr)
            except KeyError as e:
                print(page.name, str(e), file=sys.stderr)
            except BotException as e:
                print(page.name, unicode(e), file=sys.stderr)

        print(u'\n' + category + u':', unicode(saves) + u'/' + unicode(total))


def test():
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))

    with open(os.path.join('termwikiimporter', 'test', 'abba.abc'), 'w') as abc:
        for page in abba.xpath(u'./page'):
            c = page.find('content')
            botted_text = concept_parser(c.text)
            if botted_text is not None:
                abc.write(botted_text.encode('utf8'))
                abc.write('\n')
            else:
                print(etree.tostring(page, encoding='utf8'))
