# -*- coding: utf-8 -*-

#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this file. If not, see <http://www.gnu.org/licenses/>.
#
#   Copyright © 2018 The University of Tromsø
#   http://giellatekno.uit.no & http://divvun.no
#
"""Functions to import and export giella xml dicts to the TermWiki."""
import collections
import glob
import os
import sys
import uuid

import attr
from lxml import etree


@attr.s(frozen=True)
class Expression(object):
    """Representation of giella l and t dictionary elements."""

    lemma = attr.ib(validator=attr.validators.instance_of(str))
    lang = attr.ib(validator=attr.validators.instance_of(str))
    pos = attr.ib(validator=attr.validators.instance_of(str))

    langs = {
        'eng': 'en',
        'fin': 'fi',
        'nob': 'nb',
        'sma': 'sma',
        'sme': 'se',
        'smj': 'smj',
        'smn': 'smn',
        'swe': 'sv',
    }

    @property
    def pagename(self):
        """Construct a page name from the content of the class."""
        return '{} {} {}'.format(self.lemma, self.langs[self.lang], self.pos)

    @property
    def stempagename(self):
        """Construct a page name from the content of the class."""
        return '{}:{}'.format(type(self).__name__, self.pagename)

    @property
    def content(self):
        """Construct a termwiki page from the content of the the class."""
        return '{}{}\n|Lemma={}\n|Lang={}\n|Pos={}\n{}\n'.format(
            '{{',
            type(self).__name__, self.lemma, self.langs[self.lang], self.pos,
            '}}')


@attr.s(frozen=True)
class Translation(object):
    """Representation of a giella tg dictionary element."""
    tw_id = attr.ib(validator=attr.validators.instance_of(str))
    restriction = attr.ib(validator=attr.validators.instance_of(str))
    translations = attr.ib(validator=attr.validators.instance_of(set))
    examples = attr.ib(validator=attr.validators.instance_of(set))

    @property
    def content(self):
        """Construct the translation part of a dict page."""
        return '|Translation stem={}\n|Restriction={}\n{}\n{}\n'.format(
            '@@'.join(sorted([stem.pagename for stem in self.translations])),
            self.restriction, '}}', '\n'.join(
                sorted([example.content for example in self.examples])))


@attr.s(frozen=True)
class Example(object):
    """Representation of a giella xg dictionary element."""

    restriction = attr.ib(validator=attr.validators.instance_of(str))
    orig = attr.ib(validator=attr.validators.instance_of(str))
    translation = attr.ib(validator=attr.validators.instance_of(str))
    orig_source = attr.ib(validator=attr.validators.instance_of(str))
    translation_source = attr.ib(validator=attr.validators.instance_of(str))

    @property
    def content(self):
        """Construct a termwiki template from the content of the class."""
        return ('{}{}\n|Original={}\n|Source of original={}\n'
                '|Translation={}\n|Source of translation={}\n'
                '|Restriction={}\n{}'.format(
                    '{{',
                    type(self).__name__, self.orig, self.orig_source,
                    self.translation, self.translation_source,
                    self.restriction, '}}'))


