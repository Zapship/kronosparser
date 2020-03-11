import re
from datetime import datetime, timedelta

import pyparsing
import pytz
from dateutil import parser as date_parser


def find_all(expression, text):
    matches = []
    if expression is not None:
        for match in expression.scanString(text):
            # TODO(RA, 05-10-2016): prevent suppressed ParseResults objects from ever being created
            if len(match[0]) > 0:
                matches.append({
                    'text': text[match[1]:match[2]],
                    'parsed': match[0][0],
                    'start': match[1],
                    'end': match[2]
                })
    return matches


def caseless_literal_or(values):
    sorted_values = sorted(values, key=lambda x: (-len(x), x))
    return pyparsing.Regex('|'.join(re.escape(value) for value in sorted_values), re.IGNORECASE)


def _is_alphanumeric(value):
    return re.match(r'\w', value) is not None


def caseless_keyword(kw):
    leading = r'\b' if _is_alphanumeric(kw[0]) else ''
    trailing = r'\b' if _is_alphanumeric(kw[-1]) else ''
    return pyparsing.Regex('{}{}{}'.format(leading, re.escape(kw), trailing), re.IGNORECASE)


def caseless_keyword_or(values, no_lead=False, no_trail=False):
    sorted_values = sorted(values, key=lambda x: (-len(x), x))
    regexes = []
    for value in sorted_values:
        leading = r'\b'
        trailing = r'\b'
        if not _is_alphanumeric(value[0]) or no_lead:
            leading = ''
        if not _is_alphanumeric(value[-1]) or no_trail:
            trailing = ''
        regexes.append(re.escape(value))
    return pyparsing.Regex(r'{}({}){}'.format(leading, '|'.join(regexes), trailing), re.IGNORECASE)


def pluralize(words, pyparsing_regex=False):
    if isinstance(words, str):
        words = [words]
    if pyparsing_regex:
        return caseless_keyword_or(words + [plural(word) for word in words])
    return words + [plural(word) for word in words]


def plural(noun):
    if noun[-1] == 'y':
        if noun[-2] in 'aeiou':
            return noun + 's'
        return noun[:-1] + 'ies'
    if noun[-1] == 'f' and noun[-2] != 'f' and not all(
            [letter in 'aeiou' for letter in noun[-3:-1]]):
        return noun[:-1] + 'ves'
    if noun[-2:] == 'fe' and not all([letter in 'aeiou' for letter in noun[-4:-2]]):
        return noun[:-2] + 'ves'
    if noun[-1] in ['s', 'x', 'z'] or noun[-2:] in ['ch', 'sh']:
        return noun + 'es'
    return noun + 's'


def structurize(text, parsers):
    results = []
    for parser in parsers:
        results.extend(find_all(parser, text))
    return results


def set_date_for_interval(match):
    match['parsed'] = {'date': match['parsed']['interval']['start']}
    return match


def set_dates_with_timezone_fixes(match, timezone):
    tz = pytz.timezone(timezone)
    now = datetime.now()
    tz_hours_offset = tz.utcoffset(now).total_seconds() / 60 / 60

    parsed_output_keys = list(match['parsed'].keys())
    if 'datetime' in parsed_output_keys:
        _datetime = str(set_timezones_for_datetime(match['parsed'], tz, tz_hours_offset))
        match['parsed']['datetime'] = _datetime

    if 'date' in parsed_output_keys:
        match['parsed']['date'] = str(
            set_timezones_for_date(match['parsed'], tz_hours_offset).date())

    if 'interval' in parsed_output_keys:
        for boundary in ['start', 'end']:
            if 'date' in match['parsed']['interval'][boundary]:
                _date = str(
                    set_timezones_for_date(match['parsed']['interval'][boundary],
                                           tz_hours_offset).date())
                match['parsed']['interval'][boundary] = _date
            if 'datetime' in match['parsed']['interval'][boundary]:
                _datetime = str(
                    set_timezones_for_datetime(match['parsed']['interval'][boundary], timezone,
                                               tz_hours_offset))
                match['parsed']['interval'][boundary] = _datetime

    if 'utc' in parsed_output_keys:
        del match['parsed']['utc']
    if 'tz_threshold' in parsed_output_keys:
        del match['parsed']['tz_threshold']
        del match['parsed']['days_delta']


def set_timezones_for_datetime(match, tz, tz_hours_offset):
    matched_datetime = date_parser.parse(match['datetime'])
    non_utc_datetime = matched_datetime
    if match.get('utc'):
        utc_tz = pytz.timezone('UTC')
        utc_datetime = utc_tz.localize(matched_datetime)
        non_utc_datetime = utc_datetime.astimezone(tz)
    elif 'tz_threshold' in match:
        non_utc_datetime = set_threshold(match, tz_hours_offset, 'datetime')
    return non_utc_datetime


def set_timezones_for_date(match, tz_hours_offset):
    matched_date = date_parser.parse(match['date'])
    non_utc_date = matched_date
    if 'tz_threshold' in match:
        non_utc_date = set_threshold(match, tz_hours_offset, 'date')
    return non_utc_date


def set_threshold(match, tz_hours_offset, date_label):
    matched = date_parser.parse(match[date_label])
    days_delta = match['days_delta']
    tz_threshold = match['tz_threshold']
    final = matched
    if 0 < tz_threshold <= tz_hours_offset or 0 > tz_threshold >= tz_hours_offset:
        final = matched + timedelta(days=days_delta)
    return final
