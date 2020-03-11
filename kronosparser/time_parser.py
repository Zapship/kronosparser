import datetime
import re

import pyparsing
from dateutil.relativedelta import relativedelta
from pyparsing import Optional

from kronosparser import utils
from kronosparser.time_interval import TimeInterval
from kronosparser.word_number import units

_BEGINNING = 1
_MIDDLE = 2
_END = 3

_CENTURY_CHANGE = 30


def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0)


def utc_today():
    return datetime.datetime.utcnow().date()


def past_future_wrap(func):
    def decorated_func(tokens, origin=None):
        if origin is None:
            origin = utc_today()
        if 'weekday_ref' in tokens and 'dir_rel' not in tokens.weekday_ref:
            for i, tag in [(-1, 'past'), (1, 'future')]:
                toks = tokens.copy()
                toks.weekday_ref.dir_rel = i
                func(toks, origin=origin)
                tokens[tag] = {'date': toks['date']}
                if 'days_delta' in toks:
                    tokens[tag]['days_delta'] = toks['days_delta']
                if 'tz_threshold' in toks:
                    tokens[tag]['tz_threshold'] = toks['tz_threshold']
        else:
            func(tokens, origin=origin)

    return decorated_func


def past_future_unwrap(func):
    time_keys = ['past', 'future']

    def decorated_func(tokens):
        if 'past' in tokens:
            for time_key in time_keys:
                toks = dict(tokens[time_key])
                for key, val in tokens.items():
                    if key not in time_keys:
                        toks[key] = val
                func(toks)
                for key, val in toks.items():
                    tokens[time_key][key] = val
        else:
            func(tokens)

    return decorated_func


def tz_decorate(key, rel_hour=0):
    def tz_decorator(func):
        def decorated_func(tokens, origin=None):
            if origin is None:
                origin = utc_today()
            datetime_utc = func(tokens, origin=origin)
            now = utc_now()
            diff_hour = (now.hour - rel_hour) % 24
            if diff_hour >= 12:
                datetime_alt = func(tokens, origin=origin + datetime.timedelta(days=1))
            else:
                datetime_alt = func(tokens, origin=origin - datetime.timedelta(days=1))
            if datetime_utc and datetime_alt:
                tokens[key] = datetime_utc
                if datetime_utc != datetime_alt:
                    tokens['days_delta'] = (datetime_alt - datetime_utc).days
                    if diff_hour >= 12:
                        tokens['tz_threshold'] = 24 - diff_hour
                    else:
                        tokens['tz_threshold'] = -diff_hour - 1
            elif datetime_utc or datetime_alt:
                tokens[key] = datetime_utc or datetime_alt
            else:
                tokens['datetime_parsing_error'] = True
                return

        return decorated_func

    return tz_decorator


def before_after_any(tokens):
    start = None
    end = None
    for start_type in ['exclusive_start', 'inclusive_start']:
        if start_type in tokens:
            if 'future' in tokens[start_type]:
                start = tokens[start_type]['future']['calculatedTime']
            else:
                start = tokens[start_type]['calculatedTime']
            if isinstance(start, TimeInterval):
                start = start.get_end()
                if start is None:
                    tokens['datetime_parsing_error'] = True
                    return
            if isinstance(start, datetime.date) and start_type == 'exclusive_start':
                start += datetime.timedelta(days=1)
            break
    for end_type in ['exclusive_end', 'inclusive_end']:
        if end_type in tokens:
            if 'future' in tokens[end_type]:
                end = tokens[end_type]['future']['calculatedTime']
                del tokens[end_type]
            else:
                end = tokens[end_type]['calculatedTime']
            if isinstance(end, TimeInterval):
                end = end.get_start()
                if end is None:
                    tokens['datetime_parsing_error'] = True
                    return
            if isinstance(end, datetime.date) and end_type == 'exclusive_end':
                end -= datetime.timedelta(1)
            break
    if 'past' in tokens:
        del tokens['past']
        del tokens['future']
    tokens['calculatedTime'] = TimeInterval(start, end)


def set_datetime(tokens):
    if 'past' in tokens:
        return {
            'past': set_datetime_single(tokens['past']),
            'future': set_datetime_single(tokens['future'])
        }
    else:
        return set_datetime_single(tokens)


