import kronosparser.utils

from .utils import ParserTestCase


class TestUtils(ParserTestCase):
    def test_caseless_literal_or(self):
        self.assertParsed(kronosparser.utils.caseless_literal_or(['foo', 'bar']), 'foo', 'foo')

    def test_caseless_literal_or_matches_longest(self):
        self.assertParsed(
            kronosparser.utils.caseless_literal_or(['foo', 'foox', 'fooxyz', 'fooxy']), 'fooxyza',
            'fooxyz')
