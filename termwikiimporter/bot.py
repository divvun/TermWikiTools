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


class BotException(Exception):
    pass


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def parse_concept(lines):
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


def parse_related_expression(lines, sanctioned):
    template_contents = {}
    template_contents[u'sanctioned'] = 'No'
    template_contents[u'is_typo'] = 'No'
    template_contents[u'has_illegal_char'] = 'No'
    template_contents[u'pos'] = ''
    template_contents[u'collection'] = ''
    template_contents[u'status'] = ''
    template_contents[u'note'] = ''
    template_contents[u'equivalence'] = ''

    key = ''
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith('|'):
            (key, info) = l[1:].split('=')
            if key == 'in_header':
                pass
            else:
                if key == 'wordclass':
                    key = 'pos'
                template_contents[key] = info

        elif l.startswith('}}'):
            if template_contents['sanctioned'] == 'No':
                try:
                    if sanctioned[template_contents['language']] == 'Yes':
                        template_contents['sanctioned'] = 'Yes'
                except KeyError:
                    pass

            try:
                template_contents['expression']
                return importer.ExpressionInfo(**template_contents)
            except KeyError:
                raise BotException('expression not set in Related expression template')
        else:
            template_contents[key] = template_contents[key] + u' ' + l.strip()


def parse_related_concept(lines):
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
    expression_contents = {}
    counter = collections.defaultdict(int)

    key = ''
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith(u'|pos'):
            (key, info) = l[1:].split(u'=')
            expression_contents[key] = info
            if not info in ['N', 'V', 'A', 'Adv', 'Pron', 'Interj']:
                raise BotException('wrong pos', info)
        elif l.startswith(u'|language'):
            (key, info) = l[1:].split(u'=')
            expression_contents[key] = info
            if not info in ['se', 'sma', 'smj', 'sms', 'sms', 'en', 'nb', 'nb', 'sv', 'lat', 'fi', 'smn', 'nn']:
                raise BotException('wrong language', info)
            #print(lineno(), l)
        elif l.startswith(u'|sources') or l.startswith(u'|monikko') or l.startswith(u'|sanamuoto') or l.startswith(u'|origin') or l.startswith(u'|perussanatyyppi') or l.startswith(u'|wordclass') or l.startswith('|sanaluokka'):
            (key, info) = l[1:].split(u'=')
            counter[key] += 1
            #print(lineno(), l)
        elif l.startswith(u'}}'):
            return counter
            #return importer.RelatedConceptInfo(**expression_contents)
        else:
            raise BotException(u'Unknown:', l)

    print(lineno())

def expression_parser(text):
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
    sanctioned = {}
    concept = importer.Concept()
    lines = collections.deque(text.split(u'\n'))

    l = lines.popleft()
    if l.startswith(u'{{Concept'):
        (concept_info, sanctioned) = parse_concept(lines)
        for key, info in concept_info.iteritems():
            concept.add_concept_info(key, info)
        while len(lines) > 0:
            l = lines.popleft()
            if (l.startswith(u'{{Related expression') or
                    l.startswith(u'{{Related_expression')):
                try:
                    concept.add_expression(parse_related_expression(lines, sanctioned))
                except BotException:
                    pass
            elif l.startswith(u'{{Related concept'):
                concept.add_related_concept(parse_related_concept(lines))
            else:
                raise BotException('unhandled', l.strip())
        if not concept.is_empty:
            return unicode(concept)
    else:
        return text


def get_site():
    with open(os.path.join(os.getenv('HOME'), '.config', 'term_config.yaml')) as config_stream:
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

            #if botted_text != c.text:
                #print('should save')
                #print(botted_text)
                #print(c.text)
