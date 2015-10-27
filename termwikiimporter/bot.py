# -*- coding: utf-8 -*-


from __future__ import print_function
import collections
from lxml import etree
import os


def main():
    klaff = collections.defaultdict(set)
    abba = etree.parse(os.path.join('termwikiimporter', 'test', 'abba.txt'))
    inside = False
    for page in abba.xpath('./page'):
        c = page.find('content')
        for l in c.text.split('\n'):
            if l.startswith('{{'):
                key = l.strip()
                inside = True
            if l.startswith('|') and inside == True:
                klaff[key].add(l.split('=')[0])
            if l.startswith('}}'):
                key = ''
                inside = False

    for key, values in klaff.items():
        print(key)
        for value in values:
            print('\t', value)

main()