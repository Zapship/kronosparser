import unittest
from datetime import date, datetime, time, timedelta

import mock
from dateutil.relativedelta import FR, MO, TH, TU, relativedelta

import kronosparser
from kronosparser.time_interval import TimeInterval

from .utils import ParserTestCase

now_mock = datetime.utcnow().replace(microsecond=0)
today_mock = now_mock.date()
leap_year = kronosparser.delta_time_defs.is_leap_year

t_morning = time(9)
t_noon = time(12)
t_afternoon = time(14)
t_evening = time(19)
t_night = time(21)
t_dawn = time(5)
t_eod = time(18)
t_dusk = time(17)
t_sunrise = time(6)
t_sunset = time(18)

month_days = [None, 31, 29 if leap_year(today_mock.year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

FLAG_KEYS = ['utc', 'days_delta', 'tz_threshold']


def utc_now_mock():
    return now_mock


def utc_today_mock():
    return today_mock


def get_last_monday():
    today = utc_today_mock()
    if today.weekday() == 0:
        return today - timedelta(days=7)
    else:
        return today + relativedelta(weekday=MO(-1))


def get_last_tuesday():
    today = utc_today_mock()
    if today.weekday() == 1:
        return today - timedelta(days=7)
    else:
        return today + relativedelta(weekday=TU(-1))


def get_next_tuesday():
    today = utc_today_mock()
    if today.weekday() == 1:
        return today + timedelta(days=7)
    else:
        return today + relativedelta(weekday=TU(+1))


def get_next_thursday():
    today = utc_today_mock()
    if today.weekday() == 3:
        return today + timedelta(days=7)
    else:
        return today + relativedelta(weekday=TH(+1))


def get_last_friday():
    today = utc_today_mock()
    if today.weekday() == 4:
        return today - timedelta(days=7)
    else:
        return today + relativedelta(weekday=FR(-1))


def get_next_friday():
    today = utc_today_mock()
    if today.weekday() == 4:
        return today + timedelta(days=7)
    else:
        return today + relativedelta(weekday=FR(+1))


def get_week_start():
    today = utc_today_mock()
    return today - timedelta(days=today.weekday())


def get_this_quarter():
    today = utc_today_mock()
    if today.month < 4:
        return TimeInterval(date(today.year, 1, 1), date(today.year, 3, 31))
    elif today.month < 7:
        return TimeInterval(date(today.year, 4, 1), date(today.year, 6, 30))
    elif today.month < 10:
        return TimeInterval(date(today.year, 7, 1), date(today.year, 9, 30))
    else:
        return TimeInterval(date(today.year, 10, 1), date(today.year, 12, 31))


def get_next_quarter():
    today = utc_today_mock()
    if today.month < 4:
        return TimeInterval(date(today.year, 4, 1), date(today.year, 6, 30))
    elif today.month < 7:
        return TimeInterval(date(today.year, 7, 1), date(today.year, 9, 30))
    elif today.month < 10:
        return TimeInterval(date(today.year, 10, 1), date(today.year, 12, 31))
    else:
        return TimeInterval(date(today.year + 1, 1, 1), date(today.year + 1, 3, 31))


def no_year_flags():
    now = utc_now_mock()
    today = now.date()
    year = now.year
    hour = now.hour
    if today.day == 31 and today.month == 12 and hour >= 12:
        flags_before_29 = {
            'utc': False,
            'days_delta': 366 if leap_year(year) else 365,
            'tz_threshold': 24 - hour
        }
        flags_after_29 = {
            'utc': False,
            'days_delta': 366 if leap_year(year + 1) else 365,
            'tz_threshold': 24 - hour
        }
    elif today.day == 1 and today.month == 1 and hour < 12:
        flags_before_29 = {
            'utc': False,
            'days_delta': -366 if leap_year(year - 1) else -365,
            'tz_threshold': -hour - 1
        }
        flags_after_29 = {
            'utc': False,
            'days_delta': -366 if leap_year(year) else -365,
            'tz_threshold': -hour - 1
        }
    else:
        flags_before_29 = {'utc': False}
        flags_after_29 = {'utc': False}
    return flags_before_29, flags_after_29


# TODO(GL, 2015-10-23): Define the applyContext method for dates and define tests bases in timedeltas
class TestDeltaTime(ParserTestCase):
    def assertParses(self, data):
        for test in data:
            text = test[0]
            expected_date = test[1]
            if isinstance(expected_date, datetime):
                expected_dict = {
                    'datetime': expected_date.isoformat(' ')
                }
            elif isinstance(expected_date, TimeInterval):
                expected_dict = {
                    'interval': {
                        'start': expected_date.get_start().isoformat(),
                        'end': expected_date.get_end().isoformat()
                    }
                }
            elif isinstance(expected_date, date):
                expected_dict = {
                    'date': expected_date.isoformat()
                }
            elif isinstance(expected_date, time):
                expected_dict = {
                    'time': expected_date.isoformat()
                }
            else:
                expected_dict = expected_date
            if len(test) is 2:
                flags = {}
            else:
                flags = test[2]
            expected_dict.update(flags)
            self.assertParsed(kronosparser.delta_time, text, expected_dict)

    def assertParsingError(self, data):
        for text in data:
            expected_dict = {
                'datetime_parsing_error': True
            }
            self.assertParsed(kronosparser.delta_time, text, expected_dict)

    def test_no_date(self):
        invalid = {'datetime_parsing_error': True}
        self.assertParsed(
            kronosparser.delta_time, 'there is no date in 2223 Raspberry Ln Mountain View CA 94045', [invalid])
        self.assertParsed(
            kronosparser.delta_time, 'I drove from 1729A 4th Avenue North in Nashville to Murfreesboro, Tennessee.', [])
        self.assertParsed(
            kronosparser.delta_time, 'know', [])
        self.assertParsed(
            kronosparser.delta_time, 'nowhere', [])
        self.assertParsed(
            kronosparser.delta_time, 'good morning', [invalid])
        self.assertParsed(
            kronosparser.delta_time, 'good afternoon', [invalid])
        self.assertParsed(
            kronosparser.delta_time, 'good evening', [invalid])
        self.assertParsed(
            kronosparser.delta_time, 'good night', [invalid])
        self.assertParsed(
            kronosparser.delta_time, 'Macbook pro $1999', [invalid])

    def test_bad_date(self):
        data = (
            '2015-13-12',
            '2015/20/11'
        )
        self.assertParsingError(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_today(self, utc_today_mock, utc_now_mock):
        now = utc_now_mock()
        hour = now.hour
        data = (
            ('just had lunch now', now, {'utc': True}),
            ('had lunch today', utc_today_mock(), {
                'days_delta': 1,
                'tz_threshold': 24 - hour,
                'utc': False
            } if hour >= 12 else {
                'days_delta': -1,
                'tz_threshold': -hour - 1,
                'utc': False
            }),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_yesterday(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        yesterday = utc_today_mock() - timedelta(days=1)
        data = (
            ('had lunch with the team yesterday', yesterday, {
                'days_delta': 1,
                'tz_threshold': 24 - hour,
                'utc': False
            } if hour >= 12 else {
                'days_delta': -1,
                'tz_threshold': -hour - 1,
                'utc': False
            }),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_one_day_before(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        today = utc_today_mock()
        one_day_before_today = utc_today_mock() - timedelta(days=1)
        one_day_before_yesterday = utc_today_mock() - timedelta(days=2)
        one_day_before_last_tuesday = get_last_tuesday() - timedelta(days=1)
        if today.weekday() == 1 and hour >= 12:
            tu_flags = {'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False}
        elif today.weekday() == 2 and hour < 12:
            tu_flags = {'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False}
        else:
            tu_flags = {'utc': False}
        if hour >= 12:
            today_flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            today_flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('had lunch a day before now', one_day_before_today, today_flags),
            ('had lunch 1 day before today', one_day_before_today, today_flags),
            ('had lunch 1 day before yesterday', one_day_before_yesterday, today_flags),
            ('had lunch one day before last tuesday', one_day_before_last_tuesday, tu_flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_a_couple(self, utc_today_mock, utc_now_mock):
        two_days_ago = utc_today_mock() - timedelta(days=2)
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('couple of days ago', two_days_ago, flags),
            ('a couple of days ago', two_days_ago, flags),
            ('a couple days ago', two_days_ago, flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_three_days_ago(self, utc_today_mock, utc_now_mock):
        three_days_ago = utc_today_mock() - timedelta(days=3)
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('had lunch 3 days ago', three_days_ago, flags),
            ('had lunch three days ago', three_days_ago, flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_weekday(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        hour = utc_now_mock().hour
        last_tuesday = {'date': get_last_tuesday().isoformat()}
        next_tuesday = {'date': get_next_tuesday().isoformat()}
        last_tuesday_noon = {'datetime': datetime.combine(get_last_tuesday(), t_noon).isoformat(' ')}
        next_tuesday_noon = {'datetime': datetime.combine(get_next_tuesday(), t_noon).isoformat(' ')}
        if today.weekday() == 1 and hour >= 12:
            last_tuesday.update({'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False})
            last_tuesday_noon.update({'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False})
        elif today.weekday() == 2 and hour < 12:
            last_tuesday.update({'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False})
            last_tuesday_noon.update({'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False})
        else:
            last_tuesday['utc'] = False
            last_tuesday_noon['utc'] = False
        if today.weekday() == 0 and hour >= 12:
            next_tuesday.update({'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False})
            next_tuesday_noon.update({'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False})
        elif today.weekday() == 1 and hour < 12:
            next_tuesday.update({'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False})
            next_tuesday_noon.update({'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False})
        else:
            next_tuesday['utc'] = False
            next_tuesday_noon['utc'] = False
        data = (
            ('had lunch tuesday', {
                'past': last_tuesday,
                'future': next_tuesday
            }),
            ('had lunch tuesday at noon', {
                'past': last_tuesday_noon,
                'future': next_tuesday_noon
            }),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_last_weekday(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        hour = utc_now_mock().hour
        last_friday = get_last_friday()
        if today.weekday() == 4 and hour >= 12:
            fr_flags = {'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False}
        elif today.weekday() == 5 and hour < 12:
            fr_flags = {'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False}
        else:
            fr_flags = {'utc': False}
        last_monday = get_last_monday()
        if today.weekday() == 0 and hour >= 12:
            mo_flags = {'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False}
        elif today.weekday() == 1 and hour < 12:
            mo_flags = {'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False}
        else:
            mo_flags = {'utc': False}
        data = (
            ('had lunch last friday', last_friday, fr_flags),
            ('had lunch last fri', last_friday, fr_flags),
            ('had lunch this last friday', last_friday, fr_flags),
            ('had a lemon and lunch last fri. with mona', last_friday, fr_flags),
            ('had a lemon and lunch last mon with mona', last_monday, mo_flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_next_weekday(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        hour = utc_now_mock().hour
        next_thursday = get_next_thursday()
        if today.weekday() == 2 and hour >= 12:
            th_flags = {'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False}
        elif today.weekday() == 3 and hour < 12:
            th_flags = {'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False}
        else:
            th_flags = {'utc': False}
        data = (
            ('will have lunch next thurs.', next_thursday, th_flags),
            ('will have lunch this thursday', next_thursday, th_flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_specific_date(self, utc_today_mock):
        data = (
            ('had lunch Tuesday March 15, 2016', date(2016, 3, 15), {'utc': False}),
            ('had lunch November 12, 2015', date(2015, 11, 12), {'utc': False}),
            ('had lunch Nov 23 2015', date(2015, 11, 23), {'utc': False}),
            ('had lunch 11-24-2015', date(2015, 11, 24), {'utc': False}),
            ('had lunch sept. 25 2015', date(2015, 9, 25), {'utc': False}),
            ('had lunch in restaurant junipero 16 the sept. 26 2015', date(2015, 9, 26), {'utc': False}),
            ('had lunch sept. 27th 2011', date(2011, 9, 27), {'utc': False}),
            ('had lunch sept. the 28th 2011', date(2011, 9, 28), {'utc': False}),
            ('had lunch 2015-11-29', date(2015, 11, 29), {'utc': False}),
            ('had lunch 2015-11-29', date(2015, 11, 29), {'utc': False}),
            ('had lunch 1/12/15', date(2015, 1, 12), {'utc': False}),
            ('had lunch 11/12/15', date(2015, 11, 12), {'utc': False}),
            ('had lunch 1/2/15', date(2015, 1, 2), {'utc': False}),
            ('had lunch 01/2/15', date(2015, 1, 2), {'utc': False}),
            ('had lunch 1/02/15', date(2015, 1, 2), {'utc': False}),
            ('Burger king 8.86 4/07/12', date(2012, 4, 7), {'utc': False}),
            ('next week Tuesday March 15, 2016', date(2016, 3, 15), {'utc': False})
        )
        self.assertParses(data)

    # TODO(RA, 2016-07-04): Consider returning the last occurrence of date (or today)
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_date_no_year(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        utc_year = today.year
        flags_before_29, flags_after_29 = no_year_flags()
        data = (
            ('had lunch on May the 4th', date(utc_year, 5, 4), flags_after_29),
            ('had lunch on May 4th', date(utc_year, 5, 4), flags_after_29),
            ('had lunch Sep 14', date(utc_year, 9, 14), flags_after_29),
            ('had lunch Sep 14th', date(utc_year, 9, 14), flags_after_29),
            ('had lunch Sep the 14th', date(utc_year, 9, 14), flags_after_29),
            ('had lunch 9/14', date(utc_year, 9, 14), flags_after_29),
            ('had lunch 13-Jan', date(utc_year, 1, 13), flags_before_29),
            ('had lunch 27 Nov', date(utc_year, 11, 27), flags_after_29),
            ('had lunch 8-March', date(utc_year, 3, 8), flags_after_29),
            ('had lunch 8th of June', date(utc_year, 6, 8), flags_after_29),
            ('had lunch 03FEB', date(utc_year, 2, 3), flags_before_29),
            ('had lunch 0302', date(utc_year, 3, 2), flags_after_29),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_date_no_year_no_month(self, utc_today_mock, utc_now_mock):
        now = utc_now_mock()
        hour = now.hour
        today = utc_today_mock()
        candidate_month_18 = date(today.year, today.month, 18)
        yesterday = utc_today_mock() - timedelta(days=1)
        tomorrow = utc_today_mock() + timedelta(days=1)
        if tomorrow.day == 1 and hour >= 12:
            flags = dict(zip(FLAG_KEYS, (False, month_days[today.month], 24 - hour)))
            alt_month_18 = date(tomorrow.year, tomorrow.month, 18)
            flags_18 = dict(zip(FLAG_KEYS, (False, 28, 24 - hour))) if today.day == 28 else {'utc': False}
        elif today.day == 1 and hour < 12:
            flags = dict(zip(FLAG_KEYS, (False, -month_days[yesterday.month], -hour - 1)))
            alt_month_18 = date(yesterday.year, yesterday.month, 18)
            flags_18 = dict(zip(FLAG_KEYS, (False, 28, -hour - 1))) if yesterday.day == 28 else {'utc': False}
        else:
            flags_18 = {'utc': False}
            flags = {'utc': False}
            alt_month_18 = None
        if alt_month_18 and candidate_month_18.weekday() is not 2:
            candidate_month_18 = alt_month_18
        data = (
            ('the 8th', date(today.year, today.month, 8), flags),
        )
        self.assertParses(data)

        wednesday_text = 'Wednesday 18th'
        if candidate_month_18.weekday() is 2:
            data = (
                (wednesday_text, candidate_month_18, flags_18),
            )
            self.assertParses(data)
        else:
            expected_dict = {
                'datetime_parsing_error': True
            }
            self.assertParsed(kronosparser.delta_time, wednesday_text, expected_dict)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_last_part_of_day(self, utc_today_mock, utc_now_mock):
        yesterday = utc_today_mock() - timedelta(days=1)
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('last morning', datetime.combine(yesterday, t_morning), flags),
            ('last A.M.', datetime.combine(yesterday, t_morning), flags),
            ('last afternoon', datetime.combine(yesterday, t_afternoon), flags),
            ('last PM', datetime.combine(yesterday, t_afternoon), flags),
            ('last evening', datetime.combine(yesterday, t_evening), flags),
            ('last night', datetime.combine(yesterday, t_night), flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_this_part_of_day(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('this morning', datetime.combine(utc_today_mock(), t_morning), flags),
            ('this AM', datetime.combine(utc_today_mock(), t_morning), flags),
            ('this afternoon', datetime.combine(utc_today_mock(), t_afternoon), flags),
            ('this PM', datetime.combine(utc_today_mock(), t_afternoon), flags),
            ('this P. M.', datetime.combine(utc_today_mock(), t_afternoon), flags),
            ('this evening', datetime.combine(utc_today_mock(), t_evening), flags),
            ('this night', datetime.combine(utc_today_mock(), t_night), flags),
            ('tonight', datetime.combine(utc_today_mock(), t_night), flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_next_part_of_day(self, utc_today_mock, utc_now_mock):
        tomorrow = utc_today_mock() + timedelta(days=1)
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('next morning', datetime.combine(tomorrow, t_morning), flags),
            ('next AM', datetime.combine(tomorrow, t_morning), flags),
            ('next afternoon', datetime.combine(tomorrow, t_afternoon), flags),
            ('next PM', datetime.combine(tomorrow, t_afternoon), flags),
            ('next p.m.', datetime.combine(tomorrow, t_afternoon), flags),
            ('next evening', datetime.combine(tomorrow, t_evening), flags),
            ('next night', datetime.combine(tomorrow, t_night), flags),
        )
        self.assertParses(data)

    # TODO(RA, 2016-06-29): Thoroughly check flags for month/year deltas (they possibly fail around the end of a month)
    @unittest.skipIf(utc_today_mock().day in [1, month_days[utc_today_mock().month]], 'test is hard to write')
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_imprecise_dates(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        hour = utc_now_mock().hour
        week_ago = today - timedelta(days=7)
        three_weeks_ago = today - timedelta(days=21)
        in_a_week = today + timedelta(days=7)
        month_ago = date(today.year, today.month, 1)
        month_ago -= timedelta(days=1)
        if month_ago.day > today.day:
            month_ago -= timedelta(days=month_ago.day - today.day)
        in_a_month = date(today.year + (today.month + 1) // 12, (today.month + 1) % 12 + 1, 1)
        in_a_month -= timedelta(days=1)
        if in_a_month.day > today.day:
            in_a_month -= timedelta(days=in_a_month.day - today.day)
        if today.month == 2 and today.day == 29:
            year_ago = date(today.year - 1, today.month, 28)
            in_a_year = date(today.year + 1, today.month, 28)
            in_23_years = date(today.year + 23, today.month, 28)
        else:
            year_ago = date(today.year - 1, today.month, today.day)
            in_a_year = date(today.year + 1, today.month, today.day)
            in_23_years = date(today.year + 23, today.month, today.day)
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        alt_day = today + timedelta(days=flags['days_delta'])
        data = (
            ('1st of this month', today - timedelta(days=today.day - 1), {'utc': False}),
            ('a year ago', year_ago, flags),
            ('a month ago', month_ago, flags if any(day.day < month_days[month_ago.month] for day in [today, alt_day]) else {'utc': False}),
            ('a week ago', week_ago, flags),
            ('3 weeks ago', three_weeks_ago, flags),
            ('three weeks ago', three_weeks_ago, flags),
            ('40 minutes ago', utc_now_mock() - timedelta(minutes=40), {'utc': True}),
            ('1 hour ago', utc_now_mock() - timedelta(hours=1), {'utc': True}),
            ('1 minute ago', utc_now_mock() - timedelta(minutes=1), {'utc': True}),
            ('in a year', in_a_year, flags),
            ('in a month', in_a_month, flags if any(day.day < month_days[in_a_month.month] for day in [today, alt_day]) else {'utc': False}),
            ('in a week', in_a_week, flags),
            ('in 23 years from now', in_23_years, flags)
        )
        self.assertParses(data)

    # TODO(RA, 2016-07-04): Consider returning a datetime
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_beginning_and_end_of(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        mid_days = [0, 16, 14, 16, 15, 16, 15, 16, 16, 15, 16, 15, 16]
        this_month = today.month
        last_day = month_days[this_month]
        last_day_next_month = month_days[this_month + 1 if this_month < 12 else 1]
        mid_q1 = date(today.year, 2, 15 if leap_year(today.year) else 14)
        mid_next_month = date(today.year + this_month // 12, this_month % 12 + 1, mid_days[this_month % 12 + 1])
        end_next_month = date(today.year + this_month // 12, this_month % 12 + 1, last_day_next_month)
        mid_last_year = date(today.year - 1, 7, 1 if leap_year(today.year - 1) else 2)
        data = (
            ('end of jan', date(today.year, 1, 31), {'utc': False}),
            ('end of week', get_week_start() + timedelta(days=6), {'utc': False}),
            ('end of 2014', date(2014, 12, 31), {'utc': False}),
            ('end of last year', date(today.year - 1, 12, 31), {'utc': False}),
            ('end of yesterday', today - timedelta(days=1), {'utc': False}),
            ('end of today', today, {'utc': False}),
            ('end of this year', date(today.year, 12, 31), {'utc': False}),
            ('end of next year', date(today.year + 1, 12, 31), {'utc': False}),
            ('end of this month', date(today.year, this_month, last_day), {'utc': False}),
            ('end of next month', end_next_month, {'utc': False}),
            ('end of Q1', date(today.year, 3, 31), {'utc': False}),
            ('late jan', date(today.year, 1, 31), {'utc': False}),
            ('late 2014', date(2014, 12, 31), {'utc': False}),
            ('late last year', date(today.year - 1, 12, 31), {'utc': False}),
            ('late yesterday', today - timedelta(days=1), {'utc': False}),
            ('late today', today, {'utc': False}),
            ('late this year', date(today.year, 12, 31), {'utc': False}),
            ('late next year', date(today.year + 1, 12, 31), {'utc': False}),
            ('late this month', date(today.year, this_month, last_day), {'utc': False}),
            ('late next month', end_next_month, {'utc': False}),
            ('late second quarter', date(today.year, 6, 30), {'utc': False}),
            ('beginning of next month', date(today.year + this_month // 12, this_month % 12 + 1, 1), {'utc': False}),
            ('start of week', get_week_start(), {'utc': False}),
            ('beginning of january', date(today.year, 1, 1), {'utc': False}),
            ('beginning of 96', date(1996, 1, 1), {'utc': False}),
            ('beginning of last year', date(today.year - 1, 1, 1), {'utc': False}),
            ('beginning of yesterday', today - timedelta(days=1), {'utc': False}),
            ('beginning of today', today, {'utc': False}),
            ('beginning of Q3', date(today.year, 7, 1), {'utc': False}),
            ('early next month', date(today.year + this_month // 12, this_month % 12 + 1, 1), {'utc': False}),
            ('early january', date(today.year, 1, 1), {'utc': False}),
            ('early 96', date(1996, 1, 1), {'utc': False}),
            ('early last year', date(today.year - 1, 1, 1), {'utc': False}),
            ('early yesterday', today - timedelta(days=1), {'utc': False}),
            ('early today', today, {'utc': False}),
            ('early Q4', date(today.year, 10, 1), {'utc': False}),
            ('mid next month', mid_next_month, {'utc': False}),
            ('mid week', get_week_start() + timedelta(days=3), {'utc': False}),
            ('mid-next week', get_week_start() + timedelta(days=10), {'utc': False}),
            ('mid january', date(today.year, 1, 16), {'utc': False}),
            ('mid 96', date(1996, 7, 1), {'utc': False}),
            ('mid last year', mid_last_year, {'utc': False}),
            ('mid yesterday', today - timedelta(days=1), {'utc': False}),
            ('mid today', today, {'utc': False}),
            ('mid Q1', mid_q1, {'utc': False}),
            ('middle of next month', mid_next_month, {'utc': False}),
            ('middle of week', get_week_start() + timedelta(days=3), {'utc': False}),
            ('middle of january', date(today.year, 1, 16), {'utc': False}),
            ('middle of 96', date(1996, 7, 1), {'utc': False}),
            ('middle of last year', mid_last_year, {'utc': False}),
            ('middle of yesterday', today - timedelta(days=1), {'utc': False}),
            ('middle of today', today, {'utc': False}),
            ('middle of Q1', mid_q1, {'utc': False})
        )
        self.assertParses(data)

    # Support for time requires leaving only the time
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_time(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('0:15:20', datetime.combine(utc_today_mock(), time(0, 15, 20)), flags),
            ('00:15:21', datetime.combine(utc_today_mock(), time(0, 15, 21)), flags),
            ('12:45', datetime.combine(utc_today_mock(), time(12, 45)), flags),
            ('23:15:20', datetime.combine(utc_today_mock(), time(23, 15, 20)), flags),
            ('@3am', datetime.combine(utc_today_mock(), time(3)), flags),
            ('6am', datetime.combine(utc_today_mock(), time(6)), flags),
            ('12:45 AM', datetime.combine(utc_today_mock(), time(0, 45)), flags),
            ('12:46 a.m', datetime.combine(utc_today_mock(), time(0, 46)), flags),
            ('12:40 PM', datetime.combine(utc_today_mock(), time(12, 40)), flags),
            ('2:32:04 PM', datetime.combine(utc_today_mock(), time(14, 32, 4)), flags),
            ('2:32:05PM', datetime.combine(utc_today_mock(), time(14, 32, 5)), flags),
            ('2:32:06p.m.', datetime.combine(utc_today_mock(), time(14, 32, 6)), flags),
            ('2:32:07pm', datetime.combine(utc_today_mock(), time(14, 32, 7)), flags),
            ('2:33pm', datetime.combine(utc_today_mock(), time(14, 33)), flags),
            ('2:34p. m.', datetime.combine(utc_today_mock(), time(14, 34)), flags),
            ('2:34p. m. PST', datetime.combine(utc_today_mock(), time(14, 34)), flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_date_with_time(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        if hour >= 12:
            day_flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            day_flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        flags_before_29, flags_after_29 = no_year_flags()
        data = (
            ('yesterday 0:15:20', datetime.combine(utc_today_mock(), time(0, 15, 20)) - timedelta(days=1), day_flags),
            ('yesterday around 8am', datetime.combine(utc_today_mock(), time(8)) - timedelta(days=1), day_flags),
            ('today 12:45', datetime.combine(utc_today_mock(), time(12, 45)), day_flags),
            ('tomorrow 00:15:21', datetime.combine(utc_today_mock(), time(0, 15, 21)) + timedelta(days=1), day_flags),
            ('noon tomorrow', datetime.combine(utc_today_mock(), t_noon) + timedelta(days=1), day_flags),
            ("4 o'clock tomorrow", datetime.combine(utc_today_mock(), time(16)) + timedelta(days=1), day_flags),
            ("4 o'clock CT tomorrow", datetime.combine(utc_today_mock(), time(16)) + timedelta(days=1), day_flags),
            ('tomorrow noon', datetime.combine(utc_today_mock(), t_noon) + timedelta(days=1), day_flags),
            ('tomorrow at noon', datetime.combine(utc_today_mock(), t_noon) + timedelta(days=1), day_flags),
            ('05/20 15:20', datetime(utc_now_mock().year, 5, 20, hour=15, minute=20), flags_after_29),
            ('05/21 at 15:25', datetime(utc_now_mock().year, 5, 21, hour=15, minute=25), flags_after_29),
            ('05/21 @ 15:26', datetime(utc_now_mock().year, 5, 21, hour=15, minute=26), flags_after_29),
            ('Apollo 11 landed on July 20, 1969, at 13:18', datetime(1969, 7, 20, hour=13, minute=18), {'utc': False}),
            ('Dec 31 1979 at 17:00', datetime(1979, 12, 31, hour=17), {'utc': False}),
            ('in two days at 2pm', datetime.combine(utc_today_mock(), time(14)) + timedelta(days=2), day_flags),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_general_relative_dates(self, utc_today_mock, utc_now_mock):
        current_year = utc_today_mock().year
        flags = {'utc': False}
        flags_before_29, flags_after_29 = no_year_flags()
        data = (
            ('2 days before Nov 23 2015', date(2015, 11, 23) - timedelta(days=2), flags),
            ('in 23 years from Jan 1, 2016', date(2039, 1, 1), flags),
            ('2 weeks before Dec 24', date(current_year, 12, 24) - timedelta(weeks=2), flags_after_29),
            ('2 months after Dec 25', date(current_year+1, 2, 25), flags_after_29),
            ('3 months after Dec 25', date(current_year+1, 3, 25), flags_after_29),
            ('a year after Dec 26', date(current_year+1, 12, 26), flags_after_29)
        )
        self.assertParses(data)

    # Support for time requires leaving only the time
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_part_of_day(self, utc_today_mock, utc_now_mock):
        hour = utc_now_mock().hour
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('the morning', datetime.combine(utc_today_mock(), t_morning), flags),
            ('in the morning', datetime.combine(utc_today_mock(), t_morning), flags),
            ('at night', datetime.combine(utc_today_mock(), t_night), flags),
            ('dusk', datetime.combine(utc_today_mock(), t_dusk), flags),
            ('dawn', datetime.combine(utc_today_mock(), t_dawn), flags),
            ('eod', datetime.combine(utc_today_mock(), t_eod), flags),
            ('end of day', datetime.combine(utc_today_mock(), t_eod), {'utc': False}),  # TODO fix flags for intervals
            ('by eod', datetime.combine(utc_today_mock(), t_eod), flags),
            ('at sunrise', datetime.combine(utc_today_mock(), t_sunrise), flags),
            ('around sunset', datetime.combine(utc_today_mock(), t_sunset), flags)
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_date_with_part_of_day(self, utc_today_mock, utc_now_mock):
        flags_before_29, flags_after_29 = no_year_flags()
        hour = utc_now_mock().hour
        yesterday = utc_today_mock() - timedelta(days=1)
        tomorrow = utc_today_mock() + timedelta(days=1)
        if hour >= 12:
            flags = {'days_delta': 1, 'tz_threshold': 24 - hour, 'utc': False}
        else:
            flags = {'days_delta': -1, 'tz_threshold': -hour - 1, 'utc': False}
        data = (
            ('yesterday morning', datetime.combine(yesterday, t_morning), flags),
            ('yesterday in the morning', datetime.combine(yesterday, t_morning), flags),
            ('today in the afternoon', datetime.combine(utc_today_mock(), t_afternoon), flags),
            ('tomorrow afternoon', datetime.combine(tomorrow, t_afternoon), flags),
            ('eod tomorrow', datetime.combine(tomorrow, t_eod), flags),
            ('05/20 in the afternoon', datetime.combine(date(utc_now_mock().year, 5, 20), t_afternoon), flags_after_29),
            ('05/21/2015 evening', datetime.combine(date(2015, 5, 21), t_evening), {'utc': False}),
            ('05/22/12 in the evening', datetime.combine(date(2012, 5, 22), t_evening), {'utc': False}),
            ('6/27 98 at night', datetime.combine(date(1998, 6, 27), t_night), {'utc': False}),
            ('Dec 12, 2012 night', datetime.combine(date(2012, 12, 12), t_night), {'utc': False}),
        )
        self.assertParses(data)

    # TODO (RA, 2016-11-08) Add correct flags
    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_interval(self, utc_today_mock, utc_now_mock):
        today = utc_today_mock()
        year = today.year
        month = today.month
        this_month = TimeInterval(date(year, month, 1), date(year, month, month_days[month]))

        if month == 1:
            last_month = TimeInterval(date(year - 1, 12, 1), date(year - 1, 12, 31))
        else:
            last_month = TimeInterval(date(year, month - 1, 1), date(year, month - 1, month_days[month - 1]))
        if month == 12:
            next_month = TimeInterval(date(year + 1, 1, 1), date(year + 1, 1, 31))
        else:
            next_month = TimeInterval(date(year, month + 1, 1), date(year, month + 1, month_days[month + 1]))
        this_week_s = get_week_start()
        last_week_s = this_week_s - timedelta(weeks=1)
        next_week_s = this_week_s + timedelta(weeks=1)
        data = (
            ('December last year',
             TimeInterval(date(today.year - 1, 12, 1), date(today.year - 1, 12, 31)),
             {'utc': False}),
            ('last week', TimeInterval(last_week_s, last_week_s + timedelta(days=6)), {'utc': False}),
            ('this week', TimeInterval(this_week_s, this_week_s + timedelta(days=6)), {'utc': False}),
            ('next week', TimeInterval(next_week_s, next_week_s + timedelta(days=6)), {'utc': False}),
            ('last month', last_month, {'utc': False}),
            ('this month', this_month, {'utc': False}),
            ('next month', next_month, {'utc': False}),
            ('last year', TimeInterval(date(year - 1, 1, 1), date(year - 1, 12, 31)), {'utc': False}),
            ('this year', TimeInterval(date(year, 1, 1), date(year, 12, 31)), {'utc': False}),
            ('next year', TimeInterval(date(year + 1, 1, 1), date(year + 1, 12, 31)), {'utc': False}),
            ('Q1', TimeInterval(date(year, 1, 1), date(year, 3, 31)), {'utc': False}),
            ('November', TimeInterval(date(year, 11, 1), date(year, 11, 30)), {'utc': False}),
            ('February 2012', TimeInterval(date(2012, 2, 1), date(2012, 2, 29)), {'utc': False}),
            ('July, 1992', TimeInterval(date(1992, 7, 1), date(1992, 7, 31)), {'utc': False}),
            ('Q1 2015', TimeInterval(date(2015, 1, 1), date(2015, 3, 31)), {'utc': False}),
            ('show me 2017 opportunities', TimeInterval(date(2017, 1, 1), date(2017, 12, 31)), {'utc': False}),
            ('this quarter', get_this_quarter(), {'utc': False}),
            ('next quarter', get_next_quarter(), {'utc': False}),
            ('third quarter 2017', TimeInterval(date(2017, 7, 1), date(2017, 9, 30)), {'utc': False}),
            ('later half of january 2017', TimeInterval(date(2017, 1, 16), date(2017, 1, 31)), {'utc': False}),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_date_range(self, patched_utc_today, patched_utc_now):
        today = utc_today_mock()
        hour = utc_now_mock().hour
        next_tue = get_next_tuesday()
        if today.weekday() == 0 and hour >= 12:
            next_tuesday_flags = {'days_delta': 7, 'tz_threshold': 24 - hour, 'utc': False}
        elif today.weekday() == 1 and hour < 12:
            next_tuesday_flags = {'days_delta': -7, 'tz_threshold': -hour - 1, 'utc': False}
        else:
            next_tuesday_flags = {'utc': False}
        data = (
            ('before 2015-04-03 after 2012-12-25', TimeInterval(date(2012, 12, 26), date(2015, 4, 2)), {'utc': False}),
            ('wed jan 11 2017 5:00 pm - 7:30 pm',
             TimeInterval(
                 datetime(2017, 1, 11, hour=17),
                 datetime(2017, 1, 11, hour=19, minute=30)
             ), {'utc': False}),
            ('from 2:30pm to 3pm on next tuesday',
             TimeInterval(
                 datetime.combine(next_tue, time(hour=14, minute=30)),
                 datetime.combine(next_tue, time(hour=15))
             ), next_tuesday_flags),
            ('from 2016-01-01 to 2016-12-31', TimeInterval(date(2016, 1, 1), date(2016, 12, 31)), {'utc': False}),
            ('between 2017-01-01 and 2017-12-31', TimeInterval(date(2017, 1, 1), date(2017, 12, 31)), {'utc': False}),
        )
        self.assertParses(data)

    @mock.patch('kronosparser.delta_time_defs.utc_now', side_effect=utc_now_mock)
    @mock.patch('kronosparser.delta_time_defs.utc_today', side_effect=utc_today_mock)
    def test_asap(self, utc_today_mock, utc_now_mock):
        next_day_8 = utc_today_mock() if utc_now_mock().hour < 8 else utc_today_mock() + timedelta(days=1)
        flags = {
            'utc': False,
            'days_delta': -1 if 8 <= utc_now_mock().hour < 20 else 1,
            'tz_threshold':
                8 - utc_now_mock().hour if utc_now_mock().hour < 8
                else 7 - utc_now_mock().hour if utc_now_mock().hour < 20
                else 32 - utc_now_mock().hour
        }
        data = (
            ('asap', datetime.combine(next_day_8, time(8)), flags),
        )
        self.assertParses(data)
