# -*- coding: utf-8 -*-


from __future__ import print_function
import collections
from lxml import etree
import inspect
import os
import sys


def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def bot(text):
    #klaff = collections.defaultdict(set)
    sanctioned = {}
    template_content = []
    inside_template = False
    for l in text.split(u'\n'):
        if l.startswith(u'{{'):
            template_content.append(l.strip())
            key = l.strip()
            inside_template = True
        elif l.startswith(u'|') and inside_template == True:
            if l.startswith(u'|reviewed_'):
                lang = l.split(u'=')[0].replace(u'|reviewed_', u'')
                bool = l.strip().split(u'=')[1]
                sanctioned[lang] = bool
            elif l.startswith(u'|language'):
                template_content.append(l.strip())
                if (key == u'{{Related expression' or
                        key == u'{{Related_expression'):
                    lang = l.strip().split(u'=')[1]
                    try:
                        template_content.append(u'|sanctioned=' +
                                                sanctioned[lang])
                    except KeyError:
                        pass
            elif (l.startswith(u'|in_header') or
                  l.startswith(u'|no picture') or
                  l.startswith(u'|reviewed=')):
                pass
            else:
                template_content.append(l.strip())
        elif l.startswith(u'}}'):
            template_content.append(l.strip())
            key = u''
            inside_template = False
        elif inside_template == True:
            template_content[-1]  = template_content[-1] + u' ' + l.strip()
        else:
            template_content.append(l.strip())

    return u'\n'.join(template_content)

def main():
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))
    inside_template = False

    with open(os.path.join('termwikiimporter', 'test', 'abba.abc'), 'w') as abc:
        for page in abba.xpath(u'./page[@title="Boazodoallu:ađaiduvvat"]'):
            c = page.find('content')
            botted_text = bot(c.text)
            #abc.write(botted_text.encode('utf8'))
            #abc.write('\n')
            if botted_text != c.text:
                print('should save')
                print(botted_text)
                print(c.text)