def set_datetime_single(tokens):
    result = {}
    if tokens.get('datetime_parsing_error') or 'calculatedTime' not in tokens:
        return {'datetime_parsing_error': True}
    result['utc'] = tokens.get('utc', False)
    if 'days_delta' in tokens and 'tz_threshold' in tokens:
        result['days_delta'] = tokens['days_delta']
        result['tz_threshold'] = tokens['tz_threshold']
    if isinstance(tokens['calculatedTime'], datetime.datetime):
        result['datetime'] = tokens['calculatedTime'].isoformat(' ')
    elif isinstance(tokens['calculatedTime'], datetime.date):
        result['date'] = tokens['calculatedTime'].isoformat()
    elif isinstance(tokens['calculatedTime'], datetime.time):
        if utc_now().hour >= 12:
            result['days_delta'] = 1
            result['tz_threshold'] = 24 - utc_now().hour
        else:
            result['days_delta'] = -1
            result['tz_threshold'] = -utc_now().hour - 1
        result['datetime'] = datetime.datetime.combine(utc_today(),
                                                       tokens['calculatedTime']).isoformat(' ')
    elif isinstance(tokens['calculatedTime'], TimeInterval):
        result['interval'] = {
            'start': tokens['calculatedTime'].get_start().isoformat(),
            'end': tokens['calculatedTime'].get_end().isoformat()
        }
    return result


def process_two_digits_year(tokens):
    two_digit_token = int(tokens[0])
    if two_digit_token > _CENTURY_CHANGE:  # TODO: Will break after singularity!
        return 1900 + two_digit_token
    else:
        return 2000 + two_digit_token


