import unittest

import mock
from dateutil import parser as date_parser
from kronosparser import parse_dates


def utc_now_mock():
    return date_parser.parse('2020-03-11 12:16:02')


class TestKronosParserIntervalNotToDate(unittest.TestCase):
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    def test_parse_date(self, utc_now_mock):
        parsed_date = parse_dates('I need the report by tomorrow')
        expected_parse = [{
            'end': 29,
            'parsed': {
                'date': '2020-03-12'
            },
            'start': 21,
            'text': 'tomorrow'
        }]
        self.assertEqual(parsed_date, expected_parse)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    def test_parse_dates_interval_to_date_false(self, utc_now_mock):
        parsed_date = parse_dates('I need the report now, by tomorrow noon, or next week',
                                  interval_to_date=False)
        expected_parse = [{
            'end': 21,
            'parsed': {
                'datetime': '2020-03-11 05:16:02-07:00'
            },
            'start': 18,
            'text': 'now'
        }, {
            'end': 39,
            'parsed': {
                'datetime': '2020-03-12 12:00:00'
            },
            'start': 26,
            'text': 'tomorrow noon'
        }, {
            'end': 53,
            'parsed': {
                'interval': {
                    'end': '2020-03-22',
                    'start': '2020-03-16'
                }
            },
            'start': 44,
            'text': 'next week'
        }]
        self.assertEqual(parsed_date, expected_parse)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    def test_parse_datetimes_and_interval(self, utc_now_mock):
        parsed_date = parse_dates('I need the report now, by tomorrow noon, or next week')
        expected_parse = [{
            'end': 21,
            'parsed': {
                'datetime': '2020-03-11 05:16:02-07:00'
            },
            'start': 18,
            'text': 'now'
        }, {
            'end': 39,
            'parsed': {
                'datetime': '2020-03-12 12:00:00'
            },
            'start': 26,
            'text': 'tomorrow noon'
        }, {
            'end': 53,
            'parsed': {
                'date': '2020-03-16'
            },
            'start': 44,
            'text': 'next week'
        }]
        self.assertEqual(parsed_date, expected_parse)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    def test_parse_date_with_future(self, utc_now_mock):
        parsed_date = parse_dates('friday', future=True)
        expected_parse = [{
            'end': 6,
            'parsed': {
                'date': '2020-03-13'
            },
            'start': 0,
            'text': 'friday'
        }]
        self.assertEqual(parsed_date, expected_parse)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    def test_parse_date_with_no_future(self, utc_now_mock):
        parsed_date = parse_dates('friday', future=False)
        expected_parse = [{
            'end': 6,
            'parsed': {
                'date': '2020-03-06'
            },
            'start': 0,
            'text': 'friday'
        }]
        self.assertEqual(parsed_date, expected_parse)
