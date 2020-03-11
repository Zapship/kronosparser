from kronosparser import time_parser as delta_time_defs
from kronosparser.utils import find_all, set_date_for_interval, set_dates_with_timezone_fixes

delta_time = delta_time_defs.delta_time


def parse_dates(text, future=False, interval_to_date=True, tz='US/Pacific'):
    matches = find_all(delta_time, text)
    for match in matches:
        parsed_output_keys = list(match['parsed'].keys())
        if 'future' in parsed_output_keys:
            match['parsed'] = match['parsed']['future' if future else 'past']
        parsed_output_keys = list(match['parsed'].keys())
        if interval_to_date and 'interval' in parsed_output_keys:
            set_date_for_interval(match)
        set_dates_with_timezone_fixes(match, tz)
    return matches