def is_leap_year(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def year_interval(year_num):
    return TimeInterval(datetime.date(year_num, 1, 1), datetime.date(year_num, 12, 31))


def quarter_by_date(origin=None):
    origin = origin or utc_today()
    if origin.month < 4:
        return 1
    elif origin.month < 7:
        return 2
    elif origin.month < 10:
        return 3
    else:
        return 4


def quarter_interval(quarter_num, year_num):
    q = {
        1: TimeInterval(datetime.date(year_num, 1, 1), datetime.date(year_num, 3, 31)),
        2: TimeInterval(datetime.date(year_num, 4, 1), datetime.date(year_num, 6, 30)),
        3: TimeInterval(datetime.date(year_num, 7, 1), datetime.date(year_num, 9, 30)),
        4: TimeInterval(datetime.date(year_num, 10, 1), datetime.date(year_num, 12, 31))
    }
    return q[quarter_num]


def month_days(month_num, year_num):
    return [None, 31, 29 if is_leap_year(year_num) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30,
            31][month_num]


def month_interval(month_num, year_num):
    return TimeInterval(datetime.date(year_num, month_num, 1),
                        datetime.date(year_num, month_num, month_days(month_num, year_num)))


def convert_to_timedelta(tokens):
    unit = tokens.time_unit.lower().rstrip('s')
    dir_tok = tokens.dir_abs * tokens.get('qty', 1)
    tokens['timeOffset'] = {
        'year': relativedelta(years=dir_tok),
        'month': relativedelta(months=dir_tok),
        'week': datetime.timedelta(weeks=dir_tok),
        'day': datetime.timedelta(days=dir_tok),
        'hour': datetime.timedelta(hours=dir_tok),
        'minute': datetime.timedelta(minutes=dir_tok),
        'second': datetime.timedelta(seconds=dir_tok),
    }[unit]


@past_future_wrap
@tz_decorate('date')
def convert_to_day(tokens, origin=None):
    if 'weekday_ref' in tokens:
        today_num = origin.weekday()
        named_day_num = weekday_number_mapping(tokens.weekday_ref.day_name.lower())
        diff = named_day_num - today_num
        if tokens.weekday_ref.dir_rel >= 0:
            day_diff = diff if diff > 0 else diff + 7
        else:
            day_diff = diff if diff < 0 else diff - 7
        return origin + datetime.timedelta(days=day_diff)
    else:
        name = tokens.name.lower()
        return {
            'today': origin,
            'yesterday': origin + datetime.timedelta(days=-1),
            'tomorrow': origin + datetime.timedelta(days=1),
        }[name]


@tz_decorate('date')
def convert_to_date(tokens, origin=None):
    yy = int(tokens.year) if 'year' in tokens else origin.year
    mm = month_mapping(tokens.month) if 'month' in tokens else origin.month
    dd = day_number_mapping(tokens.day[0] if isinstance(tokens.day, list) else tokens.day)
    parsed_date = datetime.date(yy, mm, dd)
    if 'day_name' in tokens and parsed_date.weekday() != weekday_number_mapping(tokens['day_name']):
        return None
    return parsed_date


def convert_to_time(tokens):
    hh = int(tokens.get('hour', 0))
    mm = int(tokens.get('minute', 0))
    ss = int(tokens.get('second', 0))
    return datetime.time(hh, mm, ss)


def convert_to_interval(tokens):
    origin = utc_today()
    unit = tokens.time_unit.lower().rstrip('s')
    dir_tok = tokens.dir_rel
    if unit == 'day':
        start = datetime.datetime.combine(origin, datetime.time(8))
        end = datetime.datetime.combine(origin, datetime.time(18))
    elif unit == 'week':
        weekday = origin.weekday()
        start = origin + datetime.timedelta(days=-weekday + 7 * dir_tok)
        end = origin + datetime.timedelta(days=6 - weekday + 7 * dir_tok)
    elif unit == 'month':
        rel_date = origin + relativedelta(months=dir_tok)
        start = datetime.date(rel_date.year, rel_date.month, 1)
        end = datetime.date(rel_date.year, rel_date.month, month_days(rel_date.month,
                                                                      rel_date.year))
        if 'day' in tokens:
            _day = day_number_mapping(tokens.day)
            if _day <= month_days(rel_date.month, rel_date.year):
                tokens['calculatedTime'] = datetime.date(rel_date.year, rel_date.month, _day)
            return
    elif unit == 'year':
        _year = origin.year + dir_tok
        if 'month' in tokens:
            _month = month_mapping(tokens.month)
            start = datetime.date(_year, _month, 1)
            end = datetime.date(_year, _month, month_days(_month, _year))
        else:
            start = datetime.date(_year, 1, 1)
            end = datetime.date(_year, 12, 31)
    else:
        return
    tokens['calculatedTime'] = TimeInterval(start, end)


@past_future_unwrap
def convert_to_abs_time(tokens):
    day = tokens.get('named_day', tokens.get('date', None))
    if 'time_of_day' in tokens:
        if isinstance(tokens['time_of_day'], datetime.time):
            parsed_time = tokens['time_of_day']
        elif tokens['time_of_day'] in ['noon', 'midnight']:
            parsed_time = {
                'noon': datetime.time(12),
                'midnight': datetime.time(0),
            }[tokens['time_of_day']]
        elif 'hour' in tokens:
            parsed_time = convert_to_time(tokens)
        else:
            parsed_time = utc_now().time()
    else:
        parsed_time = None
    if parsed_time is not None and day is not None:
        tokens['abs_time'] = datetime.datetime.combine(day, parsed_time)
    elif parsed_time is not None:
        tokens['abs_time'] = parsed_time
    elif day is not None:
        tokens['abs_time'] = day


@past_future_unwrap
def calculate_time(tokens):
    if 'abs_time' in tokens:
        abs_time = tokens['abs_time']
    elif tokens.time_unit in [hour_, minute_, _second_]:
        abs_time = utc_now()
    else:
        abs_time = utc_today()
    if 'timeOffset' in tokens:
        abs_time += tokens['timeOffset']
    tokens['calculatedTime'] = abs_time


def day_number_mapping(day_str):
    d = {
        '1st': 1,
        '2nd': 2,
        '3rd': 3,
        '4th': 4,
        '5th': 5,
        '6th': 6,
        '7th': 7,
        '8th': 8,
        '9th': 9,
        '10th': 10,
        '11th': 11,
        '12th': 12,
        '13th': 13,
        '14th': 14,
        '15th': 15,
        '16th': 16,
        '17th': 17,
        '18th': 18,
        '19th': 19,
        '20th': 20,
        '21st': 21,
        '22nd': 22,
        '23rd': 23,
        '24th': 24,
        '25th': 25,
        '26th': 26,
        '27th': 27,
        '28th': 28,
        '29th': 29,
        '30th': 30,
        '31st': 31
    }
    day_str = day_str.lower()
    if day_str in d:
        return d[day_str]
    else:
        return int(day_str)


def weekday_number_mapping(weekday_str):
    d = {
        'monday': 0,
        'mon': 0,
        'mon.': 0,
        'tuesday': 1,
        'tue': 1,
        'tue.': 1,
        'tues': 1,
        'tues.': 1,
        'wednesday': 2,
        'wed': 2,
        'wed.': 2,
        'thursday': 3,
        'thu': 3,
        'thu.': 3,
        'thurs': 3,
        'thurs.': 3,
        'friday': 4,
        'fri': 4,
        'fri.': 4,
        'saturday': 5,
        'sat': 5,
        'sat.': 5,
        'sunday': 6,
        'sun': 6,
        'sun.': 6
    }
    return d[weekday_str.lower()]


def month_mapping(month_str):
    m = {
        '1': 1,
        '01': 1,
        'jan': 1,
        'jan.': 1,
        'january': 1,
        '2': 2,
        '02': 2,
        'feb': 2,
        'feb.': 2,
        'february': 2,
        '3': 3,
        '03': 3,
        'mar': 3,
        'mar.': 3,
        'march': 3,
        '4': 4,
        '04': 4,
        'apr': 4,
        'apr.': 4,
        'april': 4,
        '5': 5,
        '05': 5,
        'may': 5,
        '6': 6,
        '06': 6,
        'jun': 6,
        'jun.': 6,
        'june': 6,
        '7': 7,
        '07': 7,
        'jul': 7,
        'jul.': 7,
        'july': 7,
        '8': 8,
        '08': 8,
        'aug': 8,
        'aug.': 8,
        'august': 8,
        '9': 9,
        '09': 9,
        'sep': 9,
        'sep.': 9,
        'sept': 9,
        'sept.': 9,
        'september': 9,
        '10': 10,
        'oct': 10,
        'oct.': 10,
        'october': 10,
        '11': 11,
        'nov': 11,
        'nov.': 11,
        'november': 11,
        '12': 12,
        'dec': 12,
        'dec.': 12,
        'december': 12
    }
    return m[month_str.lower()]


def quarter_mapping(quarter_parsed_expr):
    q = {
        'q1': 1,
        'q2': 2,
        'q3': 3,
        'q4': 4,
        'first': 1,
        'second': 2,
        'third': 3,
        'fourth': 4,
    }
    return q[str(quarter_parsed_expr).lower()]


def beginning_end_of_action(tokens):
    calc_time = utc_today()
    bound = {
        'beginning': _BEGINNING,
        'start': _BEGINNING,
        'early': _BEGINNING,
        'middle': _MIDDLE,
        'mid': _MIDDLE,
        'end': _END,
        'late': _END,
    }[tokens.get('bound')]
    if 'calculatedTime' in tokens and isinstance(tokens['calculatedTime'], TimeInterval):
        if bound is _BEGINNING:
            calc_time = tokens['calculatedTime'].get_start()
        elif bound is _MIDDLE:
            delta = tokens['calculatedTime'].get_end() - tokens['calculatedTime'].get_start()
            calc_time = tokens['calculatedTime'].get_start() + delta // 2
        elif bound is _END:
            calc_time = tokens['calculatedTime'].get_end()
    elif 'name' in tokens:
        calc_time += {
            'yesterday': datetime.timedelta(days=-1),
            'today': datetime.timedelta(days=0),
            'tomorrow': datetime.timedelta(days=1)
        }[tokens.name]
    tokens['calculatedTime'] = calc_time


def half_of_action(tokens):
    calc_time = utc_today()
    first = tokens['half'] in ['first', 'earlier']
    if 'calculatedTime' in tokens and isinstance(tokens['calculatedTime'], TimeInterval):
        if first:
            calc_time = tokens['calculatedTime'].get_first_half()
        else:
            calc_time = tokens['calculatedTime'].get_second_half()
    elif 'name' in tokens:
        calc_time += {
            'yesterday': datetime.timedelta(days=-1),
            'today': datetime.timedelta(days=0),
            'tomorrow': datetime.timedelta(days=1)
        }[tokens.name]
    tokens['calculatedTime'] = calc_time


@tz_decorate('calculatedTime', rel_hour=8)
def asap_action(tokens, origin=None):
    calc = datetime.datetime(origin.year, origin.month, origin.day) + datetime.timedelta(hours=8)
    return calc + (datetime.timedelta(days=1) if utc_now().hour >= 8 else datetime.timedelta(
        days=0))


# TODO: set an interval timezone decoration
def interval_year_action(tokens):
    origin = utc_today()
    if 'dir_rel' in tokens:
        calc_time = year_interval(origin.year + tokens.dir_rel)
    elif 1900 < int(tokens.get('year', 0)) - _CENTURY_CHANGE <= 2000:
        calc_time = year_interval(int(tokens.year))
    else:
        return None
    tokens['calculatedTime'] = calc_time


# TODO: set an interval timezone decoration
def interval_quarter_action(tokens, origin=None):
    if origin is None:
        origin = utc_today()
    if 'dir_rel' in tokens:
        rel_date = origin + relativedelta(months=3 * tokens.dir_rel)
        calc_time = quarter_interval(quarter_by_date(origin=rel_date), rel_date.year)
    elif 'quarter' in tokens:
        calc_time = quarter_interval(quarter_mapping(tokens.quarter),
                                     int(tokens.get('year', origin.year)))
    else:
        return None
    tokens['calculatedTime'] = calc_time


# TODO: add last and next occurrence of the month when year is unclear
# TODO: set an interval timezone decoration
def interval_month_action(tokens):
    origin = utc_today()
    if 'dir_rel' in tokens:
        rel_date = origin + relativedelta(months=tokens.dir_rel)
        calc_time = month_interval(rel_date.month, rel_date.year)
    elif 'month' in tokens:
        calc_time = month_interval(month_mapping(tokens.month), int(tokens.get('year',
                                                                               origin.year)))
    else:
        return None
    tokens['calculatedTime'] = calc_time


def now_action(tokens):
    now = utc_now()
    if 'time_unit' in tokens:
        unit = tokens.time_unit.lower().rstrip('s')
        delta = {
            'hour': datetime.timedelta(hours=tokens.qty * tokens.dir_abs),
            'minute': datetime.timedelta(minutes=tokens.qty * tokens.dir_abs),
            'second': datetime.timedelta(seconds=tokens.qty * tokens.dir_abs),
        }[unit]
    else:
        delta = datetime.timedelta()
    tokens['utc'] = True
    tokens['calculatedTime'] = now + delta


@tz_decorate('calculatedTime')
def named_day_action(tokens, origin=None):
    day = origin
    if 'date' in tokens:
        day = tokens.date
    if 'time_unit' in tokens:
        unit = tokens.time_unit.lower().rstrip('s')
        delta = {
            'year': relativedelta(years=tokens.qty * tokens.dir_abs),
            'month': relativedelta(months=tokens.qty * tokens.dir_abs),
            'week': datetime.timedelta(weeks=tokens.qty * tokens.dir_abs),
            'day': datetime.timedelta(days=tokens.qty * tokens.dir_abs),
        }[unit]
    else:
        delta = datetime.timedelta()
    if 'time_of_day' in tokens:
        if isinstance(tokens.time_of_day, datetime.time):
            parsed_time = tokens.time_of_day
        elif tokens.time_of_day in ['noon', 'midnight']:
            parsed_time = {
                'noon': datetime.time(12),
                'midnight': datetime.time(0),
            }[tokens.time_of_day]
        elif 'hour' in tokens:
            parsed_time = convert_to_time(tokens)
        else:
            parsed_time = utc_now().time()
    else:
        parsed_time = None
    if parsed_time is not None and day is not None:
        return datetime.datetime.combine(day + delta, parsed_time)
    elif parsed_time is not None:
        return parsed_time + delta
    else:
        return day + delta


@tz_decorate('calculatedTime')
def last_this_next_action(tokens, origin=None):
    return datetime.datetime.combine(origin + datetime.timedelta(days=tokens[0]), tokens[1])


def am_pm_time_to_full(tokens):
    tokens['hour'] = int(tokens['hour']) % 12
    if 'pm' in tokens:
        tokens['hour'] += 12
    return tokens


def o_clock_time_to_full(tokens):
    tokens['hour'] = int(tokens['hour']) % 12
    # Assumption: o'clock times between 7-18
    if tokens['hour'] < 7:
        tokens['hour'] += 12
    return tokens


# TODO: refactor by placing all previous methods into different files (actions and time_utils).

# Grammar used to parse different times is defined below

the_ = utils.caseless_keyword('the')
to_ = utils.caseless_keyword('to')
to_dash_ = utils.caseless_keyword_or(['to', '-'])
at_ = utils.caseless_keyword_or(['at', '@'])
and_ = utils.caseless_keyword('and')
by_ = utils.caseless_keyword('by')
around_ = utils.caseless_keyword('around')
of_ = utils.caseless_keyword('of')
on_ = utils.caseless_keyword('on')
of_dash_ = utils.caseless_keyword_or(['of', '-'])
time_ = utils.caseless_keyword('time')
o_clock = utils.caseless_keyword_or(['o\'clock', 'oclock', 'o clock'])
between_ = utils.caseless_keyword('between')

in_ = utils.caseless_keyword('in').setParseAction(
    pyparsing.replaceWith(1)).setResultsName('dir_abs')
from_ = utils.caseless_keyword('from').setParseAction(
    pyparsing.replaceWith(1)).setResultsName('dir_abs')
before_ = utils.caseless_keyword('before').setParseAction(
    pyparsing.replaceWith(-1)).setResultsName('dir_abs')
after_ = utils.caseless_keyword('after').setParseAction(
    pyparsing.replaceWith(1)).setResultsName('dir_abs')
ago_ = utils.caseless_keyword('ago').setParseAction(
    pyparsing.replaceWith(-1)).setResultsName('dir_abs')

next_ = utils.caseless_keyword('next').setParseAction(
    pyparsing.replaceWith(1)).setResultsName('dir_rel')
last_ = utils.caseless_keyword('last').setParseAction(
    pyparsing.replaceWith(-1)).setResultsName('dir_rel')
this_ = utils.caseless_keyword('this').setParseAction(
    pyparsing.replaceWith(0)).setResultsName('dir_rel')

noon_ = utils.caseless_keyword('noon')
midnight_ = utils.caseless_keyword('midnight')
now_ = utils.caseless_keyword('now')

dawn = utils.caseless_keyword('dawn').setParseAction(lambda tokens: datetime.time(5))
sunrise = utils.caseless_keyword('sunrise').setParseAction(lambda tokens: datetime.time(6))
morning = utils.caseless_keyword('morning').setParseAction(lambda tokens: datetime.time(9))
AM = pyparsing.Regex(r'a(\. ?)?m\.?', re.IGNORECASE).setParseAction(lambda tokens: datetime.time(9))
afternoon = utils.caseless_keyword('afternoon').setParseAction(lambda tokens: datetime.time(14))
PM = pyparsing.Regex(r'p(\. ?)?m\.?',
                     re.IGNORECASE).setParseAction(lambda tokens: datetime.time(14))
dusk = utils.caseless_keyword('dusk').setParseAction(lambda tokens: datetime.time(17))
sunset = utils.caseless_keyword('sunset').setParseAction(lambda tokens: datetime.time(18))
eod = utils.caseless_keyword('eod').setParseAction(lambda tokens: datetime.time(18))
evening = utils.caseless_keyword('evening').setParseAction(lambda tokens: datetime.time(19))
night = utils.caseless_keyword('night').setParseAction(lambda tokens: datetime.time(21))
tonight = (pyparsing.Empty().setParseAction(pyparsing.replaceWith(0)) +
           utils.caseless_keyword('tonight').setParseAction(lambda tokens: datetime.time(21)))

year_ = utils.pluralize('year', pyparsing_regex=True)
quarter_ = utils.pluralize('quarter', pyparsing_regex=True)
month_ = utils.pluralize('month', pyparsing_regex=True)
week_ = utils.pluralize('week', pyparsing_regex=True)
day_ = utils.pluralize('day', pyparsing_regex=True)
hour_ = utils.pluralize('hour', pyparsing_regex=True)
minute_ = utils.pluralize('minute', pyparsing_regex=True)
_second_ = utils.pluralize('second', pyparsing_regex=True)

# TODO: Use some NLP tool to disambiguate some months (e.g. `may` verb or noun) if this causes any issues
months = pyparsing.Regex(
    r'\b('
    r'jan(uary|\.)?'
    r'|feb(ruary|\.)?'
    r'|mar(ch|\.)?'
    r'|apr(il|\.)?'
    r'|may'
    r'|jun(e|\.)?'
    r'|jul(y|\.)?'
    r'|aug(ust|\.)?'
    r'|sep(t(ember|\.)?|\.)?'
    r'|oct(ober|\.)?'
    r'|nov(ember|\.)?'
    r'|dec(ember|\.)?'
    r')\b', re.IGNORECASE)

# TODO: Use some NLP tool to disambiguate some months (e.g. `may` verb or noun) if this causes any issues
months_no_spaces = pyparsing.Regex(
    r'('
    r'jan(uary|\.)?'
    r'|feb(ruary|\.)?'
    r'|mar(ch|\.)?'
    r'|apr(il|\.)?'
    r'|may'
    r'|jun(e|\.)?'
    r'|jul(y|\.)?'
    r'|aug(ust|\.)?'
    r'|sep(t(ember|\.)?|\.)?'
    r'|oct(ober|\.)?'
    r'|nov(ember|\.)?'
    r'|dec(ember|\.)?'
    r')\b', re.IGNORECASE)

day_name = pyparsing.Regex(
    r'\b('
    r'mon(day|\.)?'
    r'|tue(s(day|\.)?|\.)?'
    r'|wed(nesday|\.)?'
    r'|thu(rs(day|\.)?|\.)?'
    r'|fri(day|\.)?'
    r'|sat(urday|\.)?'
    r'|sun(day|\.)?'
    r')\b', re.IGNORECASE)
day_name = day_name.setResultsName('day_name')

ordinal_day = pyparsing.Regex(r'\b('
                              r'[23]0th'
                              r'|[23]?(1st|2nd|3rd|[4-9]th)'
                              r'|1\dth'
                              r')\b', re.IGNORECASE)

date_separators = ['/', '-', '.']

couple = (Optional(utils.caseless_keyword('a')) + utils.caseless_keyword('couple') + Optional(of_))
couple.setParseAction(pyparsing.replaceWith(2))

a_qty = pyparsing.Regex(r'\ban?\b', re.IGNORECASE).setParseAction(pyparsing.replaceWith(1))

integer = pyparsing.Word(pyparsing.nums).setParseAction(lambda token: int(token[0]))
integer_month = pyparsing.Regex(r'\b(1[012]|0?[1-9])\b')
integer_day = pyparsing.Regex(r'\b(3[01]|[1-2]\d|0?[1-9])\b')
integer_month_two_digits_no_trailing_space = pyparsing.Regex(r'\b(1[012]|0[1-9])')
integer_day_no_trailing_space = pyparsing.Regex(r'\b(3[01]|[1-2]\d|0?[1-9])')
integer_day_two_digits_no_leading_space = pyparsing.Regex(r'(3[01]|[1-2]\d|0[1-9])\b')

qty = integer | couple | a_qty | units
qty = qty.setResultsName('qty')

year4 = pyparsing.Regex(r'\b\d{4}\b').setResultsName('year')
year2 = pyparsing.Regex(r'\b\d{2}\b').setParseAction(process_two_digits_year).setResultsName('year')
year = pyparsing.MatchFirst([year4, year2])

date_sep = Optional(pyparsing.Regex(r'[/\-\. ]'))
year_sep = Optional(pyparsing.Regex(r'[/\-\. ,]'))

month = pyparsing.MatchFirst([integer_month, months])
month = month.setResultsName('month')

day_spec = pyparsing.MatchFirst([integer_day, ordinal_day])
day_spec = day_spec.setResultsName('day')

date_day = pyparsing.MatchFirst([day_name + Optional(the_),
                                 the_]) \
           + ordinal_day('day')

date_ymd = year4\
           + pyparsing.MatchFirst([SEP_SYM + month + SEP_SYM for SEP_SYM in date_separators])\
           + day_spec

date_mdy = pyparsing.MatchFirst([
    month + date_sep + Optional(the_) + day_spec +
    Optional(year_sep + year + pyparsing.NotAny(':')),
    integer_month_two_digits_no_trailing_space('month') +
    integer_day_two_digits_no_leading_space('day')
])

ignore_date_ydm = year4 + pyparsing.MatchFirst(
    [SEP_SYM + day_spec + SEP_SYM for SEP_SYM in date_separators]) + month

date_day_month = pyparsing.MatchFirst([
    day_spec + Optional(of_dash_) + month,
    integer_day_no_trailing_space('day') + months_no_spaces('month')
])

date = pyparsing.MatchFirst([
    Optional(day_name + Optional(',')) + pyparsing.MatchFirst([date_ymd, date_mdy, date_day_month]),
    date_day
])
date.setParseAction(convert_to_date)

named_day = utils.caseless_keyword_or(['yesterday', 'today', 'tomorrow']).setResultsName('name')

weekday_ref = Optional(Optional(this_).suppress() + last_ | this_ | next_)('dir_rel') + day_name
weekday_ref = weekday_ref.setResultsName('weekday_ref')

day_ref = named_day | weekday_ref
day_ref.setParseAction(convert_to_day)

part_of_day = pyparsing.MatchFirst(
    [morning, dawn, sunrise, AM, afternoon, PM, dusk, sunset, evening, eod, night])
part_of_day = part_of_day.setResultsName('part_of_day')

full_hours = pyparsing.Regex(r'\b(2[0-3]|(1|0?)[0-9])').setResultsName('hour')
am_pm_hours = pyparsing.Regex(r'\b(1[0-2]|0?[1-9])').setResultsName('hour')
minutes = pyparsing.Regex(r'[0-5][0-9]').setResultsName('minute')
seconds = pyparsing.Regex(r'[0-5][0-9]').setResultsName('second')

am = pyparsing.Regex(r'a(\. ?)?m\.?\b', re.IGNORECASE).setResultsName('am')
pm = pyparsing.Regex(r'p(\. ?)?m\.?\b', re.IGNORECASE).setResultsName('pm')

timezone = utils.caseless_keyword_or([
    'Eastern', 'Central', 'Mountain', 'Pacific', 'EST', 'CST', 'MST', 'PST', 'EDT', 'CDT', 'MDT',
    'PDT', 'ET', 'CT', 'MT', 'PT'
])

full_time = full_hours + ':' + minutes + Optional(':' + seconds)
am_pm_time = am_pm_hours + Optional(':' + minutes + Optional(':' + seconds)) + pyparsing.MatchFirst(
    [am, pm])
am_pm_time.setParseAction(am_pm_time_to_full)
o_clock_time = am_pm_hours + o_clock
o_clock_time.setParseAction(o_clock_time_to_full)

hms_time = Optional(at_) + pyparsing.MatchFirst([o_clock_time, am_pm_time, full_time
                                                 ]) + Optional(timezone)

this_time = (this_ + time_).setResultsName('this_time')

time_of_day = pyparsing.MatchFirst([
    Optional(at_ | around_).suppress() + pyparsing.MatchFirst(
        [this_time, hms_time, noon_, midnight_, dusk, dawn, sunrise, sunset, night]),
    Optional(Optional(in_) + the_).suppress() +
    pyparsing.MatchFirst([morning, afternoon, evening, night]),
    Optional(by_).suppress() + eod
])
time_of_day = time_of_day.setResultsName('time_of_day')

relative_date_unit = (year_ | month_ | week_ | day_)('time_unit')
relative_time_unit = (hour_ | minute_ | _second_)('time_unit')
relative_datetime_unit = (relative_date_unit | relative_time_unit)

now_datetime_spec = pyparsing.MatchFirst([
    now_,
    Optional(in_) + qty + relative_time_unit + from_ + now_,
    qty + relative_time_unit + (ago_ | before_ + now_),
    in_ + qty + relative_time_unit,
])
now_datetime_spec.setParseAction(now_action)

named_day_date_spec = pyparsing.MatchFirst([
    Optional(in_) + qty + relative_date_unit + from_ + now_,
    qty + relative_date_unit + (ago_ | before_ + now_),
    in_ + qty + relative_date_unit + Optional(time_of_day),
])
named_day_date_spec.setParseAction(named_day_action)

last_this_next_interval = pyparsing.MatchFirst([
    Optional(Optional(the_) + day_spec('day') + of_) + (last_ | this_ | next_) +
    (week_ | month_)('time_unit'),
    Optional(months('month')) + (last_ | this_ | next_) + year_('time_unit')
])
last_this_next_interval.setParseAction(convert_to_interval)
last_this_next_interval = last_this_next_interval.setResultsName('calculatedTime')

datetime_spec = Optional(last_this_next_interval) \
                + pyparsing.MatchFirst([
                    time_of_day + Optional(Optional(of_ | on_) + (date | day_ref)),
                    (date | day_ref) + Optional(Optional(',') + time_of_day)
                ])
datetime_spec.setParseAction(convert_to_abs_time, calculate_time)

rel_time_spec = Optional(in_) + qty + relative_datetime_unit + (from_ | before_
                                                                | after_) + datetime_spec
rel_time_spec.setParseAction(convert_to_timedelta, calculate_time)

last_this_next_part_of_day = pyparsing.MatchFirst([
    tonight,
    (last_ | this_ | next_) + part_of_day,
])
last_this_next_part_of_day.setParseAction(last_this_next_action)

interval_year = year('year')
interval_year.setParseAction(interval_year_action)

interval_year4 = Optional('$')('datetime_parsing_error') + year4('year')
interval_year4.setParseAction(interval_year_action)

quarter_name = pyparsing.Regex(r'\bQ[1234]\b', re.IGNORECASE)
interval_quarter = pyparsing.MatchFirst([
    pyparsing.MatchFirst([
        quarter_name('quarter'),
        utils.caseless_keyword_or(['first', 'second', 'third', 'fourth'])('quarter') + quarter_
    ]) + Optional(year),
    (last_ | this_ | next_)('dir_rel') + quarter_,
])
interval_quarter.setParseAction(interval_quarter_action)

interval_month = months('month') + Optional(Optional(',') + year)
interval_month.setParseAction(interval_month_action)

this_placeholder = pyparsing.Empty()('dir_rel').setParseAction(lambda: 0)
interval = pyparsing.MatchFirst([
    interval_month, interval_quarter, interval_year, last_this_next_interval, named_day,
    (this_placeholder + relative_date_unit)('calculatedTime').setParseAction(convert_to_interval)
])

beginning_end_of = pyparsing.MatchFirst([
    utils.caseless_keyword_or(['beginning', 'start', 'middle', 'end'])('bound') + of_,
    utils.caseless_keyword_or(['early', 'late'])('bound'),
    utils.caseless_keyword('mid')('bound') + Optional(of_dash_)
]) + interval
beginning_end_of.setParseAction(beginning_end_of_action)

half_of = (utils.caseless_keyword_or(['earlier', 'first', 'later', 'second'])('half')) +\
          utils.caseless_keyword('half') + Optional(of_dash_) + interval
half_of.setParseAction(half_of_action)

asap = utils.caseless_keyword('asap')
asap.setParseAction(asap_action)

before_after_datetime_object = pyparsing.MatchFirst([
    (between_ + datetime_spec)('inclusive_start') + (and_ + datetime_spec)('inclusive_end'),
    (Optional(from_) + datetime_spec)('inclusive_start') +
    (to_dash_ + datetime_spec)('inclusive_end'),
    (after_ + datetime_spec)('exclusive_start') + Optional(
        (before_ + datetime_spec)('exclusive_end')),
    (before_ + datetime_spec)('exclusive_end') + Optional(
        (after_ + datetime_spec)('exclusive_start')),
])
before_after_datetime_object.setParseAction(before_after_any)

ignore_greetings = 'good' + (morning | afternoon | evening | night)

delta_time = pyparsing.MatchFirst([
    ignore_greetings.suppress(
    ),  # Allows multiple refactors related to morning/afternoon/evening/night keywords
    beginning_end_of,
    half_of,
    before_after_datetime_object,
    datetime_spec,
    rel_time_spec,
    last_this_next_interval + pyparsing.NotAny(datetime_spec),
    named_day_date_spec,
    now_datetime_spec,
    last_this_next_part_of_day,
    ignore_date_ydm.suppress(),  # Required to prevent extracting a fragment of an invalid date
    interval_quarter,
    interval_month,
    interval_year4,
    asap,
])
delta_time.addParseAction(set_datetime)
