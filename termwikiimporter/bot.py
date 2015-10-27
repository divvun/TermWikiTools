# -*- coding: utf-8 -*-


from __future__ import print_function
import collections
from lxml import etree
import inspect
import os
import sys
from termwikiimporter import importer


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
                (key, info) = l[1:].split('=')
                template_contents[key] = info
        elif l.startswith('}}'):
            return (template_contents, sanctioned)
        else:
            template_contents[key]  = template_contents[key] + u' ' + l.strip()


def parse_related_expression(lines, sanctioned):
    template_contents = {}
    template_contents[u'sanctioned'] = 'No'
    template_contents[u'is_typo'] = 'No'
    template_contents[u'has_illegal_char'] = 'No'
    template_contents[u'pos'] = ''
    template_contents[u'collection'] = ''
    template_contents[u'status'] = ''
    template_contents[u'note'] = ''


    key = ''
    while len(lines) > 0:
        l = lines.popleft().strip()
        if l.startswith('|'):
            (key, info) = l[1:].split('=')
            if key == 'in_header':
                pass
            else:
                if key == 'sanctioned':
                    if info == 'No':
                        try:
                            if sanctioned[template_contents['language']] == 'Yes':
                                info = 'Yes'
                        except KeyError:
                            pass
                template_contents[key] = info

        elif l.startswith('}}'):
            return importer.ExpressionInfo(**template_contents)
        else:
            template_contents[key]  = template_contents[key] + u' ' + l.strip()


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
            template_contents[key]  = template_contents[key] + u' ' + l.strip()


def bot(text):
    #klaff = collections.defaultdict(set)
    sanctioned = {}
    template_content = []
    inside_template = False
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
                concept.add_expression(parse_related_expression(lines, sanctioned))
            elif l.startswith(u'{{Related concept'):
                concept.add_related_concept(parse_related_concept(lines))
            else:
                raise BotException('unhandled', l.strip())
        if not concept.is_empty:
            return unicode(concept)
    else:
        return text


def main():
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))
    inside_template = False

    with open(os.path.join('termwikiimporter', 'test', 'abba.abc'), 'w') as abc:
        for page in abba.xpath(u'./page'):
            c = page.find('content')
            botted_text = bot(c.text)
            #abc.write(botted_text.encode('utf8'))
            #abc.write('\n')
            if botted_text != c.text:
                print('should save')
                print(botted_text)
                print(c.text)
