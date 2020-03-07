import unittest

import kronosparser.utils


class ParserTestCase(unittest.TestCase):
    def assertFind(self, parser, text, expected):
        if not isinstance(expected, list):
            expected = [expected]
        self.assertEqual(kronosparser.utils.find_all(parser, text), expected)

    def assertParsed(self, parser, text, expected):
        if not isinstance(expected, list):
            expected = [expected]
        results = kronosparser.utils.find_all(parser, text)
        self.assertEqual([r['parsed'] for r in results], expected)