class XmlDictExtractor(object):
    """Class to extract info from a giella xml dictionary."""

    def __init__(self, dictxml: etree.ElementTree) -> None:
        """Initialise the XmlDictExtractor class."""
        self.dictxml = dictxml
        langpair = dictxml.getroot().get('id')
        self.fromlang = langpair[:3]
        self.tolang = langpair[3:]

    @staticmethod
    def normalise_lemma(lemma: str) -> str:
        for offending, replacement in [('\n', ' '), ('  ', ' ')]:
            while offending in lemma:
                lemma = lemma.replace(offending, replacement)

        return lemma

    def l_or_t2stem(self, element: etree.Element) -> Expression:
        """Turn the given giella dictionary element into a Stem object."""
        return Expression(
            lemma=self.normalise_lemma(element.text),
            lang=self.tolang if element.tag == 't' else self.fromlang,
            pos=element.get('pos'))

    @staticmethod
    def xg2example(example_group: etree.Element) -> Example:
        """Turn an xg giella dictionary element into an Example object."""
        restriction = example_group.get('re') \
            if example_group.get('re') is not None else ''
        orig_source = example_group.find('.//x[@src]').get('src') \
            if example_group.find('.//x[@src]') is not None else ''
        translation_source = example_group.find('.//xt[@src]').get('src') \
            if example_group.find('.//xt[@src]') is not None else ''

        return Example(
            restriction=restriction,
            orig=example_group.find('.//x').text,
            translation=example_group.find('.//xt').text,
            orig_source=orig_source,
            translation_source=translation_source)

    @staticmethod
    def is_valid_example(example_group: etree.Element) -> bool:
        """Check if an xg element has valid content."""
        orig = example_group.find('./x')
        trans = example_group.find('./xt')
        return (orig.text is not None and orig.text.strip()
                and trans.text is not None and trans.text.strip())

    def translations(self, tg_element: etree.Element):
        """Find the valid t elements of a tg_element."""
        for t_element in tg_element.xpath('.//t[@pos]'):
            if t_element.text is not None:
                yield self.l_or_t2stem(t_element)

    @staticmethod
    def get_twid(lemma: str, tg_element: etree.Element) -> str:
        """Set a termwiki id if it does not exist."""
        if not tg_element.get('tw_id'):
            write_xml = True
            tw_id = '{} {}'.format(lemma, str(uuid.uuid4()))
            tg_element.set('tw_id', tw_id)

        return tg_element.get('tw_id')

    @staticmethod
    def get_restriction(tg_element: etree.Element) -> str:
        re_element = tg_element.find('./re')

        return re_element.text \
            if re_element is not None and re_element.text is not None else ''

    @staticmethod
    def get_translations(tg_element: etree.Element) -> set:
        return {stem for stem in self.translations(tg_element)}

    def get_examples(self, tg_element: etree.Element) -> set:
        return {
            self.xg2example(example_group)
            for example_group in tg_element.iter('xg')
            if self.is_valid_example(example_group)
        }

    def tg2translation(self, lemma: str,
                       tg_element: etree.Element) -> Translation:
        """Turn a tg giella dictionary element into a Translation object."""
        return Translation(
            tw_id=self.get_twid(lemma, tg_element),
            restriction=self.get_restriction(tg_element),
            translations=self.get_translations(tg_element),
            examples=self.get_examples(tg_element))

    @staticmethod
    def get_lang(element: etree.Element) -> str:
        """Get the xml:lang attribute of an etree Element."""
        return element.get('{http://www.w3.org/XML/1998/namespace}lang')

    def entry2tuple(self, entry: etree.Element) -> tuple:
        """Turn an e giella dictionary element into a tuple."""
        expression = self.l_or_t2stem(entry.find('.//l'))
        return (expression, [
            self.tg2translation(expression.lemma, translation_group)
            for translation_group in self.translation_groups(entry)
        ])

    def translation_groups(self, element):
        """Find tg elements only of the official translation language."""
        for translation_group in element.xpath('.//tg'):
            if self.get_lang(translation_group) == self.tolang:
                yield translation_group

    def register_stems(self, stemdict: collections.defaultdict) -> None:
        """Register all stems found in a giella dictionary file."""
        for stem in self.dictxml.xpath('.//l[@pos]'):
            stemdict[self.l_or_t2stem(stem)]

        for translation_group in self.translation_groups(self.dictxml):
            for stem in self.translations(translation_group):
                stemdict[stem]

    def r2dict(self, stemdict: collections.defaultdict) -> None:
        """Copy a giella dictionary file into a dict."""
        self.register_stems(stemdict)
        for entry_element in self.dictxml.iter('e'):
            stem, translations = self.entry2tuple(entry_element)
            stemdict[stem].extend(translations)


def valid_xmldict():
    """Parse xml dictionaries."""
    for pair in [
            'finsme', 'finsmn', 'nobsma', 'nobsme', 'nobsmj', 'nobsmj',
            'smafin', 'smanob', 'smasme', 'smefin', 'smenob', 'smesma',
            'smesmj', 'smesmn', 'smjnob', 'smjsme', 'smnsme', 'swesma'
    ]:
        dict_root = os.path.join(
            os.getenv('GTHOME'), 'words/dicts', pair, 'src')
        for xml_file in glob.glob(dict_root + '/*.xml'):
            if not xml_file.endswith('meta.xml') and 'Der_' not in xml_file:
                # TODO: handle Der_ files
                try:
                    parser = etree.XMLParser(
                        remove_comments=True, dtd_validation=True)
                    dictxml = etree.parse(xml_file, parser=parser)

                    origlang = dictxml.getroot().get(
                        '{http://www.w3.org/XML/1998/namespace}lang')
                    if origlang != pair[:3]:
                        raise SystemExit(
                            '{}: origlang {} in the file does not match '
                            'the language in the filename {}'.format(
                                xml_file, origlang, pair[:3]))

                    dict_id = dictxml.getroot().get('id')
                    if pair != dict_id:
                        raise SystemExit(
                            '{}: language pair in the file does not match '
                            'the one given in the filename {}'.format(
                                xml_file, dict_id, pair))

                    yield dictxml, xml_file
                except etree.XMLSyntaxError as error:
                    print(
                        'Syntax error in {} '
                        'with the following error:\n{}\n'.format(
                            xml_file, error),
                        file=sys.stderr)


def stemdict2dictpages(stemdict: collections.defaultdict):
    """Yield a dict pagename and dict content for each translation."""
    for lemma in stemdict:
        for number, translation in enumerate(stemdict[lemma], start=1):
            yield ('Dict:{} {:04d}'.format(lemma.pagename, number),
                   '{}Dict\n|Stempage={}\n{}'.format('{{', lemma.pagename,
                                                     translation.content))


def stemdict2stempages(stemdict: collections.defaultdict):
    """Yield a dict pagename and dict content for each translation."""
    for lemma in stemdict:
        yield (lemma.stempagename, lemma.content)


def parse_dicts() -> collections.defaultdict:
    """Extract xml dictionaries to a dict."""
    stemdict = collections.defaultdict(list)  # type: collections.defaultdict

    for dictxml, xml_file in valid_xmldict():
        xmldictextractor = XmlDictExtractor(dictxml=dictxml)
        xmldictextractor.register_stems(stemdict)
        xmldictextractor.r2dict(stemdict)

        with open(xml_file, 'wb') as xml_stream:
            xml_stream.write(
                etree.tostring(
                    dictxml,
                    encoding='UTF-8',
                    pretty_print=True,
                    xml_declaration=True))

    return stemdict


def main() -> None:
    """Parse the xml dictionaries."""
    parse_dicts()
