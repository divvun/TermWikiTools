# -*- coding: utf-8 -*-
""""""

class TermWiki(object):
    """Read concepts from the dump.xml file."""

    def __init__(self):
        self.pages = etree.Element('pages')

    def termwiki2xml(self, concept):
        page = etree.SubElement(self.pages, 'page')
        general = etree.SubElement(page, 'general')

        for key, value in concept['concept'].items():
            if key == 'collection':
                for collection in concept['concept']['collection']:
                    etree.SubElement(general, 'collection').text = collection
            else:
                etree.SubElement(general, key).text = value

        for concept_info in concept['concept_infos']:
            info = etree.SubElement(general, 'concept_info')
            for key, value in concept_info.items():
                etree.SubElement(info, key).text = value

        for related_expression in concept['related_expressions']:
            expression = etree.SubElement(general, 'expression')
            for key, value in related_expression.items():
                etree.SubElement(expression, key).text = value

        for related_concept in concept['related_concepts']:
            related_conc = etree.SubElement(general, 'related_concept')
            for key, value in related_concept.items():
                etree.SubElement(related_conc, key).text = value

    def read_concepts(self):
        tree = etree.parse(
            os.path.join(os.getenv('GTHOME'), 'words/terms/termwiki/dump.xml'))
        namespaces = {'m': 'http://www.mediawiki.org/xml/export-0.10/'}

        for page in tree.getroot().xpath('.//m:page', namespaces=namespaces):
            text = page.find('.//m:text', namespaces=namespaces)
            if (text is not None and
                    text.text is not None and '{{Concept' in text.text):
                concept = read_termwiki.parse_termwiki_concept(text.text)

                concept['concept']['title'] = page.find(
                    './/m:title', namespaces=namespaces).text

                self.termwiki2xml(concept)

        print(etree.tostring(self.pages, encoding='unicode', pretty_print=True))


