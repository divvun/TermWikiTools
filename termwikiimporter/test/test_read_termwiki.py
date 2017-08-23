# -*- coding: utf-8 -*-
"""Test the functions and classes found in read_termwiki."""

import collections
import unittest

from termwikiimporter import read_termwiki


class TestReadTermwiki(unittest.TestCase):
    """Test the functions in read_termwiki."""

    def test_remove_is_typo(self):
        """Check that is_typo is removed from Related expression."""
        contains_is_typo = '''{{Concept}}
{{Related expression
|expression=test
|language=se
|is_typo=Yes
}}
'''

        got = read_termwiki.term_to_string(
            read_termwiki.parse_termwiki_concept(
                contains_is_typo, collections.defaultdict(int)))
        self.assertFalse('is_typo' in got)